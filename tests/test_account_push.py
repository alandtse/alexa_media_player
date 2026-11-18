"""Tests for account-wide HTTP/2 push connectivity diagnostics."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.alexa_media.account_push import (
    abandon_push_attempt,
    begin_push_attempt,
    close_account_push,
    owns_push_attempt,
    reconnect_account_push,
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


def test_push_callbacks_ignore_previous_account_or_connection() -> None:
    """A callback from an old load cannot modify a replacement's state."""
    old = {"push_attempt": object(), "push_connected": True}
    new = {"push_attempt": object(), "push_connected": True}
    hass = SimpleNamespace(data={DOMAIN: {"accounts": {"a@example.com": old}}})
    old_attempt = old["push_attempt"]

    assert owns_push_attempt(hass, "a@example.com", old, old_attempt)

    old["push_attempt"] = object()
    assert not owns_push_attempt(hass, "a@example.com", old, old_attempt)

    hass.data[DOMAIN]["accounts"]["a@example.com"] = new
    assert not owns_push_attempt(hass, "a@example.com", old, old["push_attempt"])
    active_attempt = new["push_attempt"]
    assert owns_push_attempt(hass, "a@example.com", new, active_attempt)

    new["push_attempt"] = None  # unload before the transport closes
    assert not owns_push_attempt(hass, "a@example.com", new, active_attempt)


def test_failed_attempt_closes_transport_without_invalidating_replacement() -> None:
    """Failure of the old attempt must not turn the newer attempt off."""
    account = {}
    old = begin_push_attempt(account)
    old_client = MagicMock()
    new = begin_push_attempt(account)
    set_push_connected(account, True)

    abandon_push_attempt(account, old, old_client)
    assert account["push_attempt"] is new
    assert account["push_connected"] is True
    old_client.on_close.assert_called_once()

    new_client = MagicMock()
    abandon_push_attempt(account, new, new_client)
    assert account["push_attempt"] is None
    assert account["push_connected"] is False
    new_client.on_close.assert_called_once()


def test_account_teardown_closes_own_transport_and_invalidates_callbacks() -> None:
    """Account shutdown must release the transport before removing the entry."""
    client = MagicMock()
    account = {"http2": client}
    token = begin_push_attempt(account)
    set_push_connected(account, True)

    close_account_push(account)
    assert account["http2"] is None
    assert account["push_attempt"] is None
    assert account["push_connected"] is False
    client.on_close.assert_called_once()
    assert token is not account["push_attempt"]


@pytest.mark.asyncio
async def test_reconnect_aborts_during_backoff_when_entry_unloads() -> None:
    """A callback already sleeping must not reconnect a removed account."""
    email = "a@example.com"
    account = {"http2error": 0, "http2_lastattempt": 0, "http2": None}
    login = SimpleNamespace(close_requested=False, status={"login_successful": True})
    hass = SimpleNamespace(data={DOMAIN: {"accounts": {email: account}}})
    connect = AsyncMock(return_value=None)

    async def during_backoff(_delay):
        account["push_attempt"] = None
        hass.data[DOMAIN]["accounts"].pop(email)

    result = await reconnect_account_push(
        hass, email, account, login, connect, sleep=during_backoff, clock=lambda: 100
    )
    assert result is None
    connect.assert_awaited_once()
    assert account["http2"] is None


@pytest.mark.asyncio
async def test_reconnect_discards_client_after_entry_replacement() -> None:
    """A reconnect completing after reload cannot replace its successor."""
    email = "a@example.com"
    account = {"http2error": 0, "http2_lastattempt": 0, "http2": None}
    replacement = {"http2": object()}
    login = SimpleNamespace(close_requested=False, status={"login_successful": True})
    hass = SimpleNamespace(data={DOMAIN: {"accounts": {email: account}}})
    client = MagicMock()
    token = object()
    client._amp_attempt = token

    async def delayed_connect():
        account["push_attempt"] = token
        hass.data[DOMAIN]["accounts"][email] = replacement
        return client

    result = await reconnect_account_push(
        hass, email, account, login, delayed_connect, clock=lambda: 100
    )
    assert result is None
    client.on_close.assert_called_once()
    assert replacement["http2"] is not client
    assert account["http2"] is None


@pytest.mark.asyncio
async def test_active_reconnect_retains_new_client() -> None:
    """Reconnecting an unchanged account installs the new transport."""
    email = "a@example.com"
    account = {"http2error": 0, "http2_lastattempt": 0, "http2": None}
    login = SimpleNamespace(close_requested=False, status={"login_successful": True})
    hass = SimpleNamespace(data={DOMAIN: {"accounts": {email: account}}})
    client = MagicMock()

    async def connect():
        client._amp_attempt = begin_push_attempt(account)
        return client

    assert await reconnect_account_push(
        hass, email, account, login, connect, clock=lambda: 100
    ) is True
    assert account["http2"] is client
