"""Regression tests for shared Amazon Kids polling and initialization."""

import asyncio
import socket
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from custom_components.alexa_media.amazon_kids import (
    KIDS_SCAN_INTERVAL,
    AmazonKidsState,
)


async def drain_refreshes(state):
    """Wait for scheduled refreshes, including their completion callbacks."""
    if state._refresh_tasks:
        await asyncio.wait_for(asyncio.gather(*state._refresh_tasks), 1)


@pytest.fixture(params=[False, True], ids=["scheduled", "eager"])
def kids(request):
    """Provide shared state with mocked API calls and timer registration."""
    with (
        patch("custom_components.alexa_media.amazon_kids.AlexaAPI") as api,
        patch(
            "custom_components.alexa_media.amazon_kids.async_track_time_interval"
        ) as timer,
    ):
        api.supports_child_profiles = AsyncMock(return_value=True)
        api.get_child_profiles = AsyncMock(return_value=[])
        api.get_child_mode = AsyncMock(return_value=False)
        api.get_device_child = AsyncMock(return_value="child-id")
        state = AmazonKidsState(MagicMock(), MagicMock(email="test@example.com"))
        state.hass.async_create_background_task.side_effect = (
            lambda coro, name: asyncio.Task(
                coro,
                name=name,
                loop=asyncio.get_running_loop(),
                eager_start=request.param,
            )
        )
        yield state, api, timer
        state.async_stop()


@pytest.mark.asyncio
async def test_start_initializes_late_device_only(kids):
    """A device registered after a completed refresh need not wait for a poll."""
    state, api, timer = kids
    listener = MagicMock()
    state.async_add_listener(listener)
    state.track("A", "echo")
    await state.async_start()
    await drain_refreshes(state)
    state.track("B", "echo")
    api.get_child_mode.return_value = True
    await state.async_start()
    await drain_refreshes(state)

    assert state.state("B") == {
        "kids": True,
        "child": "child-id",
        "last_child": "child-id",
    }
    assert state.state("A")["kids"] is False
    assert api.get_child_mode.await_args_list == [
        call(state.login, "A", "echo"),
        call(state.login, "B", "echo"),
    ]
    assert listener.call_count == 2
    for _ in range(3):
        state.track("B", "echo")
        await state.async_start()
        await drain_refreshes(state)
    assert api.get_child_profiles.await_count == 2
    assert api.get_child_mode.await_count == 2
    timer.assert_called_once_with(state.hass, state._async_interval, KIDS_SCAN_INTERVAL)


@pytest.mark.asyncio
@pytest.mark.parametrize("before_snapshot", [False, True])
@pytest.mark.parametrize("polling_active", [False, True])
async def test_concurrent_starts_recheck_after_refresh_lock(
    kids, before_snapshot, polling_active
):
    """Queued starts initialize a missed device once, or skip one already read."""
    state, api, timer = kids
    if polling_active:
        state.track("cached", "echo")
        await state.async_start()
        await drain_refreshes(state)
        api.get_child_profiles.reset_mock()
        api.get_child_mode.reset_mock()
    entered = asyncio.Event()
    release = asyncio.Event()

    async def block(*args):
        entered.set()
        await release.wait()
        return [] if before_snapshot else False

    if before_snapshot:
        api.get_child_profiles.side_effect = block
    else:
        api.get_child_mode.side_effect = block
    state.track("A", "echo")
    first = asyncio.create_task(state.async_start())
    await asyncio.wait_for(entered.wait(), 1)
    state.track("B", "echo")
    starts = [asyncio.create_task(state.async_start()) for _ in range(3)]
    # Starts return while their background refreshes wait for the held lock.
    await asyncio.sleep(0)
    assert all(task.done() for task in starts)
    assert api.get_child_profiles.await_count == 1
    release.set()
    await asyncio.wait_for(asyncio.gather(first, *starts), 1)
    await drain_refreshes(state)

    assert state.state("B")["kids"] is False
    assert api.get_child_mode.await_args_list == [
        call(state.login, "A", "echo"),
        call(state.login, "B", "echo"),
    ]
    # An active start snapshots unknown devices before fetching profiles;
    # a full refresh snapshots all devices after fetching profiles.
    assert api.get_child_profiles.await_count == (
        1 if before_snapshot and not polling_active else 2
    )
    assert timer.call_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [None, RuntimeError("API failed")])
async def test_unknown_reads_retry_and_failed_polls_preserve_cache(kids, failure):
    """Unreadable devices can retry on start; cached devices retain their values."""
    state, api, _ = kids
    state.track("A", "echo")
    api.get_child_profiles.return_value = [
        {"directedId": "child-id", "firstName": "Child"}
    ]
    api.get_child_mode.return_value = True
    await state.async_start()
    await drain_refreshes(state)
    cached = state.state("A").copy()
    state.track("B", "echo")
    api.get_child_profiles.side_effect = RuntimeError("Profiles failed")
    api.get_child_mode.side_effect = failure
    api.get_child_mode.return_value = None
    await state.async_start()
    await drain_refreshes(state)
    assert state.state("B")["kids"] is None
    assert state.state("A") == cached
    assert state.child_options == ["Child"]

    await state._async_interval(None)
    assert state.state("A") == cached
    assert state.state("B")["kids"] is None
    api.get_child_mode.side_effect = None
    api.get_child_mode.return_value = False
    await state.async_start()
    await drain_refreshes(state)
    assert state.state("B")["kids"] is False
    assert state.state("A") == cached
    await state.async_start()
    await drain_refreshes(state)
    assert api.get_child_mode.await_count == 5


@pytest.mark.asyncio
async def test_explicit_refresh_waits_and_refreshes_known_devices(kids):
    """Command and interval refreshes remain serialized and refresh all devices."""
    state, api, timer = kids
    entered = asyncio.Event()
    release = asyncio.Event()

    async def read_mode(*args):
        entered.set()
        await release.wait()
        return False

    state.track("A", "echo")
    api.get_child_mode.side_effect = read_mode
    first = asyncio.create_task(state.async_start())
    await asyncio.wait_for(entered.wait(), 1)
    explicit = asyncio.create_task(state.async_refresh())
    interval = asyncio.create_task(state._async_interval(None))
    await asyncio.sleep(0)
    assert api.get_child_profiles.await_count == 1
    release.set()
    await asyncio.wait_for(asyncio.gather(first, explicit, interval), 1)
    await drain_refreshes(state)
    assert api.get_child_mode.await_count == 3
    assert api.get_child_profiles.await_count == 3
    state.async_stop()
    timer.return_value.assert_called_once_with()
    await state.async_start()
    await drain_refreshes(state)
    assert timer.call_count == 2
    assert api.get_child_mode.await_count == 4


@pytest.mark.asyncio
async def test_failed_assignment_keeps_last_child(kids):
    """A later full refresh still preserves an unreadable child assignment."""
    state, api, _ = kids
    state.track("A", "echo")
    api.get_child_mode.return_value = True
    await state.async_start()
    await drain_refreshes(state)
    cached = state.state("A").copy()
    api.get_device_child.side_effect = RuntimeError("Assignment failed")
    await state.async_refresh()
    assert state.state("A") == cached


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure", [socket.gaierror("DNS lookup failed"), RuntimeError("API failed")]
)
async def test_start_returns_before_profile_failure_and_later_poll_recovers(
    kids, failure
):
    """A slow failing optional lookup cannot hold up platform initialization."""
    state, api, timer = kids
    state.track("A", "echo")
    entered = asyncio.Event()
    release = asyncio.Event()

    async def fail_profiles(*args):
        entered.set()
        await release.wait()
        raise failure

    api.get_child_profiles.side_effect = fail_profiles
    await asyncio.wait_for(state.async_start(), 1)
    await asyncio.wait_for(entered.wait(), 1)
    assert state.state("A")["kids"] is None
    api.get_child_mode.assert_not_awaited()
    timer.assert_called_once_with(state.hass, state._async_interval, KIDS_SCAN_INTERVAL)
    release.set()
    await drain_refreshes(state)
    assert state.state("A")["kids"] is False

    api.get_child_profiles.side_effect = None
    api.get_child_profiles.return_value = [
        {"directedId": "child-id", "firstName": "Child"}
    ]
    api.get_child_mode.return_value = True
    await state._async_interval(None)
    assert state.child_options == ["Child"]
    assert state.state("A")["child"] == "child-id"


@pytest.mark.asyncio
@pytest.mark.parametrize("during_interval", [False, True])
async def test_stop_cancels_running_and_queued_refreshes(kids, during_interval):
    """Unload cancels both the API request and refreshes waiting for its lock."""
    state, api, timer = kids
    state.track("A", "echo")
    await state.async_start()
    await drain_refreshes(state)
    cached = state.state("A").copy()
    entered = asyncio.Event()

    async def block(*args):
        entered.set()
        await asyncio.Event().wait()

    api.get_child_profiles.side_effect = block
    state.track("B", "echo")
    interval = None
    if during_interval:
        interval = asyncio.create_task(state._async_interval(None))
    else:
        await state.async_start()
    await asyncio.wait_for(entered.wait(), 1)
    await state.async_start()
    await asyncio.sleep(0)
    tasks = list(state._refresh_tasks)
    assert len(tasks) == 2
    api.get_child_mode.reset_mock()
    listener = MagicMock()
    state.async_add_listener(listener)
    state.async_stop()
    state.async_stop()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    assert all(isinstance(result, asyncio.CancelledError) for result in results)
    if interval is not None:
        with pytest.raises(asyncio.CancelledError):
            await interval
    assert not state._refresh_tasks
    assert not state._refresh_lock.locked()
    timer.return_value.assert_called_once_with()
    api.get_child_mode.assert_not_awaited()
    listener.assert_not_called()
    assert state.state("A") == cached
    calls = api.get_child_profiles.await_count
    await state._async_interval(None)
    assert api.get_child_profiles.await_count == calls

    api.get_child_profiles.side_effect = None
    await state.async_start()
    await drain_refreshes(state)
    assert state.state("B")["kids"] is False
    assert timer.call_count == 2


@pytest.mark.asyncio
async def test_switch_setup_does_not_wait_for_profiles(kids, tmp_path):
    """Home Assistant startup and switch setup finish during a blocked lookup."""
    from homeassistant.core import HomeAssistant

    from custom_components.alexa_media.const import DATA_ALEXAMEDIA
    from custom_components.alexa_media.switch import async_setup_platform

    state, api, _ = kids
    hass = HomeAssistant(str(tmp_path))
    state.hass = hass
    entered = asyncio.Event()
    release = asyncio.Event()

    async def profiles(*args):
        entered.set()
        await release.wait()
        raise socket.gaierror("DNS lookup failed")

    api.get_child_profiles.side_effect = profiles
    client = MagicMock(device_serial_number="A")
    account = {
        "devices": {
            "media_player": {"A": {"deviceFamily": "ECHO", "deviceType": "echo"}}
        },
        "entities": {
            "media_player": {"A": client},
            "switch": {"A": {}},
            "amazon_kids_switch": [],
        },
        "login_obj": state.login,
        "amazon_kids": state,
    }
    hass.data[DATA_ALEXAMEDIA] = {"accounts": {"test@example.com": account}}
    try:
        with patch(
            "custom_components.alexa_media.switch.add_devices",
            new_callable=AsyncMock,
            return_value=True,
        ) as add:
            assert (
                await asyncio.wait_for(
                    async_setup_platform(
                        hass, {"email": "test@example.com"}, MagicMock()
                    ),
                    1,
                )
                is True
            )
            await asyncio.wait_for(entered.wait(), 1)
            await asyncio.wait_for(hass.async_block_till_done(), 1)
            assert add.await_count == 2
            assert account["entities"]["amazon_kids_switch"][0].available is False
            release.set()
            await drain_refreshes(state)
            assert account["entities"]["amazon_kids_switch"][0].available is True
    finally:
        state.async_stop()
        await asyncio.gather(*state._refresh_tasks, return_exceptions=True)


@pytest.mark.asyncio
async def test_entities_wait_for_parent_dashboard(kids):
    """Switch and select appear once a refresh finds the parent dashboard."""
    state, api, _ = kids
    api.supports_child_profiles.return_value = False
    added = []

    async def add_switches():
        added.append("switch")

    async def add_selects():
        added.append("select")

    state.track("A", "echo")
    await state.async_add_when_dashboard(add_switches)
    await state.async_add_when_dashboard(add_selects)
    await state.async_refresh()
    # No dashboard (amazon.nl, or DNS not ready yet): nothing is added, but
    # the binary sensor's child mode state is still read.
    assert added == []
    assert state.dashboard_available is False
    assert state.state("A")["kids"] is False

    api.supports_child_profiles.return_value = True
    await state.async_refresh()
    assert added == ["switch", "select"]
    assert state.dashboard_available is True

    # Found once: later polls neither look up nor add again, and a platform
    # set up after that adds its entities right away.
    await state.async_refresh()
    assert api.supports_child_profiles.await_count == 2

    async def add_late():
        added.append("late")

    await state.async_add_when_dashboard(add_late)
    assert added == ["switch", "select", "late"]


@pytest.mark.asyncio
async def test_failed_dashboard_check_or_add_does_not_stop_the_poll(kids):
    """A failing lookup or platform leaves the poll and other platforms working."""
    state, api, _ = kids
    api.supports_child_profiles.side_effect = OSError("resolver down")
    added = []

    async def add_broken():
        raise RuntimeError("platform failed")

    async def add_selects():
        added.append("select")

    state.track("A", "echo")
    await state.async_add_when_dashboard(add_broken)
    await state.async_add_when_dashboard(add_selects)
    await state.async_refresh()
    assert state.dashboard_available is None
    assert added == []
    assert state.state("A")["kids"] is False

    api.supports_child_profiles.side_effect = None
    await state.async_refresh()
    assert added == ["select"]
    assert state.dashboard_available is True


@pytest.mark.asyncio
async def test_stop_drops_entities_waiting_for_dashboard(kids):
    """Entities still waiting are not added after the account is unloaded."""
    state, api, _ = kids
    api.supports_child_profiles.return_value = False
    added = []

    async def add_switches():
        added.append("switch")

    await state.async_add_when_dashboard(add_switches)
    await state.async_refresh()
    state.async_stop()
    api.supports_child_profiles.return_value = True
    await state.async_refresh()
    assert added == []


@pytest.mark.asyncio
async def test_select_setup_skips_marketplace_without_dashboard(kids, tmp_path):
    """Without a parent dashboard the select platform adds no entities."""
    from homeassistant.core import HomeAssistant

    from custom_components.alexa_media.const import DATA_ALEXAMEDIA
    from custom_components.alexa_media.select import async_setup_platform

    state, api, _ = kids
    api.supports_child_profiles.return_value = False
    hass = HomeAssistant(str(tmp_path))
    state.hass = hass
    account = {
        "devices": {
            "media_player": {"A": {"deviceFamily": "ECHO", "deviceType": "echo"}}
        },
        "entities": {
            "media_player": {"A": MagicMock(device_serial_number="A")},
            "select": [],
        },
        "login_obj": state.login,
        "amazon_kids": state,
    }
    hass.data[DATA_ALEXAMEDIA] = {"accounts": {"test@example.com": account}}
    try:
        with patch(
            "custom_components.alexa_media.select.add_devices",
            new_callable=AsyncMock,
            return_value=True,
        ) as add:
            assert (
                await async_setup_platform(
                    hass, {"email": "test@example.com"}, MagicMock()
                )
                is True
            )
            await drain_refreshes(state)
            add.assert_not_awaited()
            assert account["entities"]["select"] == []
            assert state.state("A")["kids"] is False
    finally:
        state.async_stop()
        await asyncio.gather(*state._refresh_tasks, return_exceptions=True)


@pytest.mark.asyncio
async def test_alexapy_without_dashboard_check_keeps_entities(kids):
    """An alexapy that cannot check the dashboard still gets the entities."""
    state, api, _ = kids
    del api.supports_child_profiles
    added = []

    async def add_switches():
        added.append("switch")

    await state.async_add_when_dashboard(add_switches)
    await state.async_refresh()
    assert added == ["switch"]
    assert state.dashboard_available is True
