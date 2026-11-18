"""Tests for account-scoped virtual device registration and diagnostics."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.alexa_media import (
    _register_account_device,
    account_device_identifier,
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
    with patch(
        "custom_components.alexa_media.dr.async_get", return_value=registry
    ):
        _register_account_device(hass, entry, entry.data["email"])
        _register_account_device(hass, entry, entry.data["email"])

    assert registry.async_get_or_create.call_count == 2
    expected = {
        "config_entry_id": entry.entry_id,
        "identifiers": {account_device_identifier(entry)},
        "manufacturer": "Amazon",
        "model": "Alexa Account",
        "name": "Alexa Account (first@example.com)",
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
    hass = SimpleNamespace(
        data={DOMAIN: {"accounts": {entry.data["email"]: account}}}
    )
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
    assert sensors[0].device_info["identifiers"] == {
        account_device_identifier(entry)
    }


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
