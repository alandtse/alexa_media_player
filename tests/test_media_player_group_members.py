"""Tests for group_members on speaker groups, stereo pairs and their members.

Amazon reports a speaker group or stereo/subwoofer pair as its own device with
clusterMembers. Without group_members, a frontend shows the group and every
member as separate players, all playing the same song.
"""

from unittest.mock import MagicMock

from homeassistant.components.media_player import ATTR_GROUP_MEMBERS
import pytest

from custom_components.alexa_media.const import DATA_ALEXAMEDIA
from custom_components.alexa_media.media_player import AlexaClient

EMAIL = "test@example.com"
PAIR = "PAIR_SERIAL"
SPEAKER = "SPEAKER_SERIAL"
SUB = "SUB_SERIAL"


def _player_info(state):
    """Return an np/player playerInfo payload."""
    return {
        "state": state,
        "mediaId": "queue:1",
        "infoText": {"title": "Song", "subText1": "Artist", "subText2": "Album"},
        "progress": {"mediaProgress": 10, "mediaLength": 200},
        "volume": {"muted": False, "volume": 20},
    }


def _make_client(hass, serial, entity_id, parent_clusters=None, cluster_members=None):
    """Create an AlexaClient registered under the account, with no network."""
    login = MagicMock()
    login.email = EMAIL
    client = AlexaClient(None, login)
    client.hass = hass
    client.entity_id = entity_id
    client._device_serial_number = serial
    client._device_name = serial
    client._available = True
    client._capabilities = ["MUSIC_SKILL"]
    client._parent_clusters = parent_clusters or []
    client._cluster_members = cluster_members or []
    client.schedule_update_ha_state = MagicMock()
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
    return mock_hass


@pytest.fixture
def pair(hass):
    """Return a playing stereo/subwoofer pair of a speaker and a sub."""
    client = _make_client(
        hass, PAIR, "media_player.kitchen_pair", cluster_members=[SPEAKER, SUB]
    )
    client._media_player_state = "PLAYING"
    return client


@pytest.fixture
def speaker(hass):
    """Return the Echo speaker in the pair."""
    return _make_client(hass, SPEAKER, "media_player.echo", parent_clusters=[PAIR])


@pytest.fixture
def sub(hass):
    """Return the Echo Sub in the pair."""
    return _make_client(hass, SUB, "media_player.echo_sub", parent_clusters=[PAIR])


async def _pair_reports(pair, member, state):
    """Put the pair in a state and send it to the member, as the pair does."""
    pair._media_player_state = state
    pair._session = _player_info(state)
    payload = pair._make_dispatcher_data(pair._session, member.device_serial_number)
    await member._handle_event({"parent_state": payload})


@pytest.mark.usefixtures("speaker", "sub")
def test_pair_lists_itself_then_members(pair):
    """The pair leads its own group, followed by its members."""
    assert pair.group_members == [
        "media_player.kitchen_pair",
        "media_player.echo",
        "media_player.echo_sub",
    ]


@pytest.mark.usefixtures("speaker", "sub")
def test_pair_reports_group_members_attribute(pair):
    """The group_members attribute carries the list without join support."""
    assert not pair.support_grouping
    assert pair.extra_state_attributes[ATTR_GROUP_MEMBERS] == [
        "media_player.kitchen_pair",
        "media_player.echo",
        "media_player.echo_sub",
    ]


@pytest.mark.usefixtures("pair", "sub")
def test_ungrouped_player_has_no_group_members_attribute(speaker):
    """A player that is not grouped does not report the attribute."""
    assert ATTR_GROUP_MEMBERS not in speaker.extra_state_attributes


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["PLAYING", "PAUSED"])
async def test_member_lists_the_pair_it_follows(pair, speaker, sub, state):
    """A member following its pair reports the pair's group, pair first."""
    await _pair_reports(pair, speaker, state)

    assert speaker.group_members == [
        "media_player.kitchen_pair",
        "media_player.echo",
        "media_player.echo_sub",
    ]
    assert sub.group_members is None


@pytest.mark.usefixtures("pair", "sub")
def test_member_on_its_own_has_no_group(speaker):
    """A member that is not following a group is not grouped."""
    speaker._session = _player_info("PLAYING")

    assert speaker.group_members is None


@pytest.mark.usefixtures("speaker", "sub")
def test_paused_pair_lists_its_members(pair):
    """A paused pair still holds its members' session."""
    pair._media_player_state = "PAUSED"

    assert pair.group_members == [
        "media_player.kitchen_pair",
        "media_player.echo",
        "media_player.echo_sub",
    ]


@pytest.mark.usefixtures("sub")
@pytest.mark.parametrize("state", ["IDLE", None])
def test_idle_group_does_not_claim_member_playing_alone(pair, speaker, state):
    """An idle pair leaves a speaker playing its own song ungrouped."""
    pair._media_player_state = state
    speaker._media_player_state = "PLAYING"
    speaker._session = _player_info("PLAYING")

    assert pair.group_members is None
    assert speaker.group_members is None


def test_unavailable_group_has_no_group(pair, speaker):
    """An offline pair does not group its members."""
    pair._available = False

    assert pair.group_members is None


@pytest.mark.asyncio
async def test_member_drops_group_that_went_idle(pair, speaker):
    """A member stops listing a group that is idle before telling the member."""
    await _pair_reports(pair, speaker, "PLAYING")
    pair._media_player_state = "IDLE"

    assert speaker.group_members is None


def test_disabled_member_is_skipped(pair, speaker, sub):
    """A disabled entity keeps its entity_id but has no state to group."""
    speaker.add_to_platform_abort()

    assert speaker.entity_id == "media_player.echo"
    assert pair.group_members == [
        "media_player.kitchen_pair",
        "media_player.echo_sub",
    ]


@pytest.mark.asyncio
async def test_member_does_not_list_disabled_group(pair, speaker):
    """A member never leads its list with a disabled group entity."""
    await _pair_reports(pair, speaker, "PLAYING")
    pair.add_to_platform_abort()

    assert speaker.group_members is None


@pytest.mark.usefixtures("speaker")
def test_unregistered_member_is_skipped(pair):
    """A member with no entity yet is left out instead of failing."""
    assert pair.group_members == ["media_player.kitchen_pair", "media_player.echo"]


def test_group_without_known_members_has_no_group(pair, speaker):
    """A group none of whose members have entities reports nothing."""
    speaker.entity_id = None

    assert pair.group_members is None


@pytest.mark.usefixtures("speaker", "sub")
def test_group_not_added_to_hass_has_no_group(pair):
    """Before the group entity is added it has no entity id to lead with."""
    pair.entity_id = None

    assert pair.group_members is None


def test_group_without_hass_has_no_group(pair):
    """An entity that is not attached to hass reports nothing."""
    pair.hass = None

    assert pair.group_members is None
