"""Additional config-flow tests for the Bronze coverage rule."""

from collections import OrderedDict
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from aiohttp import ClientConnectionError, InvalidURL, web
from aiohttp.test_utils import make_mocked_request
from alexapy import AlexapyConnectionError, AlexapyPyotpInvalidKey
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_URL
from homeassistant.exceptions import Unauthorized
from homeassistant.helpers.network import NoURLAvailableError
import httpx
import pytest
from yarl import URL as YarlURL

from custom_components.alexa_media.config_flow import (
    AlexaMediaAuthorizationCallbackView,
    AlexaMediaAuthorizationProxyView,
    AlexaMediaFlowHandler,
    OptionsFlowHandler,
    configured_instances,
)
from custom_components.alexa_media.const import (
    AUTH_PROXY_NAME,
    DOMAIN,
)
from custom_components.alexa_media.const import (
    CONF_DEBUG,
    CONF_EXCLUDE_DEVICES,
    CONF_EXTENDED_ENTITY_DISCOVERY,
    CONF_HASS_URL,
    CONF_INCLUDE_DEVICES,
    CONF_OTPSECRET,
    CONF_PROXY_WARNING,
    CONF_PUBLIC_URL,
    CONF_QUEUE_DELAY,
    CONF_SECURITYCODE,
    CONF_TOTP_REGISTER,
    DATA_ALEXAMEDIA,
    DEFAULT_HASS_URL,
)

EMAIL = "test@example.com"  # noqa: S105
PASSWORD = "secret"  # noqa: S105
URL = "amazon.com"


def _flow() -> AlexaMediaFlowHandler:
    flow = AlexaMediaFlowHandler()
    flow.hass = MagicMock()
    flow.hass.config.country = "US"
    flow.hass.config.path = MagicMock(return_value="/config")
    flow.hass.data = {DATA_ALEXAMEDIA: {"accounts": {}, "config_flows": {}}}
    flow.async_show_form = MagicMock(
        side_effect=lambda **kwargs: {"type": "form", **kwargs}
    )
    flow.async_abort = MagicMock(return_value={"type": "abort"})
    flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})
    flow.async_external_step = MagicMock(return_value={"type": "external"})
    flow.async_external_step_done = MagicMock(return_value={"type": "done"})
    return flow


def test_configured_instances_and_update_ord_dict():
    """The helper builds titles and merges ordered schemas."""
    hass = MagicMock()
    hass.config_entries.async_entries.return_value = [
        MagicMock(title="one"),
        MagicMock(title="two"),
    ]
    assert configured_instances(hass) == {"one", "two"}

    flow = _flow()
    result = flow._update_ord_dict(
        OrderedDict([("a", 1), ("b", 2)]),
        {"b": 3, "c": 4},
    )
    assert list(result.items()) == [("a", 1), ("b", 3)]


@pytest.mark.asyncio
async def test_import_delegates_to_legacy_step():
    """YAML import uses the legacy user step."""
    flow = _flow()
    flow.async_step_user_legacy = AsyncMock(return_value={"type": "form"})

    assert await flow.async_step_import({"email": EMAIL}) == {"type": "form"}
    flow.async_step_user_legacy.assert_awaited_once_with({"email": EMAIL})


def test_save_user_input_covers_all_branches():
    """All mutable config fields are normalized correctly."""
    flow = _flow()
    flow.config = OrderedDict({CONF_SECURITYCODE: "old", CONF_OTPSECRET: "old"})
    flow._save_user_input_to_config(
        {
            CONF_HASS_URL: "http://ha",
            CONF_SECURITYCODE: "123456",
            CONF_OTPSECRET: " 12 34 ",
            CONF_EMAIL: EMAIL,
            CONF_PASSWORD: PASSWORD,
            CONF_URL: " amazon.com. au ",
            CONF_PUBLIC_URL: "http://public",
            CONF_SCAN_INTERVAL: timedelta(seconds=90),
            CONF_QUEUE_DELAY: 2.5,
            CONF_INCLUDE_DEVICES: ["kitchen", "office"],
            CONF_EXCLUDE_DEVICES: ["garage"],
            CONF_EXTENDED_ENTITY_DISCOVERY: True,
            CONF_DEBUG: True,
        }
    )

    assert flow.config[CONF_HASS_URL] == "http://ha"
    assert flow.config[CONF_SECURITYCODE] == "123456"
    assert flow.config[CONF_OTPSECRET] == "1234"
    assert flow.config[CONF_URL] == "amazon.com.au"
    assert flow.config[CONF_PUBLIC_URL] == "http://public/"
    assert flow.config[CONF_SCAN_INTERVAL] == 90
    assert flow.config[CONF_INCLUDE_DEVICES] == "kitchen,office"
    assert flow.config[CONF_EXCLUDE_DEVICES] == "garage"
    assert flow.config[CONF_DEBUG] is True

    # Missing security code, blank OTP, empty lists and plain strings.
    flow._save_user_input_to_config(
        {
            CONF_OTPSECRET: "   ",
            CONF_INCLUDE_DEVICES: [],
            CONF_EXCLUDE_DEVICES: "garage, shed",
            CONF_PUBLIC_URL: "",
            CONF_SCAN_INTERVAL: 30,
        }
    )
    assert CONF_SECURITYCODE not in flow.config
    assert CONF_OTPSECRET not in flow.config
    assert flow.config[CONF_INCLUDE_DEVICES] == ""
    assert flow.config[CONF_EXCLUDE_DEVICES] == "garage, shed"
    assert flow.config[CONF_PUBLIC_URL] == ""
    assert flow.config[CONF_SCAN_INTERVAL] == 30

    flow._save_user_input_to_config({CONF_INCLUDE_DEVICES: "office"})
    assert flow.config[CONF_INCLUDE_DEVICES] == "office"


def test_update_schema_defaults_uses_saved_config():
    """The legacy schema reflects the current config and security code."""
    flow = _flow()
    flow.config = {
        CONF_URL: "amazon.co.uk",
        CONF_EMAIL: EMAIL,
        CONF_PASSWORD: PASSWORD,
        CONF_PUBLIC_URL: "http://ha/",
        CONF_INCLUDE_DEVICES: "kitchen",
        CONF_EXCLUDE_DEVICES: "garage",
        CONF_SCAN_INTERVAL: 45,
        CONF_QUEUE_DELAY: 2.0,
        CONF_EXTENDED_ENTITY_DISCOVERY: True,
        CONF_DEBUG: True,
    }
    flow.securitycode = "123456"

    schema = flow._update_schema_defaults()

    assert isinstance(schema, OrderedDict)
    assert len(schema) == len(flow.data_schema)
    assert any(
        callable(getattr(key, "default", None)) and key.default() == "123456"
        for key in schema
    )


@pytest.mark.asyncio
async def test_proxy_warning_both_paths():
    """Declining the warning goes back; accepting starts the proxy."""
    flow = _flow()
    flow.proxy_schema = OrderedDict()

    result = await flow.async_step_proxy_warning({CONF_PROXY_WARNING: False})
    assert result["type"] == "form"

    flow.async_step_start_proxy = AsyncMock(return_value={"type": "external"})
    result = await flow.async_step_proxy_warning({CONF_PROXY_WARNING: True})
    assert result == {"type": "external"}


@pytest.mark.asyncio
async def test_totp_register_both_paths():
    """Declining TOTP shows a fresh code; accepting continues."""
    flow = _flow()
    flow.login = MagicMock()
    flow.login.get_totp_token.return_value = "123456"
    flow.login.email = EMAIL
    flow.login.url = URL

    result = await flow.async_step_totp_register({CONF_TOTP_REGISTER: False})
    assert result["type"] == "form"
    flow.login.get_totp_token.assert_called_once()

    flow.async_step_start_proxy = AsyncMock(return_value={"type": "external"})
    result = await flow.async_step_totp_register({CONF_TOTP_REGISTER: True})
    assert result == {"type": "external"}


@pytest.mark.asyncio
async def test_process_step_both_paths():
    """Process dispatches to the user form or login test."""
    flow = _flow()
    flow.async_step_user = AsyncMock(return_value={"type": "form"})
    flow._test_login = AsyncMock(return_value={"type": "create_entry"})

    assert await flow.async_step_process("user", {CONF_EMAIL: EMAIL}) == {
        "type": "form"
    }
    flow.async_step_user.assert_awaited_once_with(user_input=None)

    assert await flow.async_step_process("user", None) == {"type": "create_entry"}
    flow._test_login.assert_awaited_once()


@pytest.mark.asyncio
async def test_finish_proxy_failure_aborts():
    """A failed login aborts the flow."""
    flow = _flow()
    flow.login = MagicMock()
    flow.login.test_loggedin = AsyncMock(return_value=False)

    assert await flow.async_step_finish_proxy() == {"type": "abort"}
    flow.async_abort.assert_called_once_with(reason="login_failed")


@pytest.mark.asyncio
async def test_check_proxy_removes_handler_and_finishes():
    """Checking the proxy removes the flow handler."""
    flow = _flow()
    flow.login = MagicMock(email=EMAIL, url=URL)
    proxy_view = MagicMock()
    proxy_view.handlers = {"flow": MagicMock()}
    flow.hass.data["auth:alexamedia:proxy"] = proxy_view
    flow.flow_id = "flow"

    assert await flow.async_step_check_proxy() == {"type": "done"}
    assert "flow" not in proxy_view.handlers


def _login(status=None):
    login = MagicMock()
    login.email = EMAIL
    login.url = URL
    login.password = PASSWORD
    login.status = status or {}
    login.session.closed = False
    login.get_totp_token.return_value = "123456"
    login.login = AsyncMock()
    login.close = AsyncMock()
    login.reported_account_domain = None
    login.access_token = "access"  # nosec B105
    login.refresh_token = "refresh"  # nosec B105
    login.expires_in = 3600
    login.mac_dms = "mac"
    login.code_verifier = "verifier"
    login.authorization_code = "code"  # nosec B105
    return login


@pytest.mark.asyncio
async def test_legacy_step_without_input_and_duplicate():
    """The legacy step shows a form and rejects an existing account."""
    flow = _flow()
    flow.async_show_form = MagicMock(
        side_effect=lambda **kwargs: {"type": "form", **kwargs}
    )

    assert (await flow.async_step_user_legacy(None))["type"] == "form"

    flow.config = {
        CONF_EMAIL: EMAIL,
        CONF_URL: URL,
        CONF_PASSWORD: PASSWORD,
        CONF_DEBUG: False,
    }
    with patch(
        "custom_components.alexa_media.config_flow.configured_instances",
        return_value={f"{EMAIL} - {URL}"},
    ):
        result = await flow.async_step_user_legacy(
            {
                CONF_EMAIL: EMAIL,
                CONF_URL: URL,
                CONF_PASSWORD: PASSWORD,
                CONF_DEBUG: False,
            }
        )
    assert result["type"] == "form"
    assert result["errors"] == {CONF_EMAIL: "identifier_exists"}


@pytest.mark.asyncio
async def test_legacy_reuses_loaded_login_and_resumes_status():
    """A loaded login can be reused without creating a new AlexaLogin."""
    flow = _flow()
    existing = _login({"login_successful": True})
    flow.hass.data[DATA_ALEXAMEDIA]["accounts"][EMAIL] = {"login_obj": existing}
    flow.config = {
        "reauth": True,
        CONF_EMAIL: EMAIL,
        CONF_URL: URL,
        CONF_PASSWORD: PASSWORD,
        CONF_DEBUG: False,
    }
    flow._test_login = AsyncMock(return_value={"type": "create_entry"})

    result = await flow.async_step_user_legacy(
        {CONF_EMAIL: EMAIL, CONF_URL: URL, CONF_PASSWORD: PASSWORD}
    )

    assert result == {"type": "create_entry"}
    assert flow.login is existing
    existing.login.assert_not_awaited()
    flow._test_login.assert_awaited_once()


@pytest.mark.asyncio
async def test_legacy_otp_branches():
    """Valid and empty OTP secrets produce the right forms."""
    flow = _flow()
    flow.login = _login()
    flow.config = {
        CONF_EMAIL: EMAIL,
        CONF_URL: URL,
        CONF_PASSWORD: PASSWORD,
        CONF_DEBUG: False,
    }
    flow.async_show_form = MagicMock(
        side_effect=lambda **kwargs: {"type": "form", **kwargs}
    )

    result = await flow.async_step_user_legacy(
        {
            CONF_EMAIL: EMAIL,
            CONF_URL: URL,
            CONF_PASSWORD: PASSWORD,
            CONF_OTPSECRET: "1234",
        }
    )
    assert result["type"] == "form"
    assert "message" in result["description_placeholders"]

    flow.login.get_totp_token.return_value = ""
    result = await flow.async_step_user_legacy(
        {
            CONF_EMAIL: EMAIL,
            CONF_URL: URL,
            CONF_PASSWORD: PASSWORD,
            CONF_OTPSECRET: "1234",
        }
    )
    assert result["errors"] == {"base": "2fa_key_invalid"}


@pytest.mark.asyncio
async def test_legacy_login_and_error_paths():
    """Legacy login handles success and the three exception branches."""
    flow = _flow()
    flow.login = _login()
    flow.config = {
        CONF_EMAIL: EMAIL,
        CONF_URL: URL,
        CONF_PASSWORD: PASSWORD,
        CONF_DEBUG: False,
    }
    flow._test_login = AsyncMock(return_value={"type": "create_entry"})
    flow.async_show_form = MagicMock(
        side_effect=lambda **kwargs: {"type": "form", **kwargs}
    )

    assert await flow.async_step_user_legacy({CONF_EMAIL: EMAIL}) == {
        "type": "create_entry"
    }
    flow.login.login.assert_awaited_once()

    flow.login.login.side_effect = AlexapyConnectionError("down")
    result = await flow.async_step_user_legacy({CONF_EMAIL: EMAIL})
    assert result["errors"] == {"base": "connection_error"}

    flow.login.login.side_effect = AlexapyPyotpInvalidKey("bad key")
    result = await flow.async_step_user_legacy({CONF_EMAIL: EMAIL})
    assert result["errors"] == {"base": "2fa_key_invalid"}

    flow.login.login.side_effect = RuntimeError("boom")
    result = await flow.async_step_user_legacy({CONF_EMAIL: EMAIL})
    assert result["errors"] == {"base": "unknown_error"}

    flow.config[CONF_DEBUG] = True
    with pytest.raises(RuntimeError):
        await flow.async_step_user_legacy({CONF_EMAIL: EMAIL})


@pytest.mark.asyncio
async def test_reauth_automatic_and_manual_paths():
    """Reauth either shows the form (recent login) or retries automatically."""
    flow = _flow()
    flow.context = {"entry_id": "entry"}
    flow.hass.config_entries.async_get_entry.return_value = MagicMock()
    flow.config = {CONF_EMAIL: EMAIL}
    flow.async_show_form = MagicMock(
        side_effect=lambda **kwargs: {"type": "form", **kwargs}
    )

    login = _login()
    login.stats = {"login_timestamp": __import__("datetime").datetime.now()}
    flow.login = login
    result = await flow.async_step_reauth(None)
    assert result["type"] == "form"
    assert result["description_placeholders"]["message"] == "REAUTH"

    login.stats = {
        "login_timestamp": __import__("datetime").datetime.now()
        - __import__("datetime").timedelta(minutes=5)
    }
    flow.async_step_user_legacy = AsyncMock(return_value={"type": "create_entry"})
    with patch("custom_components.alexa_media.config_flow.sleep", new=AsyncMock()):
        result = await flow.async_step_reauth(None)
    assert result == {"type": "create_entry"}
    flow.async_step_user_legacy.assert_awaited_once()


@pytest.mark.asyncio
async def test_test_login_success_pops_ephemeral_fields():
    """Successful login removes security code and hass_url before saving."""
    flow = _flow()
    flow.login = _login({"login_successful": True})
    flow.config = {
        CONF_EMAIL: EMAIL,
        CONF_SECURITYCODE: "123456",
        CONF_HASS_URL: DEFAULT_HASS_URL,
    }
    flow.async_set_unique_id = AsyncMock(return_value=None)
    flow._abort_if_unique_id_configured = MagicMock()
    flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})

    result = await flow._test_login()

    assert result == {"type": "create_entry"}
    assert CONF_SECURITYCODE not in flow.config
    assert CONF_HASS_URL not in flow.config


@pytest.mark.asyncio
async def test_test_login_reauth_account_ownership_and_email_move():
    """Reauth rejects a runtime account owned by another entry and moves email."""
    flow = _flow()
    flow.login = _login({"login_successful": True})
    existing = MagicMock()
    existing.entry_id = "entry"
    existing.data = {CONF_EMAIL: EMAIL}
    flow.reauth_entry = existing
    flow.config = {CONF_EMAIL: EMAIL}
    flow.hass.config_entries.async_reload = AsyncMock()
    flow.hass.config_entries.async_update_entry = MagicMock()
    flow.hass.bus.async_fire = MagicMock()
    flow.async_abort = MagicMock(return_value={"type": "abort"})

    flow.hass.data[DATA_ALEXAMEDIA]["accounts"][EMAIL] = {
        "config_entry": MagicMock(entry_id="other")
    }
    with patch(
        "custom_components.alexa_media.config_flow.async_dismiss_persistent_notification"
    ):
        result = await flow._test_login()
    assert result == {"type": "abort"}
    flow.async_abort.assert_called_with(reason="already_configured")

    # Same account email, existing runtime account: update the login object.
    flow.async_abort.reset_mock()
    flow.hass.data[DATA_ALEXAMEDIA]["accounts"][EMAIL] = {
        "config_entry": existing,
        "login_obj": None,
    }
    with patch(
        "custom_components.alexa_media.config_flow.async_dismiss_persistent_notification"
    ):
        result = await flow._test_login()
    assert result == {"type": "abort"}
    flow.async_abort.assert_called_with(reason="reauth_successful")


@pytest.mark.asyncio
async def test_test_login_securitycode_and_failure_branches():
    """Security-code, login-failure and error-message branches are covered."""
    flow = _flow()
    flow.async_show_form = MagicMock(
        side_effect=lambda **kwargs: {"type": "form", **kwargs}
    )
    flow.async_step_user_legacy = AsyncMock(return_value={"type": "create_entry"})
    flow.async_abort = MagicMock(return_value={"type": "abort"})
    flow.login = _login({"securitycode_required": True})
    flow.automatic_steps = 0
    flow.securitycode = None
    with patch("custom_components.alexa_media.config_flow.sleep", new=AsyncMock()):
        result = await flow._test_login()
    assert result == {"type": "create_entry"}
    flow.async_step_user_legacy.assert_awaited_once()

    flow.login = _login({"login_failed": "bad"})
    with patch(
        "custom_components.alexa_media.config_flow.async_dismiss_persistent_notification"
    ):
        result = await flow._test_login()
    assert result == {"type": "abort"}

    flow.login = _login(
        {
            "error_message": "There was a problem\n            "
            "Enter a valid email or mobile number\n          "
        }
    )
    flow.automatic_steps = 0
    with patch("custom_components.alexa_media.config_flow.sleep", new=AsyncMock()):
        result = await flow._test_login()
    assert result == {"type": "create_entry"}

    flow.login = _login({"error_message": "some other error"})
    result = await flow._test_login()
    assert result["type"] == "form"


class _ResponseContext:
    def __init__(self, status=200):
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return False


class _SessionContext:
    def __init__(self, status=200, exc=None):
        self.status = status
        self.exc = exc

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return False

    def get(self, _url):
        if self.exc:
            raise self.exc
        return _ResponseContext(self.status)


def _user_input(**overrides):
    data = {
        CONF_URL: URL,
        CONF_EMAIL: EMAIL,
        CONF_PASSWORD: PASSWORD,
        CONF_HASS_URL: "http://ha",
        CONF_DEBUG: False,
    }
    data.update(overrides)
    return data


@pytest.mark.asyncio
async def test_user_step_url_detection_failures():
    """Missing internal and external URLs fall back to the form defaults."""
    flow = _flow()
    with patch(
        "custom_components.alexa_media.config_flow.get_url",
        side_effect=NoURLAvailableError,
    ):
        result = await flow.async_step_user(None)
    assert result["type"] == "form"


@pytest.mark.asyncio
async def test_user_step_reuses_loaded_login_and_creates_proxy():
    """A loaded login skips AlexaLogin creation and starts the proxy."""
    flow = _flow()
    login = _login()
    flow.login = None
    flow.hass.data[DATA_ALEXAMEDIA]["accounts"][EMAIL] = {"login_obj": login}
    flow.config = {
        CONF_EMAIL: EMAIL,
        CONF_URL: URL,
        CONF_PASSWORD: PASSWORD,
        CONF_DEBUG: False,
    }
    flow.async_step_start_proxy = AsyncMock(return_value={"type": "external"})

    with (
        patch(
            "custom_components.alexa_media.config_flow.get_url",
            return_value="http://ha",
        ),
        patch(
            "custom_components.alexa_media.config_flow.ClientSession",
            return_value=_SessionContext(200),
        ),
    ):
        result = await flow.async_step_user(_user_input())

    assert result == {"type": "external"}
    assert flow.login is login


@pytest.mark.asyncio
async def test_user_step_creates_login_when_none_loaded():
    """A new AlexaLogin is created when no loaded login exists."""
    flow = _flow()
    flow.login = None
    flow.config = {
        CONF_EMAIL: EMAIL,
        CONF_URL: URL,
        CONF_PASSWORD: PASSWORD,
        CONF_DEBUG: False,
    }
    new_login = _login()
    flow.async_step_start_proxy = AsyncMock(return_value={"type": "external"})

    with (
        patch(
            "custom_components.alexa_media.config_flow.get_url",
            return_value="http://ha",
        ),
        patch(
            "custom_components.alexa_media.config_flow.ClientSession",
            return_value=_SessionContext(200),
        ),
        patch(
            "custom_components.alexa_media.config_flow.calculate_uuid",
            new_callable=AsyncMock,
            return_value={"uuid": "uuid"},
        ),
        patch(
            "custom_components.alexa_media.config_flow.AlexaLogin",
            return_value=new_login,
        ) as login_cls,
    ):
        result = await flow.async_step_user(_user_input())

    assert result == {"type": "external"}
    login_cls.assert_called_once()
    assert flow.login is new_login


@pytest.mark.asyncio
async def test_user_step_requires_hass_url():
    """A missing hass_url with no detected URL returns the user form."""
    flow = _flow()
    flow.login = _login()
    flow.config = {
        CONF_EMAIL: EMAIL,
        CONF_URL: URL,
        CONF_PASSWORD: PASSWORD,
        CONF_DEBUG: False,
    }
    calls = []

    def _get_url(_hass, **kwargs):
        calls.append(kwargs)
        if kwargs.get("prefer_external"):
            raise NoURLAvailableError
        return "http://ha"

    with patch(
        "custom_components.alexa_media.config_flow.get_url", side_effect=_get_url
    ):
        result = await flow.async_step_user(_user_input(**{CONF_HASS_URL: None}))

    assert result["type"] == "form"
    assert any(call.get("prefer_external") for call in calls)


@pytest.mark.asyncio
@pytest.mark.parametrize("exc", [ClientConnectionError("down"), InvalidURL("bad")])
async def test_user_step_url_check_errors_return_warning(exc):
    """Connection and invalid-URL errors return the proxy warning form."""
    flow = _flow()
    flow.login = _login()
    flow.config = {
        CONF_EMAIL: EMAIL,
        CONF_URL: URL,
        CONF_PASSWORD: PASSWORD,
        CONF_DEBUG: False,
    }

    with (
        patch(
            "custom_components.alexa_media.config_flow.get_url",
            return_value="http://ha",
        ),
        patch(
            "custom_components.alexa_media.config_flow.ClientSession",
            return_value=_SessionContext(exc=exc),
        ),
    ):
        result = await flow.async_step_user(_user_input())

    assert result["type"] == "form"
    assert result["step_id"] == "proxy_warning"


@pytest.mark.asyncio
async def test_user_step_otp_registration_form():
    """A generated OTP opens the TOTP registration step."""
    flow = _flow()
    flow.login = _login()
    flow.login.get_totp_token.return_value = "123456"
    flow.config = {
        CONF_EMAIL: EMAIL,
        CONF_URL: URL,
        CONF_PASSWORD: PASSWORD,
        CONF_DEBUG: False,
    }

    with (
        patch(
            "custom_components.alexa_media.config_flow.get_url",
            return_value="http://ha",
        ),
        patch(
            "custom_components.alexa_media.config_flow.ClientSession",
            return_value=_SessionContext(200),
        ),
    ):
        result = await flow.async_step_user(_user_input(**{CONF_OTPSECRET: "1234"}))

    assert result["type"] == "form"
    assert result["step_id"] == "totp_register"


@pytest.mark.asyncio
async def test_start_proxy_invalid_url_and_missing_session():
    """Proxy setup handles an invalid URL and a missing session."""
    flow = _flow()
    flow.login = _login()
    flow.proxy = None
    flow.config = {CONF_HASS_URL: "http://ha"}

    with patch(
        "custom_components.alexa_media.config_flow.AlexaProxy",
        side_effect=ValueError("bad url"),
    ):
        result = await flow.async_step_start_proxy()
    assert result["errors"] == {"base": "invalid_url"}

    flow.proxy = MagicMock()
    flow.proxy.session = None
    flow.proxy.change_login = MagicMock()
    flow.proxy.access_url.return_value = YarlURL("http://proxy")
    flow.proxy.all_handler = MagicMock()
    flow.flow_id = "flow"
    flow.hass.data = {}
    flow.hass.http.register_view = MagicMock()
    flow.async_external_step = MagicMock(return_value={"type": "external"})

    result = await flow.async_step_start_proxy()
    assert result == {"type": "external"}


def _request(hass, path="/auth/alexamedia/proxy/flow?config_flow_id=flow", **kwargs):
    app = web.Application()
    app["hass"] = hass
    return make_mocked_request("GET", path, app=app, **kwargs)


@pytest.mark.asyncio
async def test_proxy_view_debug_logging_and_errors():
    """The proxy wrapper logs redacted data and maps handler errors."""
    hass = MagicMock()
    hass.config_entries.flow.async_progress.return_value = [
        {"flow_id": "flow", "handler": DOMAIN}
    ]
    view = AlexaMediaAuthorizationProxyView()
    handler = AsyncMock(
        return_value=web.Response(text="ok", headers={"Set-Cookie": "secret"})
    )
    view.handlers["flow"] = handler
    request = _request(hass, headers={"Authorization": "secret"})

    with patch(
        "custom_components.alexa_media.config_flow._LOGGER.isEnabledFor",
        return_value=True,
    ):
        response = await view.check_auth()(request, config_flow_id="flow")
    assert response.text == "ok"

    handler.side_effect = httpx.ConnectError("down")
    response = await view.check_auth()(request, config_flow_id="flow")
    assert "Connection Error" in response.text

    handler.side_effect = web.HTTPFound("/redirect")
    with pytest.raises(web.HTTPFound):
        await view.check_auth()(request, config_flow_id="flow")

    handler.side_effect = RuntimeError("boom")
    response = await view.check_auth()(request, config_flow_id="flow")
    assert "unexpected error" in response.text.lower()


@pytest.mark.asyncio
async def test_proxy_view_rejects_missing_or_mismatched_flow():
    """Missing, mismatched and unknown flows are unauthorized."""
    hass = MagicMock()
    hass.config_entries.flow.async_progress.return_value = []
    view = AlexaMediaAuthorizationProxyView()
    request = _request(hass)

    with pytest.raises(Unauthorized):
        await view.check_auth()(request)
    with pytest.raises(Unauthorized):
        await view.check_auth()(request, config_flow_id="other")
    with pytest.raises(Unauthorized):
        await view.check_auth()(request, config_flow_id="flow")


@pytest.mark.asyncio
async def test_callback_view_success_and_bad_flow():
    """The callback configures the flow and rejects invalid flow IDs."""
    hass = MagicMock()
    hass.config_entries.flow.async_configure = AsyncMock()
    view = AlexaMediaAuthorizationCallbackView()
    request = _request(hass, path="/auth/alexamedia/callback?flow_id=flow")

    response = await view.get(request)
    assert "Success" in response.text
    hass.config_entries.flow.async_configure.assert_awaited_once()

    bad = _request(hass, path="/auth/alexamedia/callback")
    with pytest.raises(Exception):
        await view.get(bad)


@pytest.mark.asyncio
async def test_user_step_invalid_otp_key():
    """An invalid OTP key creating a login returns the user form error."""
    flow = _flow()
    flow.login = None
    flow.config = {}

    with (
        patch(
            "custom_components.alexa_media.config_flow.get_url",
            return_value="http://ha",
        ),
        patch(
            "custom_components.alexa_media.config_flow.calculate_uuid",
            new_callable=AsyncMock,
            return_value={"uuid": "uuid"},
        ),
        patch(
            "custom_components.alexa_media.config_flow.AlexaLogin",
            side_effect=AlexapyPyotpInvalidKey("bad"),
        ),
    ):
        result = await flow.async_step_user(_user_input(**{CONF_OTPSECRET: "bad"}))

    assert result["errors"] == {"base": "2fa_key_invalid"}


@pytest.mark.asyncio
async def test_legacy_creates_login_when_no_loaded_account():
    """The legacy step creates a login when the runtime account is absent."""
    flow = _flow()
    flow.login = None
    flow.config = {
        CONF_EMAIL: EMAIL,
        CONF_URL: URL,
        CONF_PASSWORD: PASSWORD,
        CONF_DEBUG: False,
    }
    new_login = _login()
    flow._test_login = AsyncMock(return_value={"type": "create_entry"})

    with (
        patch(
            "custom_components.alexa_media.config_flow.calculate_uuid",
            new_callable=AsyncMock,
            return_value={"uuid": "uuid"},
        ),
        patch(
            "custom_components.alexa_media.config_flow.AlexaLogin",
            return_value=new_login,
        ),
    ):
        result = await flow.async_step_user_legacy(
            {CONF_EMAIL: EMAIL, CONF_URL: URL, CONF_PASSWORD: PASSWORD}
        )

    assert result == {"type": "create_entry"}
    assert flow.login is new_login


@pytest.mark.asyncio
async def test_reauth_reuses_loaded_login_and_handles_missing_account():
    """Reauth reuses a loaded login and handles a missing account."""
    flow = _flow()
    flow.context = {"entry_id": "entry"}
    flow.hass.config_entries.async_get_entry.return_value = MagicMock()
    flow.config = {CONF_EMAIL: EMAIL}
    login = _login()
    login.stats = {
        "login_timestamp": __import__("datetime").datetime.now()
        - __import__("datetime").timedelta(minutes=5)
    }
    flow.hass.data[DATA_ALEXAMEDIA]["accounts"][EMAIL] = {"login_obj": login}
    flow.async_step_user_legacy = AsyncMock(return_value={"type": "create_entry"})

    with patch("custom_components.alexa_media.config_flow.sleep", new=AsyncMock()):
        result = await flow.async_step_reauth(None)
    assert result == {"type": "create_entry"}
    assert flow.login is login

    # No runtime account: the KeyError branch leaves login unset.
    flow.hass.data[DATA_ALEXAMEDIA]["accounts"].clear()
    flow.login = None
    with patch("custom_components.alexa_media.config_flow.sleep", new=AsyncMock()):
        result = await flow.async_step_reauth(None)
    assert result == {"type": "create_entry"}
    assert flow.login is None


@pytest.mark.asyncio
async def test_test_login_securitycode_saved_and_fallback():
    """A saved security code is submitted, and an empty code is not generated."""
    flow = _flow()
    flow.async_step_user_legacy = AsyncMock(return_value={"type": "create_entry"})
    flow.async_show_form = MagicMock(
        side_effect=lambda **kwargs: {"type": "form", **kwargs}
    )
    flow.login = _login({"securitycode_required": True})
    flow.login.get_totp_token.return_value = ""
    flow.securitycode = "654321"
    flow.automatic_steps = 0

    with patch("custom_components.alexa_media.config_flow.sleep", new=AsyncMock()):
        result = await flow._test_login()
    assert result == {"type": "create_entry"}
    assert flow.async_step_user_legacy.call_args.kwargs["user_input"] == {
        CONF_SECURITYCODE: "654321"
    }


def test_options_flow_legacy_ha_version_sets_entry():
    """Older Home Assistant versions receive config_entry in __init__."""
    entry = MagicMock()
    with (
        patch("custom_components.alexa_media.config_flow.HAVERSION", "2024.1.0"),
        patch.object(
            config_entries.OptionsFlow,
            "config_entry",
            property(
                lambda self: self._config_entry,
                lambda self, value: setattr(self, "_config_entry", value),
            ),
        ),
    ):
        flow = OptionsFlowHandler(entry)

    assert flow._config_entry is entry


@pytest.mark.asyncio
async def test_options_flow_factory_and_empty_form():
    """The options flow can be created and shows the form without input."""
    entry = MagicMock()
    entry.options = {}
    entry.data = {}

    flow = OptionsFlowHandler(entry)
    flow.hass = MagicMock()
    flow._config_entry = entry
    flow.async_show_form = MagicMock(
        side_effect=lambda **kwargs: {"type": "form", **kwargs}
    )

    assert isinstance(
        AlexaMediaFlowHandler.async_get_options_flow(entry), OptionsFlowHandler
    )
    result = await flow.async_step_init()
    assert result["type"] == "form"
    flow.async_show_form.assert_called_once()
