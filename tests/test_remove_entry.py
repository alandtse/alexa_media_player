"""Tests for secure-entry teardown (best-effort deregister + store delete)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.alexa_media import async_remove_entry
from custom_components.alexa_media.const import CONF_SECURE


def _secure_entry():
    entry = MagicMock()
    entry.entry_id = "entry123"
    entry.data = {"email": "user@example.com", CONF_SECURE: True}
    return entry


@pytest.mark.asyncio
async def test_remove_deregisters_and_deletes_store():
    hass = MagicMock()
    store = AsyncMock()
    store.async_load = AsyncMock(
        return_value={"refresh_token": "r", "mac_dms": {"k": "v"}, "serial": "S"}
    )
    manager = AsyncMock()
    with (
        patch(
            "custom_components.alexa_media.SecureCredentialStore", return_value=store
        ),
        patch("alexapy.TokenManager", return_value=manager),
        patch("alexapy.DeviceCredentials"),
    ):
        assert await async_remove_entry(hass, _secure_entry()) is True

    manager.async_refresh_access_token.assert_awaited_once()
    manager.async_deregister.assert_awaited_once()
    store.async_remove.assert_awaited_once()


@pytest.mark.asyncio
async def test_remove_survives_deregister_failure():
    hass = MagicMock()
    store = AsyncMock()
    store.async_load = AsyncMock(return_value={"refresh_token": "r"})
    manager = AsyncMock()
    manager.async_refresh_access_token = AsyncMock(side_effect=RuntimeError("boom"))
    with (
        patch(
            "custom_components.alexa_media.SecureCredentialStore", return_value=store
        ),
        patch("alexapy.TokenManager", return_value=manager),
        patch("alexapy.DeviceCredentials"),
    ):
        # Amazon failure must never block removal.
        assert await async_remove_entry(hass, _secure_entry()) is True
    store.async_remove.assert_awaited_once()


@pytest.mark.asyncio
async def test_remove_without_stored_creds_still_deletes_store():
    hass = MagicMock()
    store = AsyncMock()
    store.async_load = AsyncMock(return_value=None)
    with patch(
        "custom_components.alexa_media.SecureCredentialStore", return_value=store
    ):
        assert await async_remove_entry(hass, _secure_entry()) is True
    store.async_remove.assert_awaited_once()
