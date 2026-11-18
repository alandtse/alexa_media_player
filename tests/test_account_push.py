"""Tests for account-wide HTTP/2 push connectivity diagnostics."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.alexa_media.account_push import (
    set_push_connected,
    subscribe_push_connected,
)
from custom_components.alexa_media.binary_sensor import (
    AlexaAccountPushSensor,
    async_setup_entry,
)
from custom_components.alexa_media.const import DOMAIN


def _entry(identifier: str, email: str):
    return SimpleNamespace(entry_id=identifier, data={"email": email})


def test_push_transitions_and_idempotence() -> None:
    """Only actual open/close transitions notify subscribers."""
    account = {}
    callback = MagicMock()
    unsubscribe = subscribe_push_connected(account, callback)

    assert account.get("push_connected", False) is False
    set_push_connected(account, True)
    assert account["push_connected"] is True
    set_push_connected(account, True)
    callback.assert_called_once()

    set_push_connected(account, False)
    assert account["push_connected"] is False
    assert callback.call_count == 2
    unsubscribe()
    set_push_connected(account, True)
    assert callback.call_count == 2


def test_push_accounts_do_not_leak() -> None:
    """One account's events cannot change another account's sensor."""
    first_account, second_account = {}, {}
    first = AlexaAccountPushSensor(first_account, _entry("entry-1", "a@example.com"))
    second = AlexaAccountPushSensor(second_account, _entry("entry-2", "b@example.com"))

    assert first.is_on is False
    assert second.is_on is False
    assert first.unique_id != second.unique_id
    assert first.device_info != second.device_info

    set_push_connected(first_account, True)
    assert first.is_on is True
    assert second.is_on is False
    set_push_connected(first_account, False)
    assert first.is_on is False


@pytest.mark.asyncio
async def test_push_entity_subscribes_and_unregisters() -> None:
    """State callbacks update the entity and are removed on unload."""
    account = {}
    sensor = AlexaAccountPushSensor(account, _entry("entry-1", "a@example.com"))
    unsubs = []
    sensor.async_on_remove = unsubs.append
    with patch(
        "homeassistant.components.binary_sensor.BinarySensorEntity.async_added_to_hass",
        new_callable=AsyncMock,
    ):
        with patch.object(sensor, "async_write_ha_state") as write:
            await sensor.async_added_to_hass()
            set_push_connected(account, True)
            write.assert_called_once()
            assert len(unsubs) == 1
            unsubs.pop()()
            set_push_connected(account, False)
            write.assert_called_once()


@pytest.mark.asyncio
async def test_push_entity_setup_even_without_echoes() -> None:
    """Account diagnostic loads regardless of Echo inventory or name filters."""
    entry = _entry("entry-1", "a@example.com")
    account = {"push_connected": False}
    hass = SimpleNamespace(data={DOMAIN: {"accounts": {entry.data["email"]: account}}})
    add_entities = MagicMock()
    with (
        patch(
            "custom_components.alexa_media.binary_sensor.async_setup_platform",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "custom_components.alexa_media.binary_sensor.config_entry_config",
            return_value={"include_devices": ["Only This Echo"]},
        ),
    ):
        assert await async_setup_entry(hass, entry, add_entities) is True

    add_entities.assert_called_once()
    sensor = add_entities.call_args.args[0][0]
    assert isinstance(sensor, AlexaAccountPushSensor)
    assert sensor.is_on is False


@pytest.mark.asyncio
async def test_push_entity_not_added_after_failed_platform_setup() -> None:
    """A platform failure must not add a half-initialized diagnostic."""
    entry = _entry("entry-1", "a@example.com")
    add_entities = MagicMock()
    with (
        patch(
            "custom_components.alexa_media.binary_sensor.async_setup_platform",
            new_callable=AsyncMock,
            return_value=False,
        ),
        patch(
            "custom_components.alexa_media.binary_sensor.config_entry_config",
            return_value={},
        ),
    ):
        assert await async_setup_entry(SimpleNamespace(), entry, add_entities) is False
    add_entities.assert_not_called()
