"""Tests for absolute media seek support."""

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.components.media_player import MediaPlayerState
import pytest

from custom_components.alexa_media.const import DATA_ALEXAMEDIA
from custom_components.alexa_media.media_player import AlexaClient

EMAIL = "test@example.com"  # noqa: S105


def _client() -> AlexaClient:
    client = object.__new__(AlexaClient)
    client.hass = MagicMock()
    client._login = MagicMock(email=EMAIL)
    client.alexa_api = MagicMock()
    client.alexa_api.set_media = AsyncMock()
    client._available = True
    client._media_player_state = "PLAYING"
    client._connected_bluetooth = None
    client._bluetooth_state = None
    client._playing_parent = None
    client._session = {}
    client._player_info = {}
    client._parent_clusters = []
    client.check_login_changes = MagicMock()
    client.async_update = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_seek_sends_milliseconds():
    """HA seek positions are seconds; the Alexa command uses milliseconds."""
    client = _client()

    with patch(
        "custom_components.alexa_media.media_player.is_http2_enabled",
        return_value=True,
    ):
        await client.async_media_seek(12.5)

    client.alexa_api.set_media.assert_awaited_once_with(
        {"type": "SeekCommand", "mediaPosition": 12500}
    )


@pytest.mark.asyncio
async def test_seek_forwards_to_playing_parent():
    """Cluster members delegate seek to the parent group."""
    client = _client()
    parent = MagicMock()
    parent.async_media_seek = AsyncMock()
    client._playing_parent = parent

    await client.async_media_seek(5)

    parent.async_media_seek.assert_awaited_once_with(5)
    client.alexa_api.set_media.assert_not_awaited()


@pytest.mark.asyncio
async def test_seek_ignored_when_idle():
    """Seeking is only valid while playing or paused."""
    client = _client()
    client._media_player_state = "IDLE"

    await client.async_media_seek(5)

    client.alexa_api.set_media.assert_not_awaited()


@pytest.mark.asyncio
async def test_seek_finds_paused_group_without_playing_parent():
    """Seek uses dev's paused-group routing even after the playing pointer clears."""
    client = _client()
    client._media_player_state = "PAUSED"
    client._parent_clusters = ["group"]
    client._player_info = {"dopplerId": {"parentSerialNumber": "group"}}
    parent = MagicMock(state=MediaPlayerState.PAUSED, async_media_seek=AsyncMock())
    client.hass.data = {
        DATA_ALEXAMEDIA: {
            "accounts": {EMAIL: {"entities": {"media_player": {"group": parent}}}}
        }
    }

    await client.async_media_seek(7)

    parent.async_media_seek.assert_awaited_once_with(7)
    client.alexa_api.set_media.assert_not_awaited()


@pytest.mark.asyncio
async def test_seek_keeps_bluetooth_session_on_member():
    """A stale group pointer must not divert a member's own Bluetooth seek."""
    client = _client()
    client._session = {"mediaId": "BluetoothMediaId"}
    parent = MagicMock(async_media_seek=AsyncMock())
    client._playing_parent = parent

    with patch(
        "custom_components.alexa_media.media_player.is_http2_enabled", return_value=True
    ):
        await client.async_media_seek(7)

    parent.async_media_seek.assert_not_awaited()
    client.alexa_api.set_media.assert_awaited_once_with(
        {"type": "SeekCommand", "mediaPosition": 7000}
    )
