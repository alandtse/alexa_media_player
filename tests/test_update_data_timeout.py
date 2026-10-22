"""Tests that a get_devices timeout never prunes the device registry."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from alexapy import AlexaAPI
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_URL
from homeassistant.helpers import device_registry as dr
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.alexa_media.const import (
    CONF_EXCLUDE_DEVICES,
    CONF_INCLUDE_DEVICES,
    CONF_SCAN_INTERVAL,
    DOMAIN,
)

EMAIL = "test@example.com"
DEVICE_SERIAL = "G090XXXXXXXXXXXX"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Allow Home Assistant to load the custom integration."""
    yield


class FakeAlexaLogin:
    """Network-free stand-in for alexapy.AlexaLogin."""

    def __init__(self, url, email, **kwargs):
        self.url = url
        self.email = email
        self.status = {}
        self.stats = {"login_timestamp": datetime(1, 1, 1), "api_calls": 0}
        self._session = None
        self.session = MagicMock(closed=False)
        self.close_requested = False
        self.access_token = None
        self.close = AsyncMock()
        self.save_cookiefile = AsyncMock()
        self.reset = AsyncMock()

    async def load_cookie(self):
        """Report that no cookie is stored."""
        return None

    async def login(self, cookies=None, **kwargs):
        """Log in successfully."""
        self.status["login_successful"] = True


@pytest.fixture
def amazon_api():
    """Patch the Amazon login layer and every Alexa API call the first refresh makes."""
    with (
        patch("custom_components.alexa_media.AlexaLogin", FakeAlexaLogin),
        patch(
            "custom_components.alexa_media.HTTP2EchoClient",
            MagicMock(return_value=MagicMock(async_run=AsyncMock())),
        ),
        patch.object(AlexaAPI, "get_devices", AsyncMock(return_value=[])) as devices,
        patch.object(AlexaAPI, "get_bluetooth", AsyncMock(return_value={})),
        patch.object(AlexaAPI, "get_device_preferences", AsyncMock(return_value={})),
        patch.object(AlexaAPI, "get_dnd_state", AsyncMock(return_value={})),
        patch.object(AlexaAPI, "get_notification_states", AsyncMock(return_value=[])),
        patch.object(AlexaAPI, "get_authentication", AsyncMock(return_value={})),
        patch.object(AlexaAPI, "get_network_details", AsyncMock(return_value={})),
    ):
        yield devices


def _entry_with_registered_device(hass):
    """Add a config entry that already owns a device, as after a restart."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_EMAIL: EMAIL,
            CONF_PASSWORD: "password",
            CONF_URL: "amazon.com",
            CONF_INCLUDE_DEVICES: "",
            CONF_EXCLUDE_DEVICES: "",
            CONF_SCAN_INTERVAL: 60,
        },
    )
    entry.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, DEVICE_SERIAL)},
        name="Kitchen Echo",
    )
    return entry, device


async def test_get_devices_timeout_keeps_registered_devices(hass, amazon_api):
    """A get_devices timeout must retry setup, not wipe the device registry."""
    entry, device = _entry_with_registered_device(hass)
    amazon_api.side_effect = asyncio.TimeoutError

    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    amazon_api.assert_awaited()
    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert dr.async_get(hass).async_get(device.id) is not None
