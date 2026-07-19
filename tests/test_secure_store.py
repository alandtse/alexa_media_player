"""Tests for the protected credential store."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.alexa_media.secure_store import (
    CREDENTIAL_KEYS,
    SecureCredentialStore,
)


def _store_with_backing():
    backing = MagicMock()
    backing.async_load = AsyncMock(return_value=None)
    backing.async_save = AsyncMock()
    backing.async_remove = AsyncMock()
    backing.key = "alexa_media.secure_credentials.entry123"
    with patch(
        "custom_components.alexa_media.secure_store.Store", return_value=backing
    ):
        store = SecureCredentialStore(MagicMock(), "entry123")
    return store, backing


def test_store_created_private_and_atomic():
    with patch("custom_components.alexa_media.secure_store.Store") as store_cls:
        SecureCredentialStore(MagicMock(), "entry123")
    _args, kwargs = store_cls.call_args
    assert kwargs["private"] is True
    assert kwargs["atomic_writes"] is True


@pytest.mark.asyncio
async def test_save_persists_only_known_keys():
    store, backing = _store_with_backing()
    await store.async_save(
        {
            "refresh_token": "r",
            "mac_dms": {"k": "v"},
            "serial": "S",
            "customer_id": "C",
            "domain": "amazon.com",
            "password": "leak",  # must be dropped
        },
        pending_validation=True,
    )
    payload = backing.async_save.call_args.args[0]
    assert "password" not in payload
    assert set(payload) == set(CREDENTIAL_KEYS) | {"pending_validation"}
    assert payload["pending_validation"] is True


@pytest.mark.asyncio
async def test_mark_validated_clears_flag():
    store, backing = _store_with_backing()
    backing.async_load = AsyncMock(
        return_value={"refresh_token": "r", "pending_validation": True}
    )
    store._data = None
    await store.async_mark_validated()
    payload = backing.async_save.call_args.args[0]
    assert payload["pending_validation"] is False


@pytest.mark.asyncio
async def test_mark_validated_noop_when_not_pending():
    store, backing = _store_with_backing()
    backing.async_load = AsyncMock(
        return_value={"refresh_token": "r", "pending_validation": False}
    )
    store._data = None
    await store.async_mark_validated()
    backing.async_save.assert_not_called()


@pytest.mark.asyncio
async def test_remove_delegates_to_backing():
    store, backing = _store_with_backing()
    await store.async_remove()
    backing.async_remove.assert_awaited_once()
