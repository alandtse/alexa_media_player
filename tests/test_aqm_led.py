"""Regression tests for discovery-driven AQM LED switches."""

from copy import deepcopy
from unittest.mock import AsyncMock, MagicMock, patch

from aiohttp import ClientConnectionError, ClientPayloadError
from homeassistant.exceptions import HomeAssistantError
import pytest

from custom_components.alexa_media.alexa_entity import (
    get_led_indicator_instance,
    parse_alexa_entities,
)
from custom_components.alexa_media.aqm_led import resolve_endpoint_id, set_led_state
from custom_components.alexa_media.const import DATA_ALEXAMEDIA
from custom_components.alexa_media.switch import (
    LEDIndicatorSwitch,
    async_setup_platform,
)


@pytest.fixture
def appliance():
    """Sanitized discovery metadata matching the captured AQM capability."""
    return {
        "entityId": "aqm-entity",
        "applianceId": "aqm-appliance",
        "friendlyName": "Office AQM",
        "modelName": "AQM",
        "friendlyDescription": "Amazon Indoor Air Quality Monitor",
        "applianceTypes": ["AIR_QUALITY_MONITOR"],
        "manufacturerName": "Amazon",
        "alexaDeviceIdentifierList": [{"dmsDeviceSerialNumber": "aqm-serial"}],
        "capabilities": [
            {
                "interfaceName": "Alexa.RangeController",
                "instance": "9",
                "properties": {
                    "supported": [{"name": "rangeValue"}],
                    "retrievable": True,
                    "proactivelyReported": True,
                },
            },
            {
                "interfaceName": "Alexa.ToggleController",
                "instance": "11",
                "properties": {
                    "supported": [{"name": "toggleState"}],
                    "retrievable": True,
                    "readOnly": False,
                },
                "resources": {
                    "friendlyNames": [
                        {"value": {"text": "Enable LED Indicator", "locale": "en-US"}},
                        {"value": {"text": "LED", "locale": "en-US"}},
                    ]
                },
            },
        ],
    }


@pytest.mark.parametrize("instance", ["11", "42", 17])
def test_discovery_instance(appliance, instance):
    """Use resource identity rather than assuming a numeric instance."""
    appliance["capabilities"][1]["instance"] = instance
    parsed = parse_alexa_entities([appliance])
    aqm = parsed["aiaqm"][0]
    assert aqm["led_indicator_instance"] == str(instance)
    assert aqm["device_serial"] == "aqm-serial"
    assert parsed["smart_switch"] == []


@pytest.mark.parametrize("label", ["Enable LED Indicator", "LED", "LED Indicator"])
def test_discovery_friendly_names(appliance, label):
    """Either advertised name is sufficient without an instance fallback."""
    appliance["capabilities"][1]["resources"]["friendlyNames"] = [
        {"value": {"text": label, "locale": "en-US"}}
    ]
    assert get_led_indicator_instance(appliance) == "11"


@pytest.mark.parametrize(
    "change",
    [
        "readonly",
        "unretrievable",
        "wrong_property",
        "unrelated",
        "missing_instance",
        "range",
    ],
)
def test_discovery_rejects_other_capabilities(appliance, change):
    """Read-only toggles, air quality ranges and unnamed toggles are not LEDs."""
    cap = appliance["capabilities"][1]
    if change == "readonly":
        cap["properties"]["readOnly"] = True
    elif change == "unretrievable":
        cap["properties"]["retrievable"] = False
    elif change == "wrong_property":
        cap["properties"]["supported"] = [{"name": "powerState"}]
    elif change == "unrelated":
        cap["resources"] = {"friendlyNames": [{"value": {"text": "Notifications"}}]}
    elif change == "missing_instance":
        cap.pop("instance")
    else:
        cap["interfaceName"] = "Alexa.RangeController"
    assert get_led_indicator_instance(appliance) is None


@pytest.fixture
def switch(appliance):
    """A real switch with a mocked shared coordinator."""
    coordinator = MagicMock()
    coordinator.async_request_refresh = AsyncMock()
    coordinator.last_update_success = True
    coordinator.data = {"aqm-entity": []}
    return LEDIndicatorSwitch(
        coordinator, MagicMock(), parse_alexa_entities([appliance])["aiaqm"][0]
    )


@pytest.mark.parametrize(
    "value,expected", [("ON", True), ("OFF", False), ("invalid", None)]
)
def test_state_scoped_to_instance(switch, value, expected):
    """An unrelated toggle and range instance cannot supply LED state."""
    switch.coordinator.data["aqm-entity"] = [
        {
            "namespace": "Alexa.ToggleController",
            "name": "toggleState",
            "instance": "other",
            "value": "ON",
        },
        {
            "namespace": "Alexa.RangeController",
            "name": "rangeValue",
            "instance": "11",
            "value": 99,
        },
        {
            "namespace": "Alexa.ToggleController",
            "name": "toggleState",
            "instance": 11,
            "value": value,
        },
    ]
    assert switch.is_on is expected
    assert switch.available is (expected is not None)
    switch.coordinator.last_update_success = False
    assert not switch.available


def test_unknown_and_identity(switch):
    """Unknown is not off, and the entity joins the existing AQM device."""
    assert switch.is_on is None
    assert not switch.available
    assert switch.unique_id == "aqm-entity_led_indicator"
    assert switch.device_info["identifiers"] == {("alexa_media", "aqm-serial")}


@pytest.mark.asyncio
async def test_control_refresh_and_endpoint_cache(switch):
    """Both directions address the discovered instance and confirm via polling."""
    with (
        patch(
            "custom_components.alexa_media.switch.resolve_endpoint_id",
            AsyncMock(return_value="endpoint"),
        ) as resolve,
        patch(
            "custom_components.alexa_media.switch.set_led_state", AsyncMock()
        ) as control,
    ):
        await switch.async_turn_on()
        await switch.async_turn_off()
        resolve.assert_awaited_once_with(switch._login, "aqm-entity")
        assert [call.args for call in control.await_args_list] == [
            (switch._login, "endpoint", "11", True),
            (switch._login, "endpoint", "11", False),
        ]
        assert switch.coordinator.async_request_refresh.await_count == 2
        assert switch.is_on is None


@pytest.mark.asyncio
async def test_failed_control_does_not_change_state(switch):
    """A rejection surfaces to HA without inventing a state or refreshing."""
    switch._endpoint_id = "endpoint"
    with patch(
        "custom_components.alexa_media.switch.set_led_state",
        AsyncMock(side_effect=HomeAssistantError("rejected")),
    ):
        with pytest.raises(HomeAssistantError, match="rejected"):
            await switch.async_turn_on()
    assert switch.is_on is None
    switch.coordinator.async_request_refresh.assert_not_awaited()


def response(body):
    """Mock the actual HTTP JSON response boundary."""
    return MagicMock(status=200, json=AsyncMock(return_value=body))


@pytest.mark.asyncio
async def test_endpoint_resolution():
    """Map legacy ids explicitly, skipping unrelated endpoints."""
    body = {
        "data": {
            "endpoints": {
                "items": [
                    {"id": "other", "legacyAppliance": None},
                    {"id": "endpoint", "legacyAppliance": {"entityId": "entity"}},
                ]
            }
        }
    }
    with patch(
        "custom_components.alexa_media.aqm_led.AlexaAPI._static_request",
        AsyncMock(return_value=response(body)),
    ):
        assert await resolve_endpoint_id(MagicMock(), "entity") == "endpoint"
        with pytest.raises(HomeAssistantError):
            await resolve_endpoint_id(MagicMock(), "absent")


@pytest.mark.parametrize("power_on", [True, False])
@pytest.mark.asyncio
async def test_control_request(power_on):
    """Verify the instance-aware endpoint feature request and response."""
    operation = "turnOn" if power_on else "turnOff"
    result = {
        "endpointId": "endpoint",
        "featureName": "toggle",
        "instance": "42",
        "featureOperationName": operation,
        "code": "SUCCESS",
    }
    body = {"data": {"setEndpointFeatures": {"featureControlResponses": [result]}}}
    with patch(
        "custom_components.alexa_media.aqm_led.AlexaAPI._static_request",
        AsyncMock(return_value=response(body)),
    ) as request:
        await set_led_state(MagicMock(), "endpoint", "42", power_on)
        assert request.call_args.args[0] == "post"
        assert request.call_args.args[2] == "/nexus/v1/graphql"
        sent = request.call_args.kwargs["data"]["variables"][
            "setEndpointFeaturesInput"
        ]["featureControlRequests"]
        assert sent == [{k: v for k, v in result.items() if k != "code"}]


@pytest.mark.parametrize(
    "body",
    [
        None,
        {},
        {"errors": [{"message": "denied"}]},
        {"data": {"setEndpointFeatures": {}}},
        {"data": {"setEndpointFeatures": {"errors": [{"code": "FAILED"}]}}},
        {
            "data": {
                "setEndpointFeatures": {
                    "featureControlResponses": [{"code": "SUCCESS"}]
                }
            }
        },
    ],
)
@pytest.mark.asyncio
async def test_control_rejects_unconfirmed_success(body):
    """Empty, malformed and rejected responses must never claim success."""
    with patch(
        "custom_components.alexa_media.aqm_led.AlexaAPI._static_request",
        AsyncMock(return_value=response(body)),
    ):
        with pytest.raises(HomeAssistantError):
            await set_led_state(MagicMock(), "endpoint", "11", True)


@pytest.mark.parametrize(
    "include,exclude,count",
    [
        ([], [], 1),
        (["Office AQM"], ["Office AQM"], 1),
        ([], ["Office AQM"], 0),
        (["Other"], [], 0),
    ],
)
@pytest.mark.asyncio
async def test_setup_filters_and_duplicates(appliance, include, exclude, count):
    """LEDs work without extended discovery and respect device name filters."""
    account = {
        "devices": {
            "media_player": {},
            "aiaqm": parse_alexa_entities([deepcopy(appliance)])["aiaqm"],
        },
        "entities": {"media_player": {}, "smart_switch": [], "amazon_kids_switch": []},
        "options": {},
        "coordinator": MagicMock(),
        "login_obj": MagicMock(),
    }
    hass = MagicMock()
    hass.data = {DATA_ALEXAMEDIA: {"accounts": {"test@example.com": account}}}
    config = {
        "email": "test@example.com",
        "include_devices": include,
        "exclude_devices": exclude,
    }
    with patch(
        "custom_components.alexa_media.switch.add_devices", AsyncMock(return_value=True)
    ) as add:
        await async_setup_platform(hass, config, MagicMock())
        await async_setup_platform(hass, config, MagicMock())
        added_leds = [
            entity
            for call in add.call_args_list
            for entity in call.args[1]
            if isinstance(entity, LEDIndicatorSwitch)
        ]
        assert len(added_leds) == count
        assert len(account["entities"]["smart_switch"]) == count


@pytest.mark.parametrize("supported", [None, [None], "toggleState", {}, 42, []])
def test_malformed_led_properties_preserve_discovery(appliance, supported):
    """Malformed LED metadata must not abort discovery of other devices."""
    appliance["capabilities"][1]["properties"]["supported"] = supported
    other = deepcopy(appliance)
    other["entityId"] = "other-entity"
    other["applianceId"] = "other-appliance"
    other["capabilities"][1]["properties"]["supported"] = [{"name": "toggleState"}]

    assert get_led_indicator_instance(appliance) is None
    parsed = parse_alexa_entities([appliance, other])
    assert [entity["id"] for entity in parsed["aiaqm"]] == [
        "aqm-entity",
        "other-entity",
    ]
    assert [entity["led_indicator_instance"] for entity in parsed["aiaqm"]] == [
        None,
        "11",
    ]


def test_mixed_supported_properties(appliance):
    """Ignore malformed entries while retaining a valid toggle property."""
    appliance["capabilities"][1]["properties"]["supported"] = [
        None,
        "invalid",
        42,
        {"name": "toggleState"},
    ]
    assert get_led_indicator_instance(appliance) == "11"


def test_malformed_led_capability_does_not_hide_later_toggle(appliance):
    """Continue looking for a valid LED capability after malformed metadata."""
    valid = deepcopy(appliance["capabilities"][1])
    appliance["capabilities"][1]["properties"]["supported"] = None
    appliance["capabilities"].append(valid)
    assert get_led_indicator_instance(appliance) == "11"


@pytest.mark.parametrize("status", [401, 403, 500, 503])
@pytest.mark.asyncio
async def test_http_errors_skip_json(status):
    """Reject HTTP failures before decoding a possibly HTML response."""
    reply = response(None)
    reply.status = status
    with patch(
        "custom_components.alexa_media.aqm_led.AlexaAPI._static_request",
        AsyncMock(return_value=reply),
    ):
        with pytest.raises(HomeAssistantError, match=f"HTTP {status}"):
            await resolve_endpoint_id(MagicMock(), "entity")
    reply.json.assert_not_awaited()


@pytest.mark.parametrize("error", [ValueError, ClientPayloadError, TimeoutError])
@pytest.mark.asyncio
async def test_json_read_errors_are_home_assistant_errors(error):
    """Invalid JSON and interrupted response reads have a consistent HA error."""
    reply = response(None)
    failure = error("unreadable response")
    reply.json.side_effect = failure
    with patch(
        "custom_components.alexa_media.aqm_led.AlexaAPI._static_request",
        AsyncMock(return_value=reply),
    ):
        with pytest.raises(HomeAssistantError, match="invalid JSON") as caught:
            await resolve_endpoint_id(MagicMock(), "entity")
    assert caught.value.__cause__ is failure


@pytest.mark.parametrize("error", [ClientConnectionError, TimeoutError])
@pytest.mark.asyncio
async def test_request_errors_are_home_assistant_errors(error):
    """Transport failures retain their cause behind a Home Assistant error."""
    failure = error("request failed")
    with patch(
        "custom_components.alexa_media.aqm_led.AlexaAPI._static_request",
        AsyncMock(side_effect=failure),
    ):
        with pytest.raises(HomeAssistantError, match="request failed") as caught:
            await resolve_endpoint_id(MagicMock(), "entity")
    assert caught.value.__cause__ is failure


@pytest.mark.asyncio
async def test_missing_http_response():
    """An absent HTTP response is also reported through Home Assistant."""
    with patch(
        "custom_components.alexa_media.aqm_led.AlexaAPI._static_request",
        AsyncMock(return_value=None),
    ):
        with pytest.raises(HomeAssistantError, match="No response"):
            await resolve_endpoint_id(MagicMock(), "entity")


@pytest.mark.parametrize("cached", [True, False])
@pytest.mark.parametrize("error", [HomeAssistantError, RuntimeError])
@pytest.mark.asyncio
async def test_failed_command_resolves_endpoint_on_retry(switch, cached, error):
    """Clear old and newly resolved IDs on failure without replaying commands."""
    switch._endpoint_id = "old-endpoint" if cached else None
    failure = error("rejected")
    endpoints = ["new-endpoint"] if cached else ["old-endpoint", "new-endpoint"]
    with (
        patch(
            "custom_components.alexa_media.switch.resolve_endpoint_id",
            AsyncMock(side_effect=endpoints),
        ) as resolve,
        patch(
            "custom_components.alexa_media.switch.set_led_state",
            AsyncMock(side_effect=[failure, None]),
        ) as control,
    ):
        with pytest.raises(error, match="rejected") as caught:
            await switch.async_turn_on()
        assert caught.value is failure
        assert switch._endpoint_id is None
        assert switch.is_on is None
        switch.coordinator.async_request_refresh.assert_not_awaited()
        assert control.await_count == 1

        await switch.async_turn_off()
        assert resolve.await_count == len(endpoints)
        assert [call.args for call in control.await_args_list] == [
            (switch._login, "old-endpoint", "11", True),
            (switch._login, "new-endpoint", "11", False),
        ]
        assert switch._endpoint_id == "new-endpoint"
        switch.coordinator.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_failed_endpoint_resolution_does_not_send_command(switch):
    """A lookup failure propagates without control or a polling refresh."""
    with (
        patch(
            "custom_components.alexa_media.switch.resolve_endpoint_id",
            AsyncMock(side_effect=HomeAssistantError("lookup failed")),
        ),
        patch(
            "custom_components.alexa_media.switch.set_led_state", AsyncMock()
        ) as control,
    ):
        with pytest.raises(HomeAssistantError, match="lookup failed"):
            await switch.async_turn_on()
    assert switch._endpoint_id is None
    control.assert_not_awaited()
    switch.coordinator.async_request_refresh.assert_not_awaited()
