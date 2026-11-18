"""Tests for account-scoped virtual device registration and diagnostics."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.exceptions import ConfigEntryNotReady
import pytest

from custom_components.alexa_media import (
    _ensure_account_diagnostic_platforms,
    _register_account_device,
    account_device_identifier,
)
from custom_components.alexa_media.account_auth import (
    publish_authentication,
    subscribe_authentication,
)
from custom_components.alexa_media.const import DOMAIN
from custom_components.alexa_media.sensor import (
    AlexaAccountAuthenticationSensor,
    async_setup_entry,
)


def _entry(entry_id: str, email: str = "first@example.com"):
    return SimpleNamespace(entry_id=entry_id, data={"email": email})


def _account(authenticated: bool = True):
    return {
        "coordinator": MagicMock(),
        "login_obj": SimpleNamespace(status={"login_successful": authenticated}),
    }


def test_account_identifier_is_stable_and_isolated() -> None:
    """A config entry has one stable identity, distinct from other accounts."""
    first = _entry("entry-1")
    second = _entry("entry-2")
    assert account_device_identifier(first) == (DOMAIN, "account_entry-1")
    assert account_device_identifier(first) == account_device_identifier(first)
    assert account_device_identifier(first) != account_device_identifier(second)


def test_account_device_registration_is_idempotent() -> None:
    """Register the account once per config entry using the same identifier."""
    hass = MagicMock()
    registry = MagicMock()
    entry = _entry("entry-1")
    with patch("custom_components.alexa_media.dr.async_get", return_value=registry):
        _register_account_device(hass, entry, entry.data["email"])
        _register_account_device(hass, entry, entry.data["email"])

    assert registry.async_get_or_create.call_count == 2
    expected = {
        "config_entry_id": entry.entry_id,
        "identifiers": {account_device_identifier(entry)},
        "manufacturer": "Amazon",
        "model": "Alexa Account",
        "name": "Alexa Account (entry-1)",
    }
    for call in registry.async_get_or_create.call_args_list:
        assert call.kwargs == expected


def test_account_authentication_state_and_device_info() -> None:
    """The diagnostic reflects account login state, not an Echo's status."""
    entry = _entry("entry-1")
    account = _account()
    sensor = AlexaAccountAuthenticationSensor(account, entry)

    assert sensor.unique_id == "entry-1_account_authentication"
    assert sensor.device_info["identifiers"] == {account_device_identifier(entry)}
    assert sensor.native_value == "authenticated"
    assert sensor.available is True

    account["login_obj"].status["login_successful"] = False
    assert sensor.native_value == "not authenticated"
    account["login_obj"] = None
    assert sensor.native_value == "not authenticated"


@pytest.mark.asyncio
async def test_account_sensor_loads_without_echo_entities() -> None:
    """Load account diagnostics without any discovered Echoes or filters."""
    entry = _entry("entry-1")
    account = _account()
    hass = SimpleNamespace(data={DOMAIN: {"accounts": {entry.data["email"]: account}}})
    add_entities = MagicMock()

    with (
        patch(
            "custom_components.alexa_media.sensor.async_setup_platform",
            new_callable=AsyncMock,
            return_value=True,
        ) as platform,
        patch(
            "custom_components.alexa_media.sensor.config_entry_config",
            return_value={"include_devices": ["Another Echo"]},
        ),
    ):
        result = await async_setup_entry(hass, entry, add_entities)

    assert result is True
    platform.assert_awaited_once()
    add_entities.assert_called_once()
    sensors = add_entities.call_args.args[0]
    assert len(sensors) == 1
    assert isinstance(sensors[0], AlexaAccountAuthenticationSensor)
    assert sensors[0].device_info["identifiers"] == {account_device_identifier(entry)}


@pytest.mark.asyncio
async def test_account_sensor_not_added_if_platform_setup_fails() -> None:
    """A failed sensor setup must not register a diagnostic entity."""
    entry = _entry("entry-1")
    add_entities = MagicMock()

    with (
        patch(
            "custom_components.alexa_media.sensor.async_setup_platform",
            new_callable=AsyncMock,
            return_value=False,
        ),
        patch(
            "custom_components.alexa_media.sensor.config_entry_config",
            return_value={},
        ),
    ):
        result = await async_setup_entry(SimpleNamespace(), entry, add_entities)

    assert result is False
    add_entities.assert_not_called()


@pytest.mark.asyncio
async def test_account_sensor_waits_for_coordinator() -> None:
    """An account not yet initialized must not create a broken diagnostic."""
    entry = _entry("entry-1")
    account = {"entities": {}}
    hass = SimpleNamespace(data={DOMAIN: {"accounts": {entry.data["email"]: account}}})
    add_entities = MagicMock()
    with (
        patch(
            "custom_components.alexa_media.sensor.async_setup_platform",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "custom_components.alexa_media.sensor.config_entry_config",
            return_value={},
        ),
    ):
        assert await async_setup_entry(hass, entry, add_entities) is True
    add_entities.assert_not_called()


def test_multiple_account_sensors_are_isolated() -> None:
    """Each account diagnostic follows only its own login and coordinator."""
    first = _entry("entry-1", "first@example.com")
    second = _entry("entry-2", "second@example.com")
    first_account = _account()
    second_account = _account(False)
    first_sensor = AlexaAccountAuthenticationSensor(first_account, first)
    second_sensor = AlexaAccountAuthenticationSensor(second_account, second)

    assert first_sensor.coordinator is first_account["coordinator"]
    assert second_sensor.coordinator is second_account["coordinator"]
    assert first_sensor.device_info != second_sensor.device_info
    assert first_sensor.native_value == "authenticated"
    assert second_sensor.native_value == "not authenticated"


def test_authentication_notifications_follow_changes_and_unsubscribe() -> None:
    """The diagnostic is updated when login changes without coordinator polling."""
    account = _account()
    callback = MagicMock()
    unsubscribe = subscribe_authentication(account, callback)

    publish_authentication(account)
    callback.assert_called_once()  # initialize the first observed state
    callback.reset_mock()
    publish_authentication(account)
    callback.assert_not_called()

    account["login_obj"].status["login_successful"] = False
    publish_authentication(account)
    callback.assert_called_once()
    callback.reset_mock()

    account["login_obj"].status["login_successful"] = True
    publish_authentication(account)
    callback.assert_called_once()

    unsubscribe()
    callback.reset_mock()
    account["login_obj"].status["login_successful"] = False
    publish_authentication(account)
    callback.assert_not_called()


@pytest.mark.asyncio
async def test_authentication_entity_subscribes_and_cleans_up() -> None:
    """The entity unsubscribes when Home Assistant removes it."""
    account = _account()
    sensor = AlexaAccountAuthenticationSensor(account, _entry("entry-1"))
    unsubs = []
    sensor.async_on_remove = unsubs.append
    with patch(
        "homeassistant.helpers.update_coordinator.CoordinatorEntity.async_added_to_hass",
        new_callable=AsyncMock,
    ):
        with patch.object(sensor, "async_write_ha_state") as update:
            await sensor.async_added_to_hass()
            assert len(unsubs) == 1
            publish_authentication(account)
            update.assert_called_once()
            unsubs.pop()()
            account["login_obj"].status["login_successful"] = False
            publish_authentication(account)
            update.assert_called_once()


@pytest.mark.asyncio
async def test_diagnostic_forward_skips_loaded_platforms() -> None:
    """Account-only startup forwards both platforms once, not media_player."""
    account = {}
    entry = _entry("entry-1")
    platforms = SimpleNamespace()
    hass = SimpleNamespace(config_entries=platforms)

    async def forward(_entry, names):
        assert names == ["sensor", "binary_sensor"]
        account.setdefault("account_diagnostic_platforms_loaded", set()).update(names)

    platforms.async_forward_entry_setups = AsyncMock(side_effect=forward)
    platforms.async_forward_entry_unload = AsyncMock()

    await _ensure_account_diagnostic_platforms(hass, entry, account)
    await _ensure_account_diagnostic_platforms(hass, entry, account)

    platforms.async_forward_entry_setups.assert_awaited_once()
    platforms.async_forward_entry_unload.assert_not_awaited()
    assert account["account_diagnostic_platforms_loaded"] == {"sensor", "binary_sensor"}


@pytest.mark.asyncio
async def test_partial_diagnostic_forward_unloads_only_failed_platform() -> None:
    """A failed binary sensor forward is cleaned up and retried independently."""
    entry = _entry("entry-1")
    account = {}
    platforms = SimpleNamespace()
    hass = SimpleNamespace(config_entries=platforms)
    attempts = []

    async def forward(_entry, names):
        attempts.append(names)
        loaded = account.setdefault("account_diagnostic_platforms_loaded", set())
        if len(attempts) == 1:
            loaded.add("sensor")
        else:
            loaded.update(names)

    platforms.async_forward_entry_setups = AsyncMock(side_effect=forward)
    platforms.async_forward_entry_unload = AsyncMock(return_value=True)

    with pytest.raises(ConfigEntryNotReady, match="binary_sensor"):
        await _ensure_account_diagnostic_platforms(hass, entry, account)

    platforms.async_forward_entry_unload.assert_awaited_once_with(
        entry, "binary_sensor"
    )
    assert account["account_diagnostic_platforms_loaded"] == {"sensor"}

    await _ensure_account_diagnostic_platforms(hass, entry, account)
    assert attempts == [
        ["sensor", "binary_sensor"],
        ["binary_sensor"],
    ]
    assert account["account_diagnostic_platforms_loaded"] == {"sensor", "binary_sensor"}
