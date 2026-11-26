"""Tests for the effective debug option passed to AlexaLogin."""

from datetime import datetime
import json
from unittest.mock import AsyncMock, MagicMock, patch

from aiohttp import CookieJar
from alexapy import hide_email
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_URL
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from yarl import URL

from custom_components.alexa_media.const import CONF_DEBUG, DATA_ALEXAMEDIA, DOMAIN

EMAIL = "test@example.com"
PASSWORD = "password"  # nosec B105  # noqa: S105


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Allow Home Assistant to load the custom integration."""
    yield


class FakeAlexaLogin:
    """Network-free stand-in for alexapy.AlexaLogin."""

    def __init__(self, url, email, **kwargs):
        self.url = url
        self.email = email
        self._session = None
        self.session = MagicMock(closed=True)
        self.status = {"login_successful": True}
        self.stats = {"login_timestamp": datetime(1, 1, 1), "api_calls": 0}
        self.load_cookie = AsyncMock(return_value=None)
        self.login = AsyncMock()
        self.close = AsyncMock()
        self.save_cookiefile = AsyncMock()
        self.reset = AsyncMock()


@pytest.fixture
def login_factory():
    """Patch the login and the network work that follows it."""
    factory = MagicMock(side_effect=FakeAlexaLogin)
    with (
        patch("custom_components.alexa_media.AlexaLogin", factory),
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
        yield factory


def _entry(*, data_debug=None, options_debug=None):
    """Build an entry whose legacy data and options can disagree."""
    data = {
        CONF_EMAIL: EMAIL,
        CONF_PASSWORD: PASSWORD,
        CONF_URL: "amazon.com",
    }
    if data_debug is not None:
        data[CONF_DEBUG] = data_debug
    options = {}
    if options_debug is not None:
        options[CONF_DEBUG] = options_debug
    return MockConfigEntry(domain=DOMAIN, data=data, options=options)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("data_debug", "options_debug", "expected"),
    [
        (False, True, True),
        (True, False, False),
        (None, True, True),
        (None, None, False),
    ],
)
async def test_setup_uses_effective_debug_option(
    hass, login_factory, data_debug, options_debug, expected
):
    """The primary login honors options over legacy data and the default."""
    entry = _entry(data_debug=data_debug, options_debug=options_debug)
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    login_factory.assert_called_once()
    assert login_factory.call_args.kwargs["debug"] is expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("data_debug", "options_debug", "expected"),
    [
        (False, True, True),
        (True, False, False),
        (None, True, True),
        (None, None, False),
    ],
)
async def test_replacement_login_uses_effective_debug_option(
    hass, login_factory, data_debug, options_debug, expected
):
    """A relogin that rebuilds the client also honors the options value."""
    entry = _entry(data_debug=data_debug, options_debug=options_debug)
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    account = hass.data[DATA_ALEXAMEDIA]["accounts"][EMAIL]
    assert login_factory.call_args.kwargs["debug"] is expected

    account["login_obj"] = None
    hass.bus.async_fire("alexa_media_relogin_required", {"email": hide_email(EMAIL)})
    await hass.async_block_till_done()

    assert login_factory.call_count == 2
    assert login_factory.call_args.kwargs["debug"] is expected


@pytest.mark.asyncio
@pytest.mark.parametrize("adopts_cookies", [True, False])
async def test_bootstrap_requires_cookie_adoption(hass, login_factory, adopts_cookies):
    """A bootstrap hit must adopt API cookies or use the normal login path."""
    api_url = URL("https://alexa.amazon.com/api/behaviors/preview")
    saved = {"session-id": "saved-session", "csrf": "saved-csrf"}
    jar = CookieJar()
    headers = {}
    if not adopts_cookies:
        jar.update_cookies({"session-id": "previous-session"}, response_url=api_url)
        headers["csrf"] = "previous-csrf"
    response = MagicMock(status=200)
    response.text = AsyncMock(
        return_value=json.dumps(
            {
                "authentication": {
                    "authenticated": True,
                    "customerEmail": EMAIL,
                    "customerId": "saved-customer",
                }
            }
        )
    )
    session = MagicMock(closed=False)
    session.get.return_value.__aenter__.return_value = response

    async def adopt(**_kwargs):
        if adopts_cookies:
            assert not jar.filter_cookies(api_url)
            jar.update_cookies(saved, response_url=api_url)
            headers["csrf"] = saved["csrf"]
        return adopts_cookies

    async def normal_login(**_kwargs):
        assert jar.filter_cookies(api_url)["session-id"].value == "previous-session"
        assert headers["csrf"] == "previous-csrf"

    def create_login(*args, **kwargs):
        client = FakeAlexaLogin(*args, **kwargs)
        client._session = session
        client._ssl = True
        client.load_cookie.return_value = saved
        client.test_loggedin = AsyncMock(side_effect=adopt)
        client.login = AsyncMock(side_effect=normal_login)
        client.check_domain = AsyncMock()
        client.finalize_login = AsyncMock()
        return client

    login_factory.side_effect = create_login
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    account = hass.data[DATA_ALEXAMEDIA]["accounts"][EMAIL]
    client = account["login_obj"]
    assert session.get.call_args.kwargs["cookies"] is saved
    client.test_loggedin.assert_awaited_once_with(cookies=saved, rebuild_session=False)
    client.finalize_login.assert_not_awaited()
    if adopts_cookies:
        client.login.assert_not_awaited()
        assert jar.filter_cookies(api_url)["session-id"].value == saved["session-id"]
        assert headers["csrf"] == saved["csrf"]
    else:
        client.login.assert_awaited_once_with(cookies=saved)
