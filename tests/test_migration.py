"""Tests for the lazy, non-destructive secure-schema migration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.alexa_media import _cleanup_legacy_secrets, async_migrate_entry
from custom_components.alexa_media.const import CONF_OAUTH, CONF_SECURE


def _entry(version=1, data=None):
    entry = MagicMock()
    entry.version = version
    entry.entry_id = "entry123"
    entry.data = data if data is not None else {}
    return entry


@pytest.mark.asyncio
async def test_migrate_copies_tokens_and_keeps_legacy():
    hass = MagicMock()
    hass.config_entries.async_update_entry = MagicMock()
    entry = _entry(
        data={
            "email": "user@example.com",
            "url": "amazon.com",
            "password": "secret",
            "otp_secret": "SEED",
            CONF_OAUTH: {"refresh_token": "r", "mac_dms": {"k": "v"}},
        }
    )
    store = AsyncMock()
    with patch(
        "custom_components.alexa_media.SecureCredentialStore", return_value=store
    ):
        assert await async_migrate_entry(hass, entry) is True

    # Tokens copied to the protected store, flagged pending until validated.
    save_kwargs = store.async_save.call_args.kwargs
    assert save_kwargs["pending_validation"] is True
    # Entry marked secure and version bumped, but legacy secrets NOT yet removed.
    update_kwargs = hass.config_entries.async_update_entry.call_args.kwargs
    assert update_kwargs["data"][CONF_SECURE] is True
    assert update_kwargs["version"] == 2
    assert update_kwargs["data"]["password"] == "secret"


@pytest.mark.asyncio
async def test_migrate_without_token_marks_secure_for_reauth():
    hass = MagicMock()
    hass.config_entries.async_update_entry = MagicMock()
    entry = _entry(data={"email": "user@example.com", "url": "amazon.com"})
    with patch("custom_components.alexa_media.SecureCredentialStore") as store_cls:
        assert await async_migrate_entry(hass, entry) is True
        store_cls.assert_not_called()
    update_kwargs = hass.config_entries.async_update_entry.call_args.kwargs
    assert update_kwargs["data"][CONF_SECURE] is True
    assert update_kwargs["version"] == 2


@pytest.mark.asyncio
async def test_migrate_noop_when_current_version():
    hass = MagicMock()
    hass.config_entries.async_update_entry = MagicMock()
    entry = _entry(version=2)
    assert await async_migrate_entry(hass, entry) is True
    hass.config_entries.async_update_entry.assert_not_called()


@pytest.mark.asyncio
async def test_cleanup_removes_legacy_secrets():
    hass = MagicMock()
    hass.config_entries.async_update_entry = MagicMock()
    hass.config.path = MagicMock(return_value="/nonexistent/cookie.pickle")
    entry = _entry(
        data={
            "email": "user@example.com",
            "url": "amazon.com",
            "password": "secret",
            "otp_secret": "SEED",
            CONF_OAUTH: {"refresh_token": "r"},
            CONF_SECURE: True,
        }
    )
    with patch("custom_components.alexa_media.os.path.exists", return_value=False):
        await _cleanup_legacy_secrets(hass, entry)
    new_data = hass.config_entries.async_update_entry.call_args.kwargs["data"]
    assert "password" not in new_data
    assert "otp_secret" not in new_data
    assert CONF_OAUTH not in new_data
    assert new_data[CONF_SECURE] is True
