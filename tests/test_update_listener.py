"""Tests for the config entry update listener in custom_components.alexa_media."""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_URL
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

SETUP_RETRIES = 3


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Allow Home Assistant to load the custom integration."""
    yield


class FakeAlexaLogin:
    """Network-free stand-in for alexapy.AlexaLogin."""

    hang_login = False

    def __init__(self, url, email, **kwargs):
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
        if FakeAlexaLogin.hang_login:
            await asyncio.Event().wait()
        self.status["login_successful"] = True


@pytest.fixture
def fake_login():
    """Patch the Amazon login layer and the device fetch that follows it."""
    FakeAlexaLogin.hang_login = False
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


def _config_entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_EMAIL: "test@example.com",
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

    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert len(entry.update_listeners) == 1

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


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
