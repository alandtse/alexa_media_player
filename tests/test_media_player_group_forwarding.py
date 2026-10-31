"""Tests for forwarding a speaker group member's transport commands to the group.

Amazon owns a group's playback session at the group, so play, pause, next and
previous sent to a member return 404. The member has to forward them to the
group while the group is playing or paused.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.alexa_media.const import DATA_ALEXAMEDIA
from custom_components.alexa_media.media_player import AlexaClient

EMAIL = "test@example.com"
GROUP = "GROUP_SERIAL"
MEMBER = "MEMBER_SERIAL"

COMMANDS = [
    ("async_media_play", "play"),
    ("async_media_pause", "pause"),
    ("async_media_next_track", "next"),
    ("async_media_previous_track", "previous"),
]


def _player_info(state, media_id="queue:1"):
    """Return an np/player playerInfo payload."""
    return {
        "state": state,
        "mediaId": media_id,
        "infoText": {"title": "Song", "subText1": "Artist", "subText2": "Album"},
        "progress": {"mediaProgress": 10, "mediaLength": 200},
        "volume": {"muted": False, "volume": 20},
    }


def _make_client(hass, serial, parent_clusters=None, cluster_members=None):
    """Create an AlexaClient registered under the account, with no network."""
    login = MagicMock()
    login.email = EMAIL
    client = AlexaClient(None, login)
    client.hass = hass
    client._device_serial_number = serial
    client._device_name = serial
    client._available = True
    client._capabilities = ["MUSIC_SKILL"]
    client._parent_clusters = parent_clusters or []
    client._cluster_members = cluster_members or []
    client.alexa_api = MagicMock()
    for method in ("play", "pause", "next", "previous"):
        setattr(client.alexa_api, method, AsyncMock())
    client.schedule_update_ha_state = MagicMock()
    client.async_update = AsyncMock()
    hass.data[DATA_ALEXAMEDIA]["accounts"][EMAIL]["entities"]["media_player"][
        serial
    ] = client
    return client


@pytest.fixture
def hass():
    """Return a mock hass holding one Alexa account."""
    mock_hass = MagicMock()
    mock_hass.data = {
        DATA_ALEXAMEDIA: {"accounts": {EMAIL: {"entities": {"media_player": {}}}}}
    }
    mock_hass.async_create_task = MagicMock(side_effect=lambda coro: coro.close())
    return mock_hass


@pytest.fixture
def group(hass):
    """Return a speaker group with one member."""
    client = _make_client(hass, GROUP, cluster_members=[MEMBER])
    for method, _ in COMMANDS:
        setattr(client, method, AsyncMock())
    return client


@pytest.fixture
def member(hass):
    """Return an Echo that is a member of the group."""
    return _make_client(hass, MEMBER, parent_clusters=[GROUP])


async def _group_reports(group, member, state):
    """Put the group in a state and send it to the member, as the group does."""
    group._media_player_state = state
    group._session = _player_info(state)
    payload = group._make_dispatcher_data(group._session, MEMBER)
    await member._handle_event({"parent_state": payload})


def _member_calls(member, api_method):
    """Return how often the member sent a command to Amazon itself."""
    return getattr(member.alexa_api, api_method).call_count


@pytest.mark.asyncio
@pytest.mark.parametrize(("command", "api_method"), COMMANDS)
async def test_paused_group_gets_member_commands(group, member, command, api_method):
    """A paused group still owns the session, so the member forwards to it."""
    await _group_reports(group, member, "PAUSED")

    await getattr(member, command)()

    getattr(group, command).assert_awaited_once()
    assert _member_calls(member, api_method) == 0


@pytest.mark.asyncio
async def test_paused_group_survives_member_refresh(group, member):
    """The member's own np/player is empty while its group is paused."""
    await _group_reports(group, member, "PAUSED")
    await member.refresh(no_throttle=True)
    member._api_get_state = AsyncMock(
        return_value={"playerInfo": _player_info(None, media_id=None)}
    )
    await member.refresh(no_throttle=True)

    await member.async_media_play()

    group.async_media_play.assert_awaited_once()
    assert _member_calls(member, "play") == 0


@pytest.mark.asyncio
async def test_group_paused_after_member_refresh(group, member):
    """The member still finds its group when the group pauses after the member's
    last refresh, so no update from the group carries its serial."""
    await _group_reports(group, member, "PLAYING")
    await member.refresh(no_throttle=True)
    group._media_player_state = "PAUSED"
    group._session = _player_info("PAUSED")
    member._api_get_state = AsyncMock(
        return_value={"playerInfo": _player_info(None, media_id=None)}
    )
    await member.refresh(no_throttle=True)

    await member.async_media_play()

    group.async_media_play.assert_awaited_once()
    assert _member_calls(member, "play") == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(("command", "api_method"), COMMANDS)
async def test_playing_group_gets_member_commands(group, member, command, api_method):
    """Forwarding while the group plays is unchanged."""
    await _group_reports(group, member, "PLAYING")

    await getattr(member, command)()

    getattr(group, command).assert_awaited_once()
    assert _member_calls(member, api_method) == 0


@pytest.mark.asyncio
async def test_own_session_not_forwarded(group, member):
    """A session the member's own np/player reports stays with the member."""
    await _group_reports(group, member, "PAUSED")
    member._api_get_state = AsyncMock(
        return_value={"playerInfo": _player_info("PLAYING", media_id="own")}
    )
    # The first refresh uses the group's report, the next one polls the member
    await member.refresh(no_throttle=True)
    member._api_get_state.assert_not_awaited()
    await member.refresh(no_throttle=True)
    member._api_get_state.assert_awaited_once()

    await member.async_media_pause()

    group.async_media_pause.assert_not_awaited()
    assert _member_calls(member, "pause") == 1


@pytest.mark.asyncio
async def test_bluetooth_not_forwarded(group, member):
    """Bluetooth audio is the member's own, whatever its group reports."""
    await _group_reports(group, member, "PAUSED")
    member._connected_bluetooth = "Phone"
    member._bluetooth_state = {"streamingState": "MUSIC"}

    await member.async_media_pause()

    group.async_media_pause.assert_not_awaited()
    assert _member_calls(member, "pause") == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(("command", "api_method"), COMMANDS)
async def test_bluetooth_while_group_plays_not_forwarded(
    group, member, command, api_method
):
    """Bluetooth started on the member while its group plays stays with the
    member, though the group's playing report is still held."""
    await _group_reports(group, member, "PLAYING")
    with patch.object(member, "_get_connected_bluetooth", return_value="Phone"):
        await member._handle_event(
            {
                "bluetooth_change": {
                    "deviceSerialNumber": MEMBER,
                    "streamingState": "MUSIC",
                }
            }
        )

    await getattr(member, command)()

    getattr(group, command).assert_not_awaited()
    assert _member_calls(member, api_method) == 1


@pytest.mark.asyncio
async def test_idle_bluetooth_still_forwarded(group, member):
    """A paired phone that isn't playing doesn't stop forwarding to the group."""
    await _group_reports(group, member, "PAUSED")
    member._connected_bluetooth = "Phone"
    member._bluetooth_state = {"streamingState": "NONE"}

    await member.async_media_play()

    group.async_media_play.assert_awaited_once()
    assert _member_calls(member, "play") == 0


@pytest.mark.asyncio
async def test_paused_bluetooth_session_not_forwarded(group, member):
    """A phone connecting after the group paused gives the member its own
    Bluetooth session, so play resumes the phone and not the group."""
    await _group_reports(group, member, "PAUSED")
    with patch.object(member, "_get_connected_bluetooth", return_value="Phone"):
        await member._handle_event(
            {
                "bluetooth_change": {
                    "deviceSerialNumber": MEMBER,
                    "streamingState": "NONE",
                }
            }
        )

    await member.async_media_play()

    group.async_media_play.assert_not_awaited()
    assert _member_calls(member, "play") == 1


@pytest.mark.asyncio
async def test_not_forwarded_after_leaving_group(group, member):
    """A member taken out of the group in the Alexa app sends to itself."""
    await _group_reports(group, member, "PAUSED")
    member._parent_clusters = []

    await member.async_media_play()

    group.async_media_play.assert_not_awaited()
    assert _member_calls(member, "play") == 1


@pytest.mark.asyncio
async def test_idle_group_not_forwarded(group, member):
    """A group with no session left does not take the member's commands."""
    await _group_reports(group, member, "PAUSED")
    group._media_player_state = "IDLE"

    await member.async_media_play()

    group.async_media_play.assert_not_awaited()
    assert _member_calls(member, "play") == 1
