"""Tests that a get_devices timeout never prunes the device registry."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from alexapy import AlexaAPI
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_URL
from homeassistant.helpers import device_registry as dr
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.alexa_media.const import (
    CONF_EXCLUDE_DEVICES,
    CONF_INCLUDE_DEVICES,
    CONF_SCAN_INTERVAL,
    DATA_ALEXAMEDIA,
    DOMAIN,
)

EMAIL = "test@example.com"
DEVICE_SERIAL = "G090XXXXXXXXXXXX"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Allow Home Assistant to load the custom integration."""
    yield


class FakeAlexaLogin:
    """Network-free stand-in for alexapy.AlexaLogin."""

    def __init__(self, url, email, **kwargs):
        self.url = url
        self.email = email
        self.status = {}
        self.stats = {"login_timestamp": datetime(1, 1, 1), "api_calls": 0}
        self._session = None
        self.session = MagicMock(closed=False)
        self.close_requested = False
        self.access_token = None
        self.close = AsyncMock()
        self.save_cookiefile = AsyncMock()
        self.reset = AsyncMock()

    async def load_cookie(self):
        """Report that no cookie is stored."""
        return None

    async def login(self, cookies=None, **kwargs):
        """Log in successfully."""
        self.status["login_successful"] = True


@pytest.fixture
def amazon_api():
    """Patch the Amazon login layer and every Alexa API call the first refresh makes."""
    with (
        patch("custom_components.alexa_media.AlexaLogin", FakeAlexaLogin),
        patch(
            "custom_components.alexa_media.HTTP2EchoClient",
            MagicMock(return_value=MagicMock(async_run=AsyncMock())),
        ),
        patch.object(AlexaAPI, "get_devices", AsyncMock(return_value=[])) as devices,
        patch.object(AlexaAPI, "get_bluetooth", AsyncMock(return_value={})),
        patch.object(AlexaAPI, "get_device_preferences", AsyncMock(return_value={})),
        patch.object(AlexaAPI, "get_dnd_state", AsyncMock(return_value={})),
        patch.object(AlexaAPI, "get_notification_states", AsyncMock(return_value=[])),
        patch.object(AlexaAPI, "get_authentication", AsyncMock(return_value={})),
        patch.object(AlexaAPI, "get_entity_state_gql", None, create=True),
        patch.object(
            AlexaAPI, "get_network_details", AsyncMock(return_value={})
        ) as network_details,
    ):
        yield devices, network_details


def _sample_echo_device():
    """Return a minimal Echo device payload from AlexaAPI.get_devices."""
    return {
        "serialNumber": DEVICE_SERIAL,
        "accountName": "Kitchen Echo",
        "capabilities": ["MUSIC_SKILL"],
        "deviceFamily": "ECHO",
        "deviceType": "A3RMGO6LYLH7YN",
        "softwareVersion": "1",
        "online": True,
        "auth_info": None,
    }


def _entry_with_registered_device(hass):
    """Add a config entry that already owns a device, as after a restart."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_EMAIL: EMAIL,
            CONF_PASSWORD: "password",
            CONF_URL: "amazon.com",
            CONF_INCLUDE_DEVICES: "",
            CONF_EXCLUDE_DEVICES: "",
            CONF_SCAN_INTERVAL: 60,
        },
    )
    entry.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, DEVICE_SERIAL)},
        name="Kitchen Echo",
    )
    return entry, device


async def test_get_devices_timeout_keeps_registered_devices(hass, amazon_api):
    """A get_devices timeout must retry setup, not wipe the device registry."""
    devices, _ = amazon_api
    entry, device = _entry_with_registered_device(hass)
    devices.side_effect = asyncio.TimeoutError

    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    devices.assert_awaited()
    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert dr.async_get(hass).async_get(device.id) is not None


@pytest.mark.parametrize("network_response", [None, {}, []])
async def test_network_discovery_failure_keeps_registered_devices(
    hass, amazon_api, network_response
):
    """A failed/empty network discovery must keep non-media_player devices intact."""
    devices, network_details = amazon_api
    entry, echo_device = _entry_with_registered_device(hass)
    aqm_device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "AQMSERIAL0000001")},
        name="Kitchen Air Quality Monitor",
    )
    devices.return_value = [_sample_echo_device()]
    network_details.return_value = network_response

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
        AsyncMock(return_value=None),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert hass.data[DATA_ALEXAMEDIA]["accounts"][EMAIL]["should_get_network"] is True
    registry = dr.async_get(hass)
    assert registry.async_get(echo_device.id) is not None
    assert registry.async_get(aqm_device.id) is not None


async def test_network_discovery_failure_preserves_existing_entities(hass, amazon_api):
    """Failed force-rediscovery must preserve existing entity discovery and state."""
    devices, network_details = amazon_api
    entry, _ = _entry_with_registered_device(hass)
    aqm_appliance = {
        "entityId": "aqm-entity",
        "applianceId": "aqm-appliance",
        "friendlyName": "Kitchen Air Quality Monitor",
        "modelName": "AQM",
        "manufacturerName": "Amazon",
        "friendlyDescription": "Amazon Indoor Air Quality Monitor",
        "applianceTypes": ["AIR_QUALITY_MONITOR"],
        "alexaDeviceIdentifierList": [{"dmsDeviceSerialNumber": "AQMSERIAL0000001"}],
        "capabilities": [
            {
                "interfaceName": "Alexa.RangeController",
                "instance": "9",
                "properties": {
                    "supported": [{"name": "rangeValue"}],
                    "retrievable": True,
                    "proactivelyReported": True,
                },
            }
        ],
    }
    devices.return_value = [_sample_echo_device()]
    network_details.return_value = [aqm_appliance]

    first_entity_state = {"aqm-entity": [{"name": "rangeValue", "value": 85}]}
    retry_entity_state = {"aqm-entity": [{"name": "rangeValue", "value": 91}]}
    with (
        patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
            AsyncMock(return_value=None),
        ),
        patch(
            "custom_components.alexa_media.get_entity_data",
            AsyncMock(side_effect=[first_entity_state, retry_entity_state]),
        ) as mock_entity_data,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        account = hass.data[DATA_ALEXAMEDIA]["accounts"][EMAIL]
        assert account["should_get_network"] is False
        assert account["coordinator"].data == first_entity_state
        discovered_aiaqm = list(account["devices"]["aiaqm"])
        assert len(discovered_aiaqm) == 1

        # Simulate a later poll after force_network_discovery where get_devices_gql fails,
        # while an enabled sensor still monitors entity state.
        aqm_device = dr.async_get(hass).async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, "AQMSERIAL0000001")},
            name="Kitchen Air Quality Monitor",
        )
        account["entities"]["sensor"]["AQMSERIAL0000001"] = {
            "Air_Quality": {
                "aqm-entity_voc": MagicMock(
                    enabled=True, alexa_entity_id="aqm-entity", device_info=None
                )
            }
        }
        account["should_get_network"] = True
        network_details.return_value = None
        await account["coordinator"].async_refresh()
        await hass.async_block_till_done()

    assert account["should_get_network"] is True
    assert account["devices"]["aiaqm"] == discovered_aiaqm
    assert dr.async_get(hass).async_get(aqm_device.id) is not None
    # Initial setup + monitored-entity fetch during retry; failed discovery must not call get_entity_data([]).
    assert mock_entity_data.await_count == 2
    assert mock_entity_data.await_args_list[1].args[1] == ["aqm-entity"]
    assert account["coordinator"].data == retry_entity_state


async def test_successful_discovery_prunes_stale_devices(hass, amazon_api):
    """Stale devices are still pruned when network discovery succeeds."""
    devices, network_details = amazon_api
    entry, echo_device = _entry_with_registered_device(hass)
    stale_device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "STALE0000000001")},
        name="Removed Smart Plug",
    )
    devices.return_value = [_sample_echo_device()]
    network_details.return_value = [
        {
            "entityId": "light-1",
            "applianceId": "appliance-1",
            "friendlyName": "Hall Light",
            "modelName": "Smart Light",
            "manufacturerName": "Philips",
            "applianceTypes": ["LIGHT"],
            "capabilities": [],
        }
    ]

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
        AsyncMock(return_value=None),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert hass.data[DATA_ALEXAMEDIA]["accounts"][EMAIL]["should_get_network"] is False
    registry = dr.async_get(hass)
    assert registry.async_get(echo_device.id) is not None
    assert registry.async_get(stale_device.id) is None


@pytest.fixture
def aqm_endpoint():
    """Return an AQM discovery row with an explicit GraphQL ID."""
    return {
        "id": "aqm-endpoint",
        "legacyAppliance": {
            "entityId": "aqm-entity",
            "applianceId": "aqm-appliance",
            "friendlyName": "Kitchen Air Quality Monitor",
            "modelName": "AQM",
            "manufacturerName": "Amazon",
            "friendlyDescription": "Amazon Indoor Air Quality Monitor",
            "applianceTypes": ["AIR_QUALITY_MONITOR"],
            "alexaDeviceIdentifierList": [
                {"dmsDeviceSerialNumber": "AQMSERIAL0000001"}
            ],
            "capabilities": [
                {
                    "interfaceName": "Alexa.RangeController",
                    "instance": "9",
                    "properties": {
                        "supported": [{"name": "rangeValue"}],
                        "retrievable": True,
                        "proactivelyReported": True,
                    },
                }
            ],
        },
    }


@pytest.mark.parametrize("auth_interruption", [False, True])
async def test_graphql_snapshot_survives_failed_rediscovery(
    hass, amazon_api, auth_interruption, aqm_endpoint
):
    """Use the same account snapshot for initial and subsequent sensor polling."""
    devices, network_details = amazon_api
    entry, _ = _entry_with_registered_device(hass)
    devices.return_value = [_sample_echo_device()]
    discovery = AsyncMock(side_effect=[[aqm_endpoint], None])
    first_state = {
        "namespace": "Alexa.TemperatureSensor",
        "name": "temperature",
        "value": {"value": 21, "scale": "CELSIUS"},
    }
    updated_state = {**first_state, "value": {"value": 22, "scale": "CELSIUS"}}
    omitted_metric = {
        "namespace": "Alexa.RangeController",
        "name": "rangeValue",
        "instance": "9",
        "value": 35,
        "timeOfSample": "2026-11-27T12:34:00Z",
    }
    initial = [first_state, omitted_metric]
    poll = AsyncMock(
        side_effect=[{"aqm-entity": initial}, {"aqm-entity": [updated_state]}]
    )
    with (
        patch.object(AlexaAPI, "get_devices_gql", discovery),
        patch.object(AlexaAPI, "get_entity_state_gql", poll, create=True),
        patch.object(AlexaAPI, "get_entity_state", AsyncMock()) as phoenix,
        patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
            AsyncMock(return_value=None),
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        account = hass.data[DATA_ALEXAMEDIA]["accounts"][EMAIL]
        coordinator = account["coordinator"]
        assert coordinator.data == {"aqm-entity": initial}
        if auth_interruption:
            account["login_obj"].status["login_successful"] = False
            await coordinator.async_refresh()
            assert coordinator.data is None
            assert poll.await_count == 1
            account["login_obj"].status["login_successful"] = True
        account["entities"]["sensor"]["AQMSERIAL0000001"] = {
            "Temperature": MagicMock(enabled=True, alexa_entity_id="aqm-entity")
        }
        account["should_get_network"] = True
        await coordinator.async_refresh()
        await hass.async_block_till_done()
        assert coordinator.data == {"aqm-entity": [updated_state, omitted_metric]}
        assert account["should_get_network"] is True
        assert discovery.await_count == 2
        network_details.assert_not_awaited()
        phoenix.assert_not_awaited()
        assert poll.await_count == 2
        for call in poll.await_args_list:
            assert call.args == (account["login_obj"], ["aqm-entity"])
            assert call.kwargs == {
                "endpoints": [
                    {
                        "id": "aqm-endpoint",
                        "legacyAppliance": {"entityId": "aqm-entity"},
                    }
                ]
            }


@pytest.mark.parametrize("first_to_finish", [0, 1])
@pytest.mark.parametrize("conflicting_sample", [False, True])
async def test_overlapping_graphql_polls_keep_newest_samples(
    hass, amazon_api, aqm_endpoint, first_to_finish, conflicting_sample
):
    """Overlapping partial replies publish the newest sample for each metric."""
    devices, _ = amazon_api
    entry, _ = _entry_with_registered_device(hass)
    devices.return_value = [_sample_echo_device()]

    def sample(instance, value, time):
        return {
            "namespace": "Alexa.RangeController",
            "name": "rangeValue",
            "instance": instance,
            "value": value,
            "timeOfSample": time,
        }

    entity_id = "aqm-entity"
    old_pm = sample("9", 10, "2026-11-27T12:00:00Z")
    old_voc = sample("3", 20, "2026-11-27T12:00:00Z")
    new_pm = sample("9", 30, "2026-11-27T12:02:00Z")
    new_voc = sample("3", 40, "2026-11-27T12:03:00Z")
    replies = [[new_pm], [new_voc]]
    if conflicting_sample:
        # This arrives from a fresh request, but Amazon sampled it earlier.
        replies[1].append(sample(9, 15, "2026-11-27T13:01:00+01:00"))

    started = [asyncio.Event(), asyncio.Event()]
    release = [asyncio.Event(), asyncio.Event()]
    next_poll = 0

    async def poll(*args, **kwargs):
        nonlocal next_poll
        if next_poll == 0:
            next_poll += 1
            return {entity_id: [old_pm, old_voc]}
        index = next_poll - 1
        next_poll += 1
        started[index].set()
        await release[index].wait()
        return {entity_id: replies[index]}

    with (
        patch.object(
            AlexaAPI, "get_devices_gql", AsyncMock(return_value=[aqm_endpoint])
        ),
        patch.object(AlexaAPI, "get_entity_state_gql", poll, create=True),
        patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
            AsyncMock(return_value=None),
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        account = hass.data[DATA_ALEXAMEDIA]["accounts"][EMAIL]
        coordinator = account["coordinator"]
        account["entities"]["sensor"]["AQMSERIAL0000001"] = {
            "Temperature": MagicMock(enabled=True, alexa_entity_id=entity_id)
        }

        async with asyncio.timeout(5), asyncio.TaskGroup() as tasks:
            # Older Home Assistant releases allow refreshes to overlap.
            refreshes = [tasks.create_task(coordinator._async_refresh())]
            await started[0].wait()
            refreshes.append(tasks.create_task(coordinator._async_refresh()))
            await started[1].wait()
            release[first_to_finish].set()
            await refreshes[first_to_finish]
            release[1 - first_to_finish].set()

        assert {
            str(state["instance"]): state for state in coordinator.data[entity_id]
        } == {
            "9": new_pm,
            "3": new_voc,
        }
