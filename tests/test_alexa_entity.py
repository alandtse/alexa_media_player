"""Test the alexa_entity module utility functions."""

import asyncio
import json
import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock

from alexapy import AlexaAPI
from alexapy.errors import AlexapyConnectionError
import pytest

from custom_components.alexa_media.alexa_entity import (
    get_entity_data,
    has_capability,
    is_hue_v1,
    is_known_ha_bridge,
    is_local,
    is_skill,
    sensor_polling_endpoints,
)


class TestHasCapability:
    """Test the has_capability function."""

    def test_has_capability_with_valid_interface(self):
        """Test has_capability returns True when interface and property match."""
        appliance = {
            "capabilities": [
                {
                    "interfaceName": "Alexa.PowerController",
                    "properties": {
                        "retrievable": True,
                        "proactivelyReported": False,
                        "supported": [{"name": "powerState"}],
                    },
                }
            ]
        }

        assert has_capability(appliance, "Alexa.PowerController", "powerState")

    def test_has_capability_with_proactively_reported(self):
        """Test has_capability returns True when proactivelyReported is True."""
        appliance = {
            "capabilities": [
                {
                    "interfaceName": "Alexa.BrightnessController",
                    "properties": {
                        "retrievable": False,
                        "proactivelyReported": True,
                        "supported": [{"name": "brightness"}],
                    },
                }
            ]
        }

        assert has_capability(appliance, "Alexa.BrightnessController", "brightness")

    def test_has_capability_no_matching_interface(self):
        """Test has_capability returns False when interface doesn't match."""
        appliance = {
            "capabilities": [
                {
                    "interfaceName": "Alexa.PowerController",
                    "properties": {
                        "retrievable": True,
                        "proactivelyReported": False,
                        "supported": [{"name": "powerState"}],
                    },
                }
            ]
        }

        assert not has_capability(appliance, "Alexa.BrightnessController", "brightness")

    def test_has_capability_no_matching_property(self):
        """Test has_capability returns False when property doesn't match."""
        appliance = {
            "capabilities": [
                {
                    "interfaceName": "Alexa.PowerController",
                    "properties": {
                        "retrievable": True,
                        "proactivelyReported": False,
                        "supported": [{"name": "powerState"}],
                    },
                }
            ]
        }

        assert not has_capability(appliance, "Alexa.PowerController", "brightness")

    def test_has_capability_no_properties(self):
        """Test has_capability returns False when properties are missing."""
        appliance = {"capabilities": [{"interfaceName": "Alexa.PowerController"}]}

        assert not has_capability(appliance, "Alexa.PowerController", "powerState")

    def test_has_capability_not_retrievable_or_reported(self):
        """Test has_capability returns False when not retrievable or proactively reported."""
        appliance = {
            "capabilities": [
                {
                    "interfaceName": "Alexa.PowerController",
                    "properties": {
                        "retrievable": False,
                        "proactivelyReported": False,
                        "supported": [{"name": "powerState"}],
                    },
                }
            ]
        }

        assert not has_capability(appliance, "Alexa.PowerController", "powerState")

    def test_has_capability_empty_capabilities(self):
        """Test has_capability returns False when capabilities list is empty."""
        appliance = {"capabilities": []}

        assert not has_capability(appliance, "Alexa.PowerController", "powerState")

    def test_has_capability_multiple_properties(self):
        """Test has_capability with multiple supported properties."""
        appliance = {
            "capabilities": [
                {
                    "interfaceName": "Alexa.ColorController",
                    "properties": {
                        "retrievable": True,
                        "proactivelyReported": False,
                        "supported": [
                            {"name": "color"},
                            {"name": "colorTemperatureInKelvin"},
                        ],
                    },
                }
            ]
        }

        assert has_capability(appliance, "Alexa.ColorController", "color")
        assert has_capability(
            appliance, "Alexa.ColorController", "colorTemperatureInKelvin"
        )
        assert not has_capability(appliance, "Alexa.ColorController", "brightness")


class TestIsHueV1:
    """Test the is_hue_v1 function."""

    def test_is_hue_v1_true(self):
        """Test is_hue_v1 returns True for Royal Philips Electronics."""
        appliance = {"manufacturerName": "Royal Philips Electronics"}
        assert is_hue_v1(appliance)

    def test_is_hue_v1_false_different_manufacturer(self):
        """Test is_hue_v1 returns False for different manufacturer."""
        appliance = {"manufacturerName": "Amazon"}
        assert not is_hue_v1(appliance)

    def test_is_hue_v1_false_no_manufacturer(self):
        """Test is_hue_v1 returns False when manufacturerName is missing."""
        appliance = {}
        assert not is_hue_v1(appliance)

    def test_is_hue_v1_false_none_manufacturer(self):
        """Test is_hue_v1 returns False when manufacturerName is None."""
        appliance = {"manufacturerName": None}
        assert not is_hue_v1(appliance)


class TestIsSkill:
    """Test the is_skill function."""

    def test_is_skill_true(self):
        """Test is_skill returns True when namespace is SKILL."""
        appliance = {"driverIdentity": {"namespace": "SKILL"}}
        assert is_skill(appliance)

    def test_is_skill_false_different_namespace(self):
        """Test is_skill returns False for different namespace."""
        appliance = {"driverIdentity": {"namespace": "OTHER"}}
        assert not is_skill(appliance)

    def test_is_skill_false_no_driver_identity(self):
        """Test is_skill returns False when driverIdentity is missing."""
        appliance = {}
        assert not is_skill(appliance)

    def test_is_skill_false_no_namespace(self):
        """Test is_skill returns False when namespace is missing."""
        appliance = {"driverIdentity": {}}
        assert not is_skill(appliance)

    def test_is_skill_false_empty_namespace(self):
        """Test is_skill returns False when namespace is empty."""
        appliance = {"driverIdentity": {"namespace": ""}}
        assert not is_skill(appliance)


class TestIsKnownHaBridge:
    """Test the is_known_ha_bridge function."""

    def test_is_known_ha_bridge_none(self):
        """Test is_known_ha_bridge returns False for None input."""
        assert not is_known_ha_bridge(None)

    def test_is_known_ha_bridge_t0bst4r(self):
        """Test is_known_ha_bridge returns True for t0bst4r manufacturer."""
        appliance = {"manufacturerName": "t0bst4r"}
        assert is_known_ha_bridge(appliance)

    def test_is_known_ha_bridge_matterbridge(self):
        """Test is_known_ha_bridge returns True for Matterbridge manufacturer."""
        appliance = {"manufacturerName": "Matterbridge"}
        assert is_known_ha_bridge(appliance)

    def test_is_known_ha_bridge_false(self):
        """Test is_known_ha_bridge returns False for unknown manufacturer."""
        appliance = {"manufacturerName": "Amazon"}
        assert not is_known_ha_bridge(appliance)

    def test_is_known_ha_bridge_no_manufacturer(self):
        """Test is_known_ha_bridge returns False when manufacturerName is missing."""
        appliance = {}
        assert not is_known_ha_bridge(appliance)


class TestIsLocal:
    """Test the is_local function."""

    def test_is_local_with_connected_via(self):
        """Test is_local returns True when connectedVia is present."""
        appliance = {"connectedVia": "Echo Dot"}
        assert is_local(appliance)

    def test_is_local_voice_enabled_not_skill(self):
        """Test is_local returns True for voice enabled device that's not a skill."""
        appliance = {
            "applianceTypes": ["ALEXA_VOICE_ENABLED"],
            "driverIdentity": {"namespace": "OTHER"},
        }
        assert is_local(appliance)

    def test_is_local_voice_enabled_skill(self):
        """Test is_local returns False for voice enabled device that's a skill."""
        appliance = {
            "applianceTypes": ["ALEXA_VOICE_ENABLED"],
            "driverIdentity": {"namespace": "SKILL"},
        }
        assert not is_local(appliance)

    def test_is_local_ledvance_not_skill(self):
        """Test is_local returns True for Ledvance device that's not a skill."""
        appliance = {
            "manufacturerName": "Ledvance",
            "driverIdentity": {"namespace": "OTHER"},
        }
        assert is_local(appliance)

    def test_is_local_sengled_not_skill(self):
        """Test is_local returns True for Sengled device that's not a skill."""
        appliance = {
            "manufacturerName": "Sengled",
            "driverIdentity": {"namespace": "OTHER"},
        }
        assert is_local(appliance)

    def test_is_local_amazon_not_skill(self):
        """Test is_local returns True for Amazon device that's not a skill."""
        appliance = {
            "manufacturerName": "Amazon",
            "driverIdentity": {"namespace": "OTHER"},
        }
        assert is_local(appliance)

    def test_is_local_ledvance_skill(self):
        """Test is_local returns False for Ledvance device that's a skill."""
        appliance = {
            "manufacturerName": "Ledvance",
            "driverIdentity": {"namespace": "SKILL"},
        }
        assert not is_local(appliance)

    def test_is_local_unknown_manufacturer(self):
        """Test is_local returns False for unknown manufacturer without other flags."""
        appliance = {"manufacturerName": "Unknown"}
        # This should return False as the final zigbee pattern check will fail
        result = is_local(appliance)
        assert result is False

    def test_is_local_empty_appliance(self):
        """Test is_local returns False for empty appliance."""
        appliance = {}
        result = is_local(appliance)
        assert result is False

    def test_is_local_zigbee_pattern_match(self):
        """Test is_local returns True for valid zigbee pattern."""
        appliance = {"applianceId": "AAA_SonarCloudService_AB:CD:EF:12:34:56:78:90"}
        result = is_local(appliance)
        assert result is True

    def test_is_local_zigbee_pattern_no_match(self):
        """Test is_local returns False for invalid zigbee pattern."""
        appliance = {"applianceId": "invalid_pattern"}
        result = is_local(appliance)
        assert result is False


@pytest.mark.asyncio
async def test_graphql_sensor_poll_keeps_missing_instances_and_recovers(monkeypatch):
    """A failed GraphQL poll leaves the last samples intact without a Phoenix retry."""
    login = SimpleNamespace(email="test@example.com")
    snapshot = [
        {"id": "endpoint", "legacyAppliance": {"entityId": "aqm"}},
    ]
    pm = {
        "namespace": "Alexa.RangeController",
        "name": "rangeValue",
        "instance": "9",
        "value": 11,
        "timeOfSample": "2026-11-27T12:34:00Z",
    }
    voc = {**pm, "instance": "3", "value": 82}
    recovered_pm = {
        **pm,
        "instance": 9,
        "value": 17,
        "timeOfSample": "2026-11-27T12:35:00Z",
    }
    recovered_voc = {**voc, "value": 85, "timeOfSample": "2026-11-27T12:36:00Z"}
    gql = AsyncMock(
        side_effect=[
            None,
            AlexapyConnectionError(),
            {"aqm": [recovered_pm]},
            {"aqm": [recovered_voc]},
        ]
    )
    legacy = AsyncMock(
        return_value={
            "deviceStates": [
                {
                    "entity": {"entityId": "guard"},
                    "capabilityStates": ['{"name": "armState", "value": "DISARMED"}'],
                }
            ]
        }
    )
    monkeypatch.setattr(AlexaAPI, "get_entity_state_gql", gql, raising=False)
    monkeypatch.setattr(AlexaAPI, "get_entity_state", legacy)

    previous = {"aqm": [pm, voc], "unmonitored": [pm]}
    for expected in (
        [pm, voc],
        [pm, voc],
        [recovered_pm, voc],
        [recovered_pm, recovered_voc],
    ):
        previous = await get_entity_data(
            login, ["aqm", "guard"], endpoints=snapshot, previous=previous
        )
        assert previous == {
            "aqm": expected,
            "guard": [{"name": "armState", "value": "DISARMED"}],
        }
        gql.assert_awaited_with(login, ["aqm"], endpoints=snapshot)
        legacy.assert_awaited_with(login, entity_ids=["guard"])


def test_sensor_polling_endpoints_requires_explicit_sensor_mapping():
    """Legacy-only discovery and entities with other capabilities stay on Phoenix."""
    rows = [
        {"id": "one", "legacyAppliance": {"entityId": "aqm"}},
        {"legacyAppliance": {"entityId": "unmapped"}},
        {"id": "two", "legacyAppliance": {"entityId": "shared"}},
        {"id": "three", "legacyAppliance": {"entityId": "guard"}},
        {"id": "four", "legacyAppliance": None},
    ]
    assert sensor_polling_endpoints(
        rows,
        {
            "temperature": [{"id": "aqm"}, {"id": "unmapped"}, {"id": "shared"}],
            "air_quality": [{"id": "aqm"}],
            "binary_sensor": [{"id": "shared"}],
            "guard": [{"id": "guard"}],
        },
    ) == [rows[0]]


@pytest.mark.asyncio
async def test_mixed_poll_returns_graphql_state_when_phoenix_times_out(monkeypatch):
    """A blocked legacy read cannot discard a successful GraphQL read."""
    login = SimpleNamespace(email="test@example.com")
    snapshot = [{"id": "endpoint", "legacyAppliance": {"entityId": "temperature"}}]
    reading = {
        "namespace": "Alexa.TemperatureSensor",
        "name": "temperature",
        "value": 19,
    }
    guard = {"namespace": "Alexa.SecurityPanelController", "name": "armState"}

    async def blocked_legacy(*args, **kwargs):
        await asyncio.Event().wait()

    monkeypatch.setattr(
        "custom_components.alexa_media.alexa_entity._LEGACY_MIXED_POLL_TIMEOUT", 0.01
    )
    monkeypatch.setattr(
        AlexaAPI,
        "get_entity_state_gql",
        AsyncMock(return_value={"temperature": [reading]}),
        raising=False,
    )
    monkeypatch.setattr(AlexaAPI, "get_entity_state", blocked_legacy)
    async with asyncio.timeout(1):
        state = await get_entity_data(
            login,
            ["temperature", "guard"],
            endpoints=snapshot,
            previous={"guard": [guard]},
        )
    assert state == {"temperature": [reading], "guard": [guard]}


@pytest.mark.asyncio
@pytest.mark.parametrize("response_kind", ["none", "empty", "partial", "empty_states"])
async def test_mixed_poll_retains_omitted_phoenix_samples(monkeypatch, response_kind):
    """Keep old Phoenix samples and publish fresh GraphQL and Phoenix data."""
    login = object()
    snapshot = [{"id": "endpoint", "legacyAppliance": {"entityId": "temperature"}}]
    reading = {
        "namespace": "Alexa.TemperatureSensor",
        "name": "temperature",
        "value": 21,
    }
    power = {"namespace": "Alexa.PowerController", "name": "powerState", "value": "OFF"}
    brightness = {
        "namespace": "Alexa.BrightnessController",
        "name": "brightness",
        "value": 40,
        "timeOfSample": "2026-11-27T12:34:00Z",
    }
    guard = {"namespace": "Alexa.SecurityPanelController", "name": "armState"}
    fresh_power = {**power, "value": "ON"}
    responses = {
        "none": None,
        "empty": {"deviceStates": []},
        "partial": {
            "deviceStates": [
                {
                    "entity": {"entityId": "light"},
                    "capabilityStates": [json.dumps(fresh_power)],
                }
            ]
        },
        "empty_states": {
            "deviceStates": [{"entity": {"entityId": "light"}, "capabilityStates": []}]
        },
    }
    monkeypatch.setattr(
        AlexaAPI,
        "get_entity_state_gql",
        AsyncMock(return_value={"temperature": [reading]}),
        raising=False,
    )
    monkeypatch.setattr(
        AlexaAPI, "get_entity_state", AsyncMock(return_value=responses[response_kind])
    )
    assert await get_entity_data(
        login,
        ["temperature", "light", "guard"],
        endpoints=snapshot,
        previous={
            "light": [power, brightness],
            "guard": [guard],
            "unmonitored": [guard],
        },
    ) == {
        "temperature": [reading],
        "light": [fresh_power if response_kind == "partial" else power, brightness],
        "guard": [guard],
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("backend", "error_type", "detail"),
    [
        ("GraphQL", AlexapyConnectionError, "connection failed (OSError)"),
        ("Phoenix", AlexapyConnectionError, "connection failed (OSError)"),
        ("Phoenix", TimeoutError, "polling budget"),
    ],
)
async def test_mixed_poll_diagnostics_preserve_samples(
    monkeypatch, caplog, backend, error_type, detail
):
    """Identify backend outages without exposing request or account details."""
    login = SimpleNamespace(email="sample@example.com")
    snapshot = [{"id": "endpoint", "legacyAppliance": {"entityId": "temperature"}}]
    temp = {
        "namespace": "Alexa.TemperatureSensor",
        "name": "temperature",
        "value": 19,
        "timeOfSample": "2026-11-27T12:34:00Z",
    }
    guard = {
        "namespace": "Alexa.SecurityPanelController",
        "name": "armState",
        "value": "DISARMED",
        "timeOfSample": "2026-11-27T12:34:00Z",
    }
    previous = {"temperature": [temp], "guard": [guard]}
    error = error_type(f"token=SECRET_TOKEN, email={login.email}")
    error.__cause__ = OSError("Cookie: SECRET_COOKIE")
    graph = AsyncMock(
        side_effect=error if backend == "GraphQL" else None,
        return_value={"temperature": [temp]},
    )
    phoenix = AsyncMock(
        side_effect=error if backend == "Phoenix" else None,
        return_value={
            "deviceStates": [
                {
                    "entity": {"entityId": "guard"},
                    "capabilityStates": [json.dumps(guard)],
                }
            ]
        },
    )
    monkeypatch.setattr(AlexaAPI, "get_entity_state_gql", graph, raising=False)
    monkeypatch.setattr(AlexaAPI, "get_entity_state", phoenix)
    logger = "custom_components.alexa_media.alexa_entity"
    with caplog.at_level(logging.DEBUG, logger=logger):
        assert (
            await get_entity_data(
                login,
                ["temperature", "guard"],
                endpoints=snapshot,
                previous=previous,
            )
            == previous
        )
    messages = [record for record in caplog.records if record.name == logger]
    assert len(messages) == 1
    assert messages[0].levelno == logging.DEBUG
    assert not messages[0].exc_info
    assert f"{backend} state poll failed for s****e@e*********m" in caplog.text
    assert error_type.__name__ in caplog.text
    assert detail in caplog.text
    assert login.email not in caplog.text
    assert "SECRET_TOKEN" not in caplog.text
    assert "SECRET_COOKIE" not in caplog.text
    graph.assert_awaited_once_with(login, ["temperature"], endpoints=snapshot)
    phoenix.assert_awaited_once_with(login, entity_ids=["guard"])
