"""Repeat/shuffle state synchronization and existing capability policy.

Transport payloads are synthetic; these tests do not establish what a particular
Amazon provider reports or whether Amazon accepts a command.
"""

from unittest.mock import AsyncMock, MagicMock

from homeassistant.components.media_player.const import (
    MediaPlayerEntityFeature,
    RepeatMode,
)
import pytest

from custom_components.alexa_media.media_player import AlexaClient
from custom_components.alexa_media.switch import RepeatSwitch, ShuffleSwitch


@pytest.fixture
def client():
    """Create a network-free client using the real entity properties."""
    login = MagicMock()
    login.email = "test@example.com"
    player = AlexaClient(None, login)
    player._device_serial_number = "SERIAL"
    player._available = True
    player._capabilities = ["MUSIC_SKILL"]
    player.alexa_api = MagicMock()
    player.alexa_api.repeat = AsyncMock(return_value=None)
    player.alexa_api.shuffle = AsyncMock(return_value=None)
    player.schedule_update_ha_state = MagicMock()
    return player


@pytest.mark.parametrize("initial", [True, False])
def test_repeat_setter_updates_native_mode(client, initial):
    """A switch-side state update must also update the native repeat mode."""
    client._repeat = initial
    client._attr_repeat = RepeatMode.ALL if initial else RepeatMode.OFF

    client.repeat_state = not initial

    assert client.repeat_state is not initial
    assert client.repeat == (RepeatMode.OFF if initial else RepeatMode.ALL)
    client.schedule_update_ha_state.assert_called_once()


@pytest.mark.parametrize(
    ("switch_type", "api_method", "value"),
    [
        (RepeatSwitch, "repeat", True),
        (RepeatSwitch, "repeat", False),
        (ShuffleSwitch, "shuffle", True),
        (ShuffleSwitch, "shuffle", False),
    ],
)
async def test_switch_acknowledged_update(client, switch_type, api_method, value):
    """Preserve the existing truthy-ack path and switch unique IDs."""
    client._repeat = not value
    client._attr_repeat = RepeatMode.OFF if value else RepeatMode.ALL
    client._shuffle = not value
    switch = switch_type(client)
    switch._attr_name = api_method
    switch.alexa_api = MagicMock()
    command = AsyncMock(return_value=True)
    setattr(switch.alexa_api, api_method, command)
    switch.schedule_update_ha_state = MagicMock()

    await (switch.async_turn_on() if value else switch.async_turn_off())

    command.assert_awaited_once_with(value)
    assert switch.unique_id == f"SERIAL_{api_method}"
    assert switch.is_on is value
    if api_method == "repeat":
        assert client.repeat == (RepeatMode.ALL if value else RepeatMode.OFF)
    else:
        assert client.shuffle is value


@pytest.mark.parametrize(
    "switch_type,api_method", [(RepeatSwitch, "repeat"), (ShuffleSwitch, "shuffle")]
)
async def test_switch_none_return_requests_refresh(client, switch_type, api_method):
    """AlexaPy 1.34.0 returns None; do not invent a success acknowledgement."""
    client.async_update = AsyncMock()
    switch = switch_type(client)
    switch.alexa_api = MagicMock()
    command = AsyncMock(return_value=None)
    setattr(switch.alexa_api, api_method, command)

    await switch.async_turn_on()

    command.assert_awaited_once_with(True)
    client.async_update.assert_awaited_once()
    assert client.repeat_state is None
    assert client.shuffle is None


@pytest.mark.parametrize("state", ["PLAYING", "PAUSED", "IDLE"])
@pytest.mark.parametrize("transport", ["SELECTED", "ENABLED", "DISABLED", "HIDDEN"])
async def test_push_transport_capabilities(client, state, transport):
    """Push transport flags, rather than playback state, govern feature bits."""
    client._player_info = {
        "state": state,
        "transport": {"repeat": transport, "shuffle": transport},
    }

    await client.refresh(no_throttle=True)

    supported = transport in ("SELECTED", "ENABLED")
    for feature in (
        MediaPlayerEntityFeature.REPEAT_SET,
        MediaPlayerEntityFeature.SHUFFLE_SET,
    ):
        assert bool(client.supported_features & feature) is supported
    assert client.repeat_state == (transport == "SELECTED" if supported else None)
    assert client.shuffle == (transport == "SELECTED" if supported else None)


@pytest.mark.parametrize("state", ["PLAYING", "PAUSED", "IDLE"])
async def test_poll_preserves_modes_and_advertises_features(client, state):
    """Document the existing workaround for unreliable polled transport flags."""
    client._repeat = True
    client._attr_repeat = RepeatMode.ALL
    client._shuffle = True
    client._api_get_state = AsyncMock(
        return_value={
            "playerInfo": {
                "state": state,
                "transport": {"repeat": "HIDDEN", "shuffle": "DISABLED"},
            }
        }
    )

    await client.refresh(no_throttle=True)

    assert client.repeat == RepeatMode.ALL
    assert client.shuffle is True
    assert client.supported_features & MediaPlayerEntityFeature.REPEAT_SET
    assert client.supported_features & MediaPlayerEntityFeature.SHUFFLE_SET


@pytest.mark.parametrize(
    "value,mode", [(True, RepeatMode.ALL), (False, RepeatMode.OFF)]
)
async def test_native_commands_share_switch_state(client, value, mode):
    """Native commands retain their existing boolean AlexaPy mapping."""
    await client.async_set_repeat(mode)
    await client.async_set_shuffle(value)

    client.alexa_api.repeat.assert_awaited_once_with(value)
    client.alexa_api.shuffle.assert_awaited_once_with(value)
    assert client.repeat_state is value
    assert client.repeat == mode
    assert client.shuffle is value
