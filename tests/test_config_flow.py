"""Tests for the secure paste-URL config flow."""

from unittest.mock import AsyncMock, MagicMock, patch

from alexapy import EnrollmentError
import pytest

from custom_components.alexa_media.config_flow import (
    CONFIG_VERSION,
    AlexaMediaFlowHandler,
)
from custom_components.alexa_media.const import (
    CONF_OAUTH,
    CONF_PASTE_URL,
    CONF_SECURE,
)

MAP_URL = (
    "https://www.amazon.com/ap/maplanding?"
    "openid.oa2.authorization_code=ANsecretcode&openid.assoc_handle=amzn"
)


def _creds(customer_id="amzn1.account.ABC"):
    creds = MagicMock()
    creds.refresh_token = "Atna|refresh"  # nosec B105
    creds.mac_dms = {"device_private_key": "k", "adp_token": "t"}
    creds.serial = "DEADBEEF"
    creds.customer_id = customer_id
    creds.domain = "amazon.com"
    creds.as_dict.return_value = {
        "refresh_token": "Atna|refresh",
        "mac_dms": {"device_private_key": "k", "adp_token": "t"},
        "serial": "DEADBEEF",
        "customer_id": customer_id,
        "domain": "amazon.com",
    }
    return creds


class TestUserStep:
    """Step 1: collect account/region and present the login URL."""

    @pytest.mark.asyncio
    async def test_shows_form_without_input(self):
        flow = AlexaMediaFlowHandler()
        flow.hass = MagicMock()
        result = await flow.async_step_user()
        assert result["type"] == "form"
        assert result["step_id"] == "user"

    @pytest.mark.asyncio
    async def test_advances_to_paste_with_login_url(self):
        flow = AlexaMediaFlowHandler()
        flow.hass = MagicMock()
        with patch(
            "custom_components.alexa_media.config_flow.EnrollmentFlow"
        ) as enroll_cls:
            enroll_cls.return_value.oauth_url = "https://www.amazon.com/ap/register?x=1"
            result = await flow.async_step_user(
                {"email": "user@example.com", "url": "amazon.com"}
            )
        assert result["type"] == "form"
        assert result["step_id"] == "paste"
        assert "amazon.com/ap/register" in result["description_placeholders"]["url"]


class TestPasteStep:
    """Step 2: parse the pasted redirect URL and register the device."""

    def _flow_at_paste(self):
        flow = AlexaMediaFlowHandler()
        flow.hass = MagicMock()
        flow.config.update({"email": "user@example.com", "url": "amazon.com"})
        flow._enrollment = MagicMock()
        flow._enrollment.oauth_url = "https://www.amazon.com/ap/register"
        return flow

    @pytest.mark.asyncio
    async def test_missing_paste_shows_error(self):
        flow = self._flow_at_paste()
        result = await flow.async_step_paste({})
        assert result["type"] == "form"
        assert result["errors"] == {"base": "paste_required"}

    @pytest.mark.asyncio
    async def test_invalid_url_shows_error(self):
        flow = self._flow_at_paste()
        flow._enrollment.parse_redirect_url.side_effect = EnrollmentError("bad host")
        result = await flow.async_step_paste({CONF_PASTE_URL: "https://evil/x"})
        assert result["errors"] == {"base": "paste_invalid"}

    @pytest.mark.asyncio
    async def test_register_failure_shows_error(self):
        flow = self._flow_at_paste()
        flow._enrollment.parse_redirect_url.return_value = "ANcode"
        flow._enrollment.async_register = AsyncMock(
            side_effect=EnrollmentError("expired code")
        )
        result = await flow.async_step_paste({CONF_PASTE_URL: MAP_URL})
        assert result["errors"] == {"base": "register_failed"}

    @pytest.mark.asyncio
    async def test_success_creates_entry_and_stores_creds(self):
        flow = self._flow_at_paste()
        flow._enrollment.parse_redirect_url.return_value = "ANcode"
        flow._enrollment.async_register = AsyncMock(return_value=_creds())
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = MagicMock()
        created = MagicMock()
        created.entry_id = "entry123"
        flow.async_create_entry = MagicMock(
            return_value={"type": "create_entry", "result": created}
        )
        store = AsyncMock()
        with patch(
            "custom_components.alexa_media.config_flow.SecureCredentialStore",
            return_value=store,
        ):
            result = await flow.async_step_paste({CONF_PASTE_URL: MAP_URL})

        assert result["type"] == "create_entry"
        # Entry is bound to the Amazon account id.
        flow.async_set_unique_id.assert_awaited_once_with("amzn1.account.ABC")
        # Credentials go to the protected store, never the entry data.
        store.async_save.assert_awaited_once()
        data = flow.async_create_entry.call_args.kwargs["data"]
        assert data[CONF_SECURE] is True
        assert "password" not in data
        assert CONF_OAUTH not in data


class TestReauth:
    """Reauth must re-enroll and must not rebind to a different account."""

    @pytest.mark.asyncio
    async def test_reauth_routes_to_user_step(self):
        flow = AlexaMediaFlowHandler()
        flow.hass = MagicMock()
        result = await flow.async_step_reauth({"email": "user@example.com"})
        assert result["type"] == "form"
        assert result["step_id"] == "user"
        assert flow.config["reauth"] is True

    @pytest.mark.asyncio
    async def test_reauth_success_updates_and_reloads(self):
        flow = AlexaMediaFlowHandler()
        flow.hass = MagicMock()
        flow.config.update(
            {"email": "user@example.com", "url": "amazon.com", "reauth": True}
        )
        flow._enrollment = MagicMock()
        flow._enrollment.parse_redirect_url.return_value = "ANcode"
        flow._enrollment.async_register = AsyncMock(return_value=_creds())
        existing = MagicMock()
        existing.entry_id = "entry123"
        flow._reauth_entry = MagicMock(return_value=existing)
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_mismatch = MagicMock()
        flow.async_abort = MagicMock(return_value={"type": "abort"})
        flow.hass.config_entries.async_update_entry = MagicMock()
        flow.hass.config_entries.async_reload = AsyncMock()
        store = AsyncMock()
        with patch(
            "custom_components.alexa_media.config_flow.SecureCredentialStore",
            return_value=store,
        ):
            result = await flow.async_step_paste({CONF_PASTE_URL: MAP_URL})

        flow._abort_if_unique_id_mismatch.assert_called_once()
        flow.hass.config_entries.async_reload.assert_awaited_once_with("entry123")
        flow.async_abort.assert_called_once_with(reason="reauth_successful")
        assert result["type"] == "abort"

    @pytest.mark.asyncio
    async def test_reauth_wrong_account_aborts(self):
        flow = AlexaMediaFlowHandler()
        flow.hass = MagicMock()
        flow.config.update(
            {"email": "user@example.com", "url": "amazon.com", "reauth": True}
        )
        flow._enrollment = MagicMock()
        flow._enrollment.parse_redirect_url.return_value = "ANcode"
        flow._enrollment.async_register = AsyncMock(
            return_value=_creds(customer_id="amzn1.account.OTHER")
        )
        existing = MagicMock()
        existing.entry_id = "entry123"
        flow._reauth_entry = MagicMock(return_value=existing)
        flow.async_set_unique_id = AsyncMock()

        def _mismatch(reason):
            raise Exception(reason)  # noqa: TRY002 — stand-in for AbortFlow

        flow._abort_if_unique_id_mismatch = MagicMock(side_effect=_mismatch)
        with (
            patch("custom_components.alexa_media.config_flow.SecureCredentialStore"),
            pytest.raises(Exception, match="wrong_account"),
        ):
            await flow.async_step_paste({CONF_PASTE_URL: MAP_URL})


def test_config_version_bumped_for_migration():
    """The schema version must advance so async_migrate_entry runs."""
    assert CONFIG_VERSION == 2
    assert AlexaMediaFlowHandler.VERSION == 2
