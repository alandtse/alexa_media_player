"""Tests for AlexaClient mute and unmute volume handling."""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.components.media_player import MediaPlayerEntity
import pytest

from custom_components.alexa_media.const import DATA_ALEXAMEDIA
from custom_components.alexa_media.media_player import AlexaClient


def _make_client(*, volume_level: float | None = 0.35, with_hass: bool = False):
    login = MagicMock()
    login.email = "test@example.com"
    client = AlexaClient(None, login)
    client._available = True
    client.entity_id = "media_player.living_room"
    client._media_vol_level = volume_level
    client.alexa_api = MagicMock()
    client.alexa_api.set_volume = AsyncMock(return_value=None)
    client.async_update = AsyncMock(return_value=None)
    if with_hass:
        client.hass = MagicMock()
        client.hass.data = {
            DATA_ALEXAMEDIA: {"accounts": {"test@example.com": {"login_obj": login}}}
        }

        def _consume_coro(coro):
            coro.close()
            return MagicMock()

        client.hass.async_create_task = MagicMock(side_effect=_consume_coro)
    return client


@pytest.mark.asyncio
async def test_unmute_without_saved_volume_uses_default_level(caplog):
    """Unmuting with no stored _saved_volume sets 0.5, never the invalid 50."""
    client = _make_client(volume_level=0.2)
    assert isinstance(client, MediaPlayerEntity)
    assert client._saved_volume is None

    with (
        caplog.at_level(logging.WARNING),
        patch(
            "custom_components.alexa_media.media_player.is_http2_enabled",
            return_value=False,
        ),
    ):
        await client.async_mute_volume(False)

    client.alexa_api.set_volume.assert_awaited_once_with(0.5)
    assert client.is_volume_muted is False
    client.async_update.assert_awaited_once()


@pytest.mark.asyncio
async def test_unmute_without_saved_volume_schedules_default_when_hass_set(caplog):
    """With hass attached, unmuting without _saved_volume schedules set_volume(0.5)."""
    client = _make_client(volume_level=0.2, with_hass=True)

    with (
        caplog.at_level(logging.WARNING),
        patch(
            "custom_components.alexa_media.media_player.is_http2_enabled",
            return_value=True,
        ),
    ):
        await client.async_mute_volume(False)

    client.hass.async_create_task.assert_called_once()
    client.alexa_api.set_volume.assert_called_once_with(0.5)


@pytest.mark.asyncio
async def test_mute_then_unmute_restores_saved_fractional_volume():
    """Muting saves the 0..1 volume level, sets 0, and unmuting restores that exact level."""
    client = _make_client(volume_level=0.35)

    with patch(
        "custom_components.alexa_media.media_player.is_http2_enabled",
        return_value=True,
    ):
        await client.async_mute_volume(True)
        assert client._saved_volume == pytest.approx(0.35)
        client.alexa_api.set_volume.assert_awaited_once_with(0)

        client.alexa_api.set_volume.reset_mock()
        await client.async_mute_volume(False)
        client.alexa_api.set_volume.assert_awaited_once_with(0.35)
