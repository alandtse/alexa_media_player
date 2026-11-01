"""Regression tests for shared Amazon Kids polling and initialization."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from custom_components.alexa_media.amazon_kids import (
    KIDS_SCAN_INTERVAL,
    AmazonKidsState,
)


@pytest.fixture
def kids():
    """Provide shared state with mocked API calls and timer registration."""
    with (
        patch("custom_components.alexa_media.amazon_kids.AlexaAPI") as api,
        patch(
            "custom_components.alexa_media.amazon_kids.async_track_time_interval"
        ) as timer,
    ):
        api.get_child_profiles = AsyncMock(return_value=[])
        api.get_child_mode = AsyncMock(return_value=False)
        api.get_device_child = AsyncMock(return_value="child-id")
        state = AmazonKidsState(MagicMock(), MagicMock(email="test@example.com"))
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
    state.track("B", "echo")
    api.get_child_mode.return_value = True
    await state.async_start()

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
    # Let each start reach the held lock before releasing the API response.
    await asyncio.sleep(0)
    assert all(not task.done() for task in starts)
    assert api.get_child_profiles.await_count == 1
    release.set()
    await asyncio.wait_for(asyncio.gather(first, *starts), 1)

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
    cached = state.state("A").copy()
    state.track("B", "echo")
    api.get_child_profiles.side_effect = RuntimeError("Profiles failed")
    api.get_child_mode.side_effect = failure
    api.get_child_mode.return_value = None
    await state.async_start()
    assert state.state("B")["kids"] is None
    assert state.state("A") == cached
    assert state.child_options == ["Child"]

    await state._async_interval(None)
    assert state.state("A") == cached
    assert state.state("B")["kids"] is None
    api.get_child_mode.side_effect = None
    api.get_child_mode.return_value = False
    await state.async_start()
    assert state.state("B")["kids"] is False
    assert state.state("A") == cached
    await state.async_start()
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
    assert api.get_child_mode.await_count == 3
    assert api.get_child_profiles.await_count == 3
    state.async_stop()
    timer.return_value.assert_called_once_with()
    await state.async_start()
    assert timer.call_count == 2
    assert api.get_child_mode.await_count == 4


@pytest.mark.asyncio
async def test_failed_assignment_keeps_last_child(kids):
    """A later full refresh still preserves an unreadable child assignment."""
    state, api, _ = kids
    state.track("A", "echo")
    api.get_child_mode.return_value = True
    await state.async_start()
    cached = state.state("A").copy()
    api.get_device_child.side_effect = RuntimeError("Assignment failed")
    await state.async_refresh()
    assert state.state("A") == cached
