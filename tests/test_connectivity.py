"""Regression tests for passive, account-owned Echo connectivity."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.const import EntityCategory
import pytest

from custom_components.alexa_media.binary_sensor import (
    EchoConnectivitySensor,
    async_setup_platform,
    async_unload_entry,
)
from custom_components.alexa_media.connectivity import (
    EchoConnectivityState,
    connectivity_state,
)
from custom_components.alexa_media.const import DOMAIN
from custom_components.alexa_media.coordinator import AlexaMediaCoordinator


def account():
    """An account with no enabled media players."""
    return {
        "login_obj": SimpleNamespace(
            close_requested=False,
            session=SimpleNamespace(closed=False),
            status={"login_successful": True},
        ),
        "coordinator": MagicMock(last_update_success=True),
        "devices": {"media_player": {"A": {"deviceFamily": "ECHO"}}},
        "entities": {"media_player": {}, "binary_sensor": []},
        "options": {},
    }


@pytest.mark.parametrize(
    "online, expected",
    [(True, True), (False, False), (None, None), ("true", None), (1, None)],
)
def test_inventory_boolean_only(online, expected):
    """Missing/malformed online is unknown, never inferred as offline."""
    state = EchoConnectivityState()
    state.inventory([{"serialNumber": "A", "online": online}], state.generation)
    assert state.values["A"] is expected


@pytest.mark.parametrize(
    "status, expected",
    [("ONLINE", True), ("OFFLINE", False), ("UNKNOWN", None), (None, None)],
)
def test_push_explicit_status_only(status, expected):
    """Accept connection status only, without inferring from unrelated fields."""
    state = EchoConnectivityState()
    state.inventory([{"serialNumber": "A"}], 0)
    state.push("A", {"dopplerConnectionState": status, "online": True})
    state.push("unknown", {"dopplerConnectionState": "ONLINE"})
    state.push("A", None)
    state.push("A", {"volumeSetting": 50})
    assert state.values == {"A": expected}


def test_inventory_race_and_recovery():
    """A push beats an in-flight inventory; later fresh inventory can recover."""
    state = EchoConnectivityState()
    state.inventory([{"serialNumber": "A", "online": True}], 0)
    request_generation = state.generation
    state.push("A", {"dopplerConnectionState": "OFFLINE"})
    state.inventory([{"serialNumber": "A", "online": True}], request_generation)
    assert state.values["A"] is False
    state.inventory([{"serialNumber": "A"}], state.generation)
    assert state.values["A"] is False
    state.inventory([{"serialNumber": "A", "online": True}], state.generation)
    assert state.values["A"] is True
    request_generation = state.generation
    state.invalidate()
    state.inventory([{"serialNumber": "A", "online": True}], request_generation)
    assert state.values["A"] is None
    assert not state.account_available
    state.inventory([{"serialNumber": "A", "online": False}], state.generation)
    assert state.values["A"] is False


def test_account_separation_and_identity():
    """Shared physical serials retain separate account states and entity IDs."""
    first, second = account(), account()
    second["second_account_index"] = 1
    a = EchoConnectivitySensor(first["coordinator"], first, "A", "one@example.com")
    b = EchoConnectivitySensor(second["coordinator"], second, "A", "two@example.com")
    connectivity_state(first).inventory([{"serialNumber": "A", "online": False}], 0)
    assert a.is_on is False and b.is_on is None
    assert a.available and b.available
    assert a.unique_id != b.unique_id
    assert a.device_info["identifiers"] == {(DOMAIN, "A")}
    assert b.device_info["identifiers"] == {(DOMAIN, "a_two_example_com")}
    assert a.entity_category is EntityCategory.DIAGNOSTIC
    assert a.entity_registry_enabled_default is False
    assert not a.should_poll


@pytest.mark.parametrize(
    "failure", ["login", "closed", "closing", "coordinator", "account"]
)
def test_account_failure_and_recovery(failure):
    """Offline stays available; account/session failure becomes unavailable."""
    data = account()
    sensor = EchoConnectivitySensor(data["coordinator"], data, "A", "one@example.com")
    state = connectivity_state(data)
    state.inventory([{"serialNumber": "A", "online": False}], 0)
    assert sensor.available and sensor.is_on is False
    if failure == "login":
        data["login_obj"].status["login_successful"] = False
    elif failure == "closed":
        data["login_obj"].session.closed = True
    elif failure == "closing":
        data["login_obj"].close_requested = True
    elif failure == "coordinator":
        data["coordinator"].last_update_success = False
    else:
        state.invalidate()
    assert not sensor.available
    state.invalidate()
    data["login_obj"] = account()["login_obj"]
    data["coordinator"].last_update_success = True
    state.account_available = True
    assert sensor.available and sensor.is_on is None
    state.push("A", {"dopplerConnectionState": "ONLINE"})
    assert sensor.available and sensor.is_on is True


@pytest.mark.asyncio
async def test_discovery_disabled_player_cleanup_zero_requests():
    """Inventory discovery honors filtered devices without needing a player."""
    data = account()
    hass = MagicMock()
    hass.data = {DOMAIN: {"accounts": {"one@example.com": data}}}
    added = MagicMock()
    with (
        patch("custom_components.alexa_media.binary_sensor.async_get_state") as kids,
        patch(
            "custom_components.alexa_media.binary_sensor.add_devices",
            AsyncMock(return_value=True),
        ),
        patch("alexapy.AlexaAPI.get_devices", AsyncMock()) as request,
    ):
        await async_setup_platform(hass, {"email": "one@example.com"}, added)
        sensor = added.call_args.args[0][0]
        assert isinstance(sensor, EchoConnectivitySensor)
        assert len(data["entities"]["binary_sensor"]) == 1
        state = connectivity_state(data)
        state.notify()
        added.assert_called_once()
        # A newly accepted device is discovered; an excluded device is absent
        # from AMP's filtered media_player inventory and cannot create an entity.
        data["devices"]["media_player"]["B"] = {"deviceFamily": "ECHO"}
        data["devices"]["media_player"]["group"] = {"deviceFamily": "WHA"}
        state.notify()
        assert added.call_count == 2
        assert len(data["entities"]["binary_sensor"]) == 2
        kids.return_value.async_start.assert_not_called()
        data["coordinator"].async_add_listener.assert_not_called()
        data["coordinator"].async_request_refresh.assert_not_called()
        request.assert_not_awaited()
        for entity in data["entities"]["binary_sensor"]:
            entity.async_remove = AsyncMock()
        await async_unload_entry(
            hass, SimpleNamespace(data={"email": "one@example.com"})
        )
        assert not state._listeners


def test_coordinator_failure_invalidates_without_requests():
    """Failure clears observations even when all diagnostic sensors are disabled."""
    coordinator = object.__new__(AlexaMediaCoordinator)
    coordinator.echo_connectivity = EchoConnectivityState()
    coordinator.echo_connectivity.inventory([{"serialNumber": "A", "online": True}], 0)
    coordinator.last_update_success = False
    with patch(
        "homeassistant.helpers.update_coordinator.DataUpdateCoordinator.async_update_listeners"
    ):
        coordinator.async_update_listeners()
    assert coordinator.echo_connectivity.values["A"] is None
    assert not coordinator.echo_connectivity.account_available


def test_cached_inventory_never_observes_or_overwrites():
    """Cached boot data creates unknowns and cannot undo push or recover failure."""
    state = EchoConnectivityState()
    inventory = [{"serialNumber": "A", "online": True}]
    state.inventory(inventory, state.generation, cached=True)
    assert state.values["A"] is None
    state.push("A", {"dopplerConnectionState": "OFFLINE"})
    state.inventory(inventory, state.generation, cached=True)
    assert state.values["A"] is False
    state.invalidate()
    state.inventory(inventory, state.generation, cached=True)
    assert state.values["A"] is None


@pytest.mark.asyncio
async def test_entity_listener_removed_on_unload():
    """Enabling/disabling a diagnostic only adds/removes a local callback."""
    data = account()
    sensor = EchoConnectivitySensor(data["coordinator"], data, "A", "one@example.com")
    callbacks = []
    sensor.async_on_remove = callbacks.append
    sensor.async_write_ha_state = MagicMock()
    await sensor.async_added_to_hass()
    state = connectivity_state(data)
    state.inventory([{"serialNumber": "A", "online": True}], 0)
    sensor.async_write_ha_state.assert_called_once()
    for callback in callbacks:
        callback()
    state.push("A", {"dopplerConnectionState": "OFFLINE"})
    sensor.async_write_ha_state.assert_called_once()
    data["coordinator"].async_add_listener.assert_not_called()
    data["coordinator"].async_request_refresh.assert_not_called()


def test_alexapy_no_data_fallback_is_not_fresh():
    """AlexaPy's identity-preserving fallback must not undo an explicit push."""
    state = EchoConnectivityState()
    devices = [{"serialNumber": "A", "online": True}]
    state.inventory(devices, 0, previous_inventory=devices)
    assert state.values["A"] is None
    state.push("A", {"dopplerConnectionState": "OFFLINE"})
    state.inventory(devices, state.generation, previous_inventory=devices)
    assert state.values["A"] is False
    # A successful JSON response produces a distinct list, even if equal.
    state.inventory([dict(devices[0])], state.generation, previous_inventory=devices)
    assert state.values["A"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("registered", [False, True])
async def test_account_unload_removes_discovery_before_platform_reset(registered):
    """Forwarded platform unload cannot leave account discovery subscribed."""
    from custom_components.alexa_media import async_unload_entry as unload_account

    data = account()
    state = connectivity_state(data)
    listener = MagicMock()
    if registered:
        data["connectivity_discovery_unsub"] = state.add_listener(listener)
    hass = MagicMock()
    hass.data = {DOMAIN: {"accounts": {"one@example.com": data}}}

    async def unload_platform(entry, component):
        # Forwarded unload resets the platform without calling its unload hook.
        assert "connectivity_discovery_unsub" not in data
        assert not state._listeners
        data["entities"][component] = []
        state.notify()
        return True

    hass.config_entries.async_forward_entry_unload = AsyncMock(
        side_effect=unload_platform
    )
    with (
        patch("custom_components.alexa_media.close_connections", AsyncMock()),
        patch("custom_components.alexa_media.notify_async_unload_entry", AsyncMock()),
    ):
        assert await unload_account(
            hass,
            SimpleNamespace(data={"email": "one@example.com", "url": "amazon.com"}),
        )
    hass.config_entries.async_forward_entry_unload.assert_awaited()
    listener.assert_not_called()
