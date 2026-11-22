"""Tests for the config entry update listener in custom_components.alexa_media."""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from alexapy import hide_email
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_URL
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

import custom_components.alexa_media as alexa_media
from custom_components.alexa_media.const import (
    CONF_EXTENDED_ENTITY_DISCOVERY,
    CONF_QUEUE_DELAY,
    DATA_ALEXAMEDIA,
    DOMAIN,
)
from custom_components.alexa_media.services import AlexaMediaServices

SETUP_RETRIES = 3


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Allow Home Assistant to load the custom integration."""
    yield


class FakeAlexaLogin:
    """Network-free stand-in for alexapy.AlexaLogin."""

    hang_login = False
    login_gate: "asyncio.Event | None" = None
    login_started: "asyncio.Event | None" = None
    login_timeout = False
    last_instance: "FakeAlexaLogin | None" = None
    instances: dict[str, "FakeAlexaLogin"] = {}

    def __init__(self, url, email, **kwargs):
        FakeAlexaLogin.last_instance = self
        FakeAlexaLogin.instances[email] = self
        self.url = url
        self.email = email
        self.status = {}
        self.stats = {"login_timestamp": datetime(1, 1, 1), "api_calls": 0}
        self._session = None
        self.session = MagicMock(closed=True)
        self.close = AsyncMock()
        self.save_cookiefile = AsyncMock()
        self.reset = AsyncMock()

    async def load_cookie(self):
        """Report that no cookie is stored."""
        return None

    async def login(self, cookies=None, **kwargs):
        """Hang like an unresponsive Amazon login, or succeed."""
        if FakeAlexaLogin.login_started is not None:
            FakeAlexaLogin.login_started.set()
        if FakeAlexaLogin.hang_login:
            FakeAlexaLogin.login_gate = asyncio.Event()
            await FakeAlexaLogin.login_gate.wait()
        if FakeAlexaLogin.login_timeout:
            raise asyncio.TimeoutError
        self.status["login_successful"] = True


@pytest.fixture
def fake_login():
    """Patch the Amazon login layer and the device fetch that follows it."""
    FakeAlexaLogin.hang_login = False
    FakeAlexaLogin.login_gate = None
    FakeAlexaLogin.login_started = asyncio.Event()
    FakeAlexaLogin.login_timeout = False
    FakeAlexaLogin.instances = {}
    with (
        patch("custom_components.alexa_media.AlexaLogin", FakeAlexaLogin),
        patch("custom_components.alexa_media.LOGIN_MAX_WAIT_S", 0.01),
        # setup_alexa fetches devices from Amazon and forwards the platforms;
        # it plays no part in the update listener's lifecycle.
        patch(
            "custom_components.alexa_media.setup_alexa",
            AsyncMock(return_value=True),
        ),
    ):
        yield FakeAlexaLogin


@pytest.fixture
def listener_spy():
    """Count calls to the real update listener."""
    spy = AsyncMock(side_effect=alexa_media.update_listener)
    with patch("custom_components.alexa_media.update_listener", spy):
        yield spy


def _config_entry(email: str = "test@example.com") -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_EMAIL: email,
            CONF_PASSWORD: "password",
            CONF_URL: "amazon.com",
        },
    )


async def _retry_then_load(hass, entry, fake_login, retries):
    """Fail setup with ConfigEntryNotReady `retries` times, then let it load."""
    fake_login.hang_login = True
    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    for attempt in range(1, retries + 1):
        assert entry.state is ConfigEntryState.SETUP_RETRY
        if attempt == retries:
            fake_login.hang_login = False
        # Home Assistant runs the retry as a background task.
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=5 * attempt))
        await hass.async_block_till_done(wait_background_tasks=True)
    assert entry.state is ConfigEntryState.LOADED


async def _wait_until(predicate, timeout=1.0):
    """Wait for a predicate without assuming an event-loop tick count."""

    async def _poll():
        while not predicate():
            await asyncio.sleep(0)

    await asyncio.wait_for(_poll(), timeout=timeout)


def _stored_options(hass, entry):
    """Return the options the integration keeps for the entry's account."""
    return hass.data[DATA_ALEXAMEDIA]["accounts"][entry.data[CONF_EMAIL]]["options"]


def _change_options(hass, entry):
    """Save new options the way the options flow does."""
    hass.config_entries.async_update_entry(
        entry,
        data={
            **entry.data,
            CONF_QUEUE_DELAY: 3.0,
            CONF_EXTENDED_ENTITY_DISCOVERY: True,
        },
    )


def _change_queue_delay(hass, entry, value):
    """Update the entry data the way the options flow does."""
    hass.config_entries.async_update_entry(
        entry, data={**entry.data, CONF_QUEUE_DELAY: value}
    )


async def test_setup_retries_register_one_update_listener(
    hass, fake_login, listener_spy
):
    """Each ConfigEntryNotReady retry must not add another update listener."""
    entry = _config_entry()
    entry.add_to_hass(hass)

    await _retry_then_load(hass, entry, fake_login, SETUP_RETRIES)
    assert len(entry.update_listeners) == 1

    # One options change runs the listener once and reloads the entry once.
    with patch.object(
        hass.config_entries,
        "async_reload",
        AsyncMock(side_effect=hass.config_entries.async_reload),
    ) as reload_spy:
        _change_queue_delay(hass, entry, 3.0)
        await hass.async_block_till_done(wait_background_tasks=True)
    assert listener_spy.await_count == 1
    assert reload_spy.await_count == 1
    assert entry.state is ConfigEntryState.LOADED
    assert len(entry.update_listeners) == 1

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_failed_login_check_then_reload_registers_one_update_listener(
    hass, fake_login, listener_spy
):
    """A setup that returns False must not leave an update listener behind."""
    entry = _config_entry()
    entry.add_to_hass(hass)

    # A failed login check starts a reauth flow; only its False result matters.
    with patch(
        "custom_components.alexa_media.test_login_status",
        AsyncMock(return_value=False),
    ):
        assert not await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_ERROR
    # No relogin handler survives a failed setup, so force_logout must not be
    # able to find a login object that would claim a recovery never started.
    email = entry.data[CONF_EMAIL]
    assert "login_obj" not in hass.data[DATA_ALEXAMEDIA]["accounts"][email]
    assert "relogin_unsubs" not in hass.data[DATA_ALEXAMEDIA]["accounts"][email]
    assert entry.runtime_data is None
    fake_login.last_instance.close.assert_awaited_once()

    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert len(entry.update_listeners) == 1
    assert hass.data[DATA_ALEXAMEDIA]["accounts"][email]["login_obj"] is not None

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_failed_login_check_keeps_login_when_close_fails(
    hass, fake_login, caplog
):
    """A failed close keeps the login for unload cleanup and logs context."""
    entry = _config_entry()
    entry.add_to_hass(hass)
    checked_login = None

    async def fail_check(hass_arg, entry_arg, login_arg):
        nonlocal checked_login
        assert hass_arg is hass
        assert entry_arg is entry
        checked_login = login_arg
        login_arg.close.side_effect = RuntimeError("close failed")
        return False

    with patch(
        "custom_components.alexa_media.test_login_status",
        AsyncMock(side_effect=fail_check),
    ):
        assert not await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    account = hass.data[DATA_ALEXAMEDIA]["accounts"][entry.data[CONF_EMAIL]]
    assert checked_login is not None
    assert account["login_obj"] is checked_login
    assert "relogin_unsubs" in account
    assert "Could not close login" in caplog.text
    # Let the hass teardown close the retained login without raising again.
    checked_login.close.side_effect = None


async def test_unload_removes_update_listener(hass, fake_login, listener_spy):
    """Reload keeps one update listener and unload removes it."""
    entry = _config_entry()
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert len(entry.update_listeners) == 1

    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert len(entry.update_listeners) == 1

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
    assert entry.update_listeners == []

    # A later data change must not reach a listener for the unloaded entry.
    _change_queue_delay(hass, entry, 3.0)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert listener_spy.await_count == 0


async def test_options_saved_during_setup_retry_are_loaded(hass, fake_login):
    """Options saved while setup is retrying must be used once the entry loads."""
    entry = _config_entry()
    entry.add_to_hass(hass)
    fake_login.hang_login = True
    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY

    _change_options(hass, entry)
    await hass.async_block_till_done(wait_background_tasks=True)

    fake_login.hang_login = False
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=5))
    await hass.async_block_till_done(wait_background_tasks=True)
    assert entry.state is ConfigEntryState.LOADED
    assert _stored_options(hass, entry)[CONF_QUEUE_DELAY] == 3.0
    assert _stored_options(hass, entry)[CONF_EXTENDED_ENTITY_DISCOVERY] is True

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_options_saved_after_failed_setup_are_loaded_on_reload(hass, fake_login):
    """Options saved after a failed setup must be used by the next reload."""
    entry = _config_entry()
    entry.add_to_hass(hass)
    with patch(
        "custom_components.alexa_media.test_login_status",
        AsyncMock(return_value=False),
    ):
        assert not await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_ERROR

    _change_options(hass, entry)
    await hass.async_block_till_done(wait_background_tasks=True)

    # The reauth flow reloads the entry the same way.
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert _stored_options(hass, entry)[CONF_QUEUE_DELAY] == 3.0
    assert _stored_options(hass, entry)[CONF_EXTENDED_ENTITY_DISCOVERY] is True

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_force_logout_defers_only_accounts_still_in_setup(hass, fake_login):
    """A recovery request during login waits for that account's setup."""
    first = _config_entry("first@example.com")
    second = _config_entry("second@example.com")
    assert await async_setup_component(hass, DOMAIN, {})
    first.add_to_hass(hass)
    second.add_to_hass(hass)

    assert await hass.config_entries.async_setup(first.entry_id)
    await hass.async_block_till_done()
    first_login = fake_login.instances[first.data[CONF_EMAIL]]
    first_login.reset.reset_mock()

    fake_login.hang_login = True
    fake_login.login_gate = None
    with (
        patch("custom_components.alexa_media.LOGIN_MAX_WAIT_S", 5),
        patch(
            "custom_components.alexa_media.calculate_uuid",
            AsyncMock(return_value={"uuid": "test-uuid", "index": 1}),
        ),
        patch(
            "custom_components.alexa_media.setup_alexa",
            AsyncMock(return_value=True),
        ),
    ):
        fake_login.login_started = asyncio.Event()
        setup_task = hass.async_create_task(
            hass.config_entries.async_setup(second.entry_id)
        )
        await asyncio.wait_for(fake_login.login_started.wait(), timeout=1)

        second_account = hass.data[DATA_ALEXAMEDIA]["accounts"][second.data[CONF_EMAIL]]
        assert second_account["login_in_progress"] is True
        assert "relogin_unsubs" in second_account

        services = AlexaMediaServices(hass)
        assert await services.force_logout(MagicMock(data={}))

        await _wait_until(lambda: second_account.get("relogin_pending"))
        second_login = fake_login.instances[second.data[CONF_EMAIL]]
        second_login.reset.assert_not_awaited()

        await _wait_until(lambda: first_login.reset.await_count)
        first_login.reset.assert_awaited()

        fake_login.login_gate.set()
        assert await setup_task
        await hass.async_block_till_done(wait_background_tasks=True)

    second_login.reset.assert_awaited()


async def test_deferred_relogin_runs_after_a_failed_setup_attempt(hass, fake_login):
    """A request made during login survives the failed attempt and still runs."""
    entry = _config_entry()
    assert await async_setup_component(hass, DOMAIN, {})
    entry.add_to_hass(hass)
    fake_login.hang_login = True
    fake_login.login_gate = None
    fake_login.login_timeout = True
    with (
        patch("custom_components.alexa_media.LOGIN_MAX_WAIT_S", 5),
        patch(
            "custom_components.alexa_media.calculate_uuid",
            AsyncMock(return_value={"uuid": "test-uuid", "index": 0}),
        ),
        patch(
            "custom_components.alexa_media.test_login_status",
            AsyncMock(return_value=True),
        ),
        patch(
            "custom_components.alexa_media.setup_alexa",
            AsyncMock(return_value=True),
        ),
    ):
        fake_login.login_started = asyncio.Event()
        setup_task = hass.async_create_task(
            hass.config_entries.async_setup(entry.entry_id)
        )
        await asyncio.wait_for(fake_login.login_started.wait(), timeout=1)

        account = hass.data[DATA_ALEXAMEDIA]["accounts"][entry.data[CONF_EMAIL]]
        assert await AlexaMediaServices(hass).force_logout(MagicMock(data={}))
        await _wait_until(lambda: account.get("relogin_pending"))

        fake_login.login_gate.set()
        assert not await setup_task
        await hass.async_block_till_done(wait_background_tasks=True)

    assert entry.state is ConfigEntryState.SETUP_RETRY
    # The deferred request runs against the handler even though this attempt
    # failed; the full reauth outcome is covered by the existing login tests.
    fake_login.instances[entry.data[CONF_EMAIL]].reset.assert_awaited()


@pytest.mark.skipif(
    not hasattr(ConfigEntry, "async_on_state_change"),
    reason="async_on_state_change requires Home Assistant 2025.3+",
)
async def test_not_loaded_state_clears_retained_relogin_state(hass, fake_login):
    """Disabling an entry in SETUP_RETRY drops its retained recovery state."""
    entry = _config_entry()
    assert await async_setup_component(hass, DOMAIN, {})
    entry.add_to_hass(hass)
    fake_login.hang_login = True
    fake_login.login_gate = None
    fake_login.login_timeout = True
    with patch("custom_components.alexa_media.LOGIN_MAX_WAIT_S", 5):
        fake_login.login_started = asyncio.Event()
        setup_task = hass.async_create_task(
            hass.config_entries.async_setup(entry.entry_id)
        )
        await asyncio.wait_for(fake_login.login_started.wait(), timeout=1)
        fake_login.login_gate.set()
        assert not await setup_task
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_RETRY
    account = hass.data[DATA_ALEXAMEDIA]["accounts"][entry.data[CONF_EMAIL]]
    assert "relogin_unsubs" in account
    account["relogin_pending"] = True

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert "relogin_unsubs" not in account
    assert "relogin_pending" not in account


async def test_force_logout_defers_before_setup_uuid_lookup_finishes(hass, fake_login):
    """A retry request during calculate_uuid is deferred, not raced."""
    entry = _config_entry()
    assert await async_setup_component(hass, DOMAIN, {})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    account = hass.data[DATA_ALEXAMEDIA]["accounts"][entry.data[CONF_EMAIL]]
    login = account["login_obj"]
    login.reset.reset_mock()

    uuid_started = asyncio.Event()
    uuid_release = asyncio.Event()

    async def slow_uuid(*args, **kwargs):
        uuid_started.set()
        await uuid_release.wait()
        return {"uuid": "test-uuid", "index": 0}

    with patch("custom_components.alexa_media.calculate_uuid", side_effect=slow_uuid):
        retry_task = hass.async_create_task(alexa_media.async_setup_entry(hass, entry))
        await asyncio.wait_for(uuid_started.wait(), timeout=1)
        assert account["login_in_progress"] is True

        assert await AlexaMediaServices(hass).force_logout(MagicMock(data={}))
        await _wait_until(lambda: account.get("relogin_pending"))
        login.reset.assert_not_awaited()

        uuid_release.set()
        await retry_task
        await hass.async_block_till_done(wait_background_tasks=True)

    login.reset.assert_awaited()


async def test_relogin_rechecks_login_in_progress_after_uuid_lookup(hass, fake_login):
    """A handler that awaited UUID lookup still defers if setup took over."""
    entry = _config_entry()
    assert await async_setup_component(hass, DOMAIN, {})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    account = hass.data[DATA_ALEXAMEDIA]["accounts"][entry.data[CONF_EMAIL]]
    login = account["login_obj"]
    login.reset.reset_mock()

    uuid_started = asyncio.Event()
    uuid_release = asyncio.Event()

    async def slow_uuid(*args, **kwargs):
        uuid_started.set()
        await uuid_release.wait()
        return {"uuid": "test-uuid", "index": 0}

    with patch("custom_components.alexa_media.calculate_uuid", side_effect=slow_uuid):
        hass.bus.async_fire(
            "alexa_media_relogin_required",
            {"email": hide_email(entry.data[CONF_EMAIL])},
        )
        await asyncio.wait_for(uuid_started.wait(), timeout=1)
        account["login_in_progress"] = True
        uuid_release.set()
        await _wait_until(lambda: account.get("relogin_pending"))
        login.reset.assert_not_awaited()

    account["login_in_progress"] = False
    account.pop("relogin_pending", None)


async def test_relogin_owns_login_while_resetting(hass, fake_login):
    """A relogin holds the login during reset; overlapping requests are replayed."""
    entry = _config_entry()
    assert await async_setup_component(hass, DOMAIN, {})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    account = hass.data[DATA_ALEXAMEDIA]["accounts"][entry.data[CONF_EMAIL]]
    login = account["login_obj"]
    login.reset.reset_mock()

    reset_started = asyncio.Event()
    reset_release = asyncio.Event()

    async def slow_reset():
        reset_started.set()
        await reset_release.wait()

    login.reset.side_effect = slow_reset
    event_data = {"email": hide_email(entry.data[CONF_EMAIL])}
    with patch(
        "custom_components.alexa_media.test_login_status",
        AsyncMock(return_value=False),
    ):
        hass.bus.async_fire("alexa_media_relogin_required", event_data)
        await asyncio.wait_for(reset_started.wait(), timeout=1)
        assert account["login_in_progress"] is True

        # A second request while reset() is suspended must not overlap it.
        hass.bus.async_fire("alexa_media_relogin_required", event_data)
        await _wait_until(lambda: account.get("relogin_pending"))
        assert login.reset.await_count == 1

        # Setup waits for the relogin instead of reusing the half-reset login.
        reset_release.set()
        await hass.async_block_till_done(wait_background_tasks=True)

    assert account["login_in_progress"] is False
    assert "relogin_pending" not in account
    # The deferred request ran once the first relogin released the login.
    assert login.reset.await_count == 2


async def test_setup_not_ready_when_relogin_keeps_login(hass, fake_login):
    """Setup must not claim a login a relogin still owns after the wait expires."""
    entry = _config_entry()
    assert await async_setup_component(hass, DOMAIN, {})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    account = hass.data[DATA_ALEXAMEDIA]["accounts"][entry.data[CONF_EMAIL]]
    account["login_in_progress"] = True

    async def no_wait(_delay):
        return None

    with (
        patch("custom_components.alexa_media.asyncio.sleep", no_wait),
        pytest.raises(alexa_media.ConfigEntryNotReady),
    ):
        await alexa_media.async_setup_entry(hass, entry)

    # The active relogin's ownership is left untouched.
    assert account["login_in_progress"] is True
    account["login_in_progress"] = False


async def test_setup_attempt_clears_display_probe_failure(hass):
    """A new setup attempt may probe again after a failed attempt."""
    entry = _config_entry()
    assert await async_setup_component(hass, DOMAIN, {})
    entry.add_to_hass(hass)
    account = {
        "display_probe_failed": {"serial"},
        "login_in_progress": True,
    }
    hass.data.setdefault(DATA_ALEXAMEDIA, {}).setdefault("accounts", {})[
        entry.data[CONF_EMAIL]
    ] = account

    async def no_wait(_delay):
        return None

    with (
        patch("custom_components.alexa_media.asyncio.sleep", no_wait),
        pytest.raises(alexa_media.ConfigEntryNotReady),
    ):
        await alexa_media.async_setup_entry(hass, entry)

    assert "display_probe_failed" not in account


def test_clear_display_relogin_marker():
    """A successful account login lets a later display failure report again."""
    hass = MagicMock()
    hass.data = {DATA_ALEXAMEDIA: {"display_relogin_reported": {"test@example.com"}}}

    alexa_media._clear_display_relogin_marker(hass, "test@example.com")

    assert (
        "test@example.com" not in hass.data[DATA_ALEXAMEDIA]["display_relogin_reported"]
    )


async def test_remove_retires_failed_entry_runtime_account():
    """Removing an entry that never unloaded must not leave its account behind."""
    entry, other = MagicMock(), MagicMock()
    login = MagicMock(close=AsyncMock())
    hass = MagicMock(
        data={
            DATA_ALEXAMEDIA: {
                "accounts": {
                    "a@example.com": {"config_entry": entry, "login_obj": login},
                    "b@example.com": {"config_entry": other, "login_obj": login},
                }
            }
        }
    )

    accounts = hass.data[DATA_ALEXAMEDIA]["accounts"]
    seen = {}

    async def record_detached():
        seen["detached"] = "a@example.com" not in accounts

    login.close.side_effect = record_detached
    await alexa_media._retire_runtime_account(hass, "a@example.com", entry)
    assert seen["detached"] is True
    assert "a@example.com" not in accounts
    login.close.assert_awaited_once()

    # A record owned by a different entry is preserved.
    await alexa_media._retire_runtime_account(hass, "b@example.com", entry)
    assert "b@example.com" in accounts
    login.close.assert_awaited_once()


async def test_relogin_skips_status_check_when_entry_unloads(hass, fake_login):
    """An entry that unloads during reset must not trigger reauthentication."""
    entry = _config_entry()
    assert await async_setup_component(hass, DOMAIN, {})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    account = hass.data[DATA_ALEXAMEDIA]["accounts"][entry.data[CONF_EMAIL]]
    login = account["login_obj"]
    login.reset.reset_mock()

    async def unload_during_reset():
        entry.mock_state(hass, ConfigEntryState.NOT_LOADED)

    login.reset.side_effect = unload_during_reset
    with (
        patch("custom_components.alexa_media.test_login_status", AsyncMock()) as status,
        patch("custom_components.alexa_media.setup_alexa", AsyncMock()) as setup,
    ):
        hass.bus.async_fire(
            "alexa_media_relogin_required",
            {"email": hide_email(entry.data[CONF_EMAIL])},
        )
        await hass.async_block_till_done()

    login.reset.assert_awaited_once()
    status.assert_not_awaited()
    setup.assert_not_awaited()
    assert account["login_in_progress"] is False


def test_state_cleanup_registration_is_optional():
    """Home Assistant 2025.2 has no async_on_state_change; setup must not fail."""

    class OldConfigEntry:
        """Stand-in for a config entry without the newer API."""

    assert (
        alexa_media._async_on_state_change_if_supported(OldConfigEntry(), lambda: None)
        is None
    )


async def test_deferred_request_survives_first_phase_failure(hass, fake_login):
    """A request deferred during UUID lookup still runs when that lookup fails."""
    entry = _config_entry()
    assert await async_setup_component(hass, DOMAIN, {})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    account = hass.data[DATA_ALEXAMEDIA]["accounts"][entry.data[CONF_EMAIL]]
    login = account["login_obj"]
    login.reset.reset_mock()

    uuid_started = asyncio.Event()
    uuid_release = asyncio.Event()
    calls = 0

    async def flaky_uuid(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            uuid_started.set()
            await uuid_release.wait()
            raise RuntimeError("uuid failed")
        return {"uuid": "test-uuid", "index": 0}

    with patch("custom_components.alexa_media.calculate_uuid", side_effect=flaky_uuid):
        # Focused retry-phase unit test: call the setup function directly
        # instead of driving HA's state machine through a second setup.
        retry_task = hass.async_create_task(alexa_media.async_setup_entry(hass, entry))
        await asyncio.wait_for(uuid_started.wait(), timeout=1)
        assert account["login_in_progress"] is True

        assert await AlexaMediaServices(hass).force_logout(MagicMock(data={}))
        await _wait_until(lambda: account.get("relogin_pending"))

        uuid_release.set()
        with pytest.raises(RuntimeError, match="uuid failed"):
            await retry_task
        await hass.async_block_till_done(wait_background_tasks=True)

    assert account["login_in_progress"] is False
    login.reset.assert_awaited()
