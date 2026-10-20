"""Tests for config_flow module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_URL
import pytest
from yarl import URL

from custom_components.alexa_media.config_flow import (
    AlexaMediaAuthorizationProxyView,
    AlexaMediaFlowHandler,
)
from custom_components.alexa_media.const import (
    CONF_DEBUG,
    CONF_HASS_URL,
    CONF_USE_REPORTED_DOMAIN,
    DATA_ALEXAMEDIA,
)


class TestReauthReload:
    """Test that reauth triggers integration reload.

    These tests verify the fix for the bug where the integration remained
    in an error state after successful reauthentication because async_reload
    was not called.
    """

    @pytest.mark.asyncio
    async def test_reauth_triggers_reload(self):
        """Test that successful reauth calls async_reload to clear error state.

        This test verifies the fix for the bug where the integration remained
        in an error state after successful reauthentication because async_reload
        was not called.

        Test plan:
        1. Trigger a reauth flow by simulating an existing entry
        2. Complete the reauth successfully
        3. Verify that async_reload is called to clear the error state
        """
        # Create flow handler
        flow = AlexaMediaFlowHandler()
        flow.hass = MagicMock()
        flow.config = {
            "email": "test@example.com",
        }

        # Mock login object with successful status
        mock_login = MagicMock()
        mock_login.email = "test@example.com"
        mock_login.url = "https://amazon.com"
        mock_login.status = {"login_successful": True}
        mock_login.access_token = "test_token"  # nosec B105
        mock_login.refresh_token = "test_refresh"  # nosec B105
        mock_login.expires_in = 3600
        mock_login.mac_dms = "test_mac"
        mock_login.code_verifier = "test_verifier"
        mock_login.authorization_code = "test_code"
        flow.login = mock_login

        # Mock existing entry (simulates reauth scenario)
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry_id"

        # Setup hass.data structure
        flow.hass.data = {
            DATA_ALEXAMEDIA: {
                "accounts": {},
                "config_flows": {},
            }
        }

        # Mock async_set_unique_id to return existing entry (triggers reauth path)
        flow.async_set_unique_id = AsyncMock(return_value=mock_entry)

        # Mock config entries methods
        flow.hass.config_entries.async_update_entry = MagicMock()
        flow.hass.config_entries.async_reload = AsyncMock()

        # Mock other required methods
        flow.hass.bus.async_fire = MagicMock()
        flow.async_abort = MagicMock(return_value={"type": "abort"})

        # Patch async_dismiss_persistent_notification
        with patch(
            "custom_components.alexa_media.config_flow.async_dismiss_persistent_notification"
        ):
            # Call _test_login which handles reauth
            await flow._test_login()

        # Verify async_reload was called with the entry_id
        flow.hass.config_entries.async_reload.assert_called_once_with("test_entry_id")

        # Verify async_abort was called with reauth_successful
        flow.async_abort.assert_called_once_with(reason="reauth_successful")

    @pytest.mark.asyncio
    async def test_new_entry_does_not_trigger_reload(self):
        """Test that new entry creation does not call async_reload.

        Only reauth (existing entry update) should trigger reload.
        New entries should use async_create_entry instead.
        """
        flow = AlexaMediaFlowHandler()
        flow.hass = MagicMock()
        flow.config = {
            "email": "test@example.com",
        }

        # Mock login object
        mock_login = MagicMock()
        mock_login.email = "test@example.com"
        mock_login.url = "https://amazon.com"
        mock_login.status = {"login_successful": True}
        mock_login.access_token = "test_token"  # nosec B105
        mock_login.refresh_token = "test_refresh"  # nosec B105
        mock_login.expires_in = 3600
        mock_login.mac_dms = "test_mac"
        mock_login.code_verifier = "test_verifier"
        mock_login.authorization_code = "test_code"
        flow.login = mock_login

        flow.hass.data = {
            DATA_ALEXAMEDIA: {
                "accounts": {},
                "config_flows": {},
            }
        }

        # Mock async_set_unique_id to return None (no existing entry = new setup)
        flow.async_set_unique_id = AsyncMock(return_value=None)

        # Mock methods
        flow.hass.config_entries.async_reload = AsyncMock()
        flow._abort_if_unique_id_configured = MagicMock()
        flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})

        await flow._test_login()

        # Verify async_reload was NOT called for new entries
        flow.hass.config_entries.async_reload.assert_not_called()

        # Verify async_create_entry was called instead
        flow.async_create_entry.assert_called_once()

    @pytest.mark.asyncio
    async def test_reauth_updates_credentials_before_reload(self):
        """Test that credentials are updated before reload is triggered.

        The async_update_entry should be called before async_reload
        to ensure new credentials are in place.
        """
        flow = AlexaMediaFlowHandler()
        flow.hass = MagicMock()
        flow.config = {
            "email": "test@example.com",
        }

        mock_login = MagicMock()
        mock_login.email = "test@example.com"
        mock_login.url = "https://amazon.com"
        mock_login.status = {"login_successful": True}
        mock_login.access_token = "new_access_token"  # nosec B105
        mock_login.refresh_token = "new_refresh_token"  # nosec B105
        mock_login.expires_in = 3600
        mock_login.mac_dms = "test_mac"
        mock_login.code_verifier = "test_verifier"
        mock_login.authorization_code = "test_code"
        flow.login = mock_login

        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry_id"

        flow.hass.data = {
            DATA_ALEXAMEDIA: {
                "accounts": {},
                "config_flows": {},
            }
        }

        flow.async_set_unique_id = AsyncMock(return_value=mock_entry)

        # Track call order
        call_order: list[str] = []
        flow.hass.config_entries.async_update_entry = MagicMock(
            side_effect=lambda *_args, **_kwargs: call_order.append("update")
        )
        flow.hass.config_entries.async_reload = AsyncMock(
            side_effect=lambda *_args, **_kwargs: call_order.append("reload")
        )
        flow.hass.bus.async_fire = MagicMock()
        flow.async_abort = MagicMock(return_value={"type": "abort"})

        with patch(
            "custom_components.alexa_media.config_flow.async_dismiss_persistent_notification"
        ):
            await flow._test_login()

        # Verify update was called before reload
        assert call_order == [
            "update",
            "reload",
        ], f"Expected update before reload, got: {call_order}"

    @pytest.mark.asyncio
    async def test_reauth_succeeds_even_when_reload_fails(self):
        """Test that reauth completes successfully even if reload raises an exception.

        The implementation includes defensive error handling that logs a warning
        but still returns reauth_successful when async_reload fails. This ensures
        credentials are updated even if the integration can't be reloaded.
        """
        flow = AlexaMediaFlowHandler()
        flow.hass = MagicMock()
        flow.config = {
            "email": "test@example.com",
        }

        mock_login = MagicMock()
        mock_login.email = "test@example.com"
        mock_login.url = "https://amazon.com"
        mock_login.status = {"login_successful": True}
        mock_login.access_token = "test_token"  # noqa: S105  # nosec B105
        mock_login.refresh_token = "test_refresh"  # noqa: S105  # nosec B105
        mock_login.expires_in = 3600
        mock_login.mac_dms = "test_mac"
        mock_login.code_verifier = "test_verifier"
        mock_login.authorization_code = "test_code"
        flow.login = mock_login

        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry_id"

        flow.hass.data = {
            DATA_ALEXAMEDIA: {
                "accounts": {},
                "config_flows": {},
            }
        }

        flow.async_set_unique_id = AsyncMock(return_value=mock_entry)
        flow.hass.config_entries.async_update_entry = MagicMock()
        # Simulate reload failure
        flow.hass.config_entries.async_reload = AsyncMock(
            side_effect=Exception("Reload failed")
        )
        flow.hass.bus.async_fire = MagicMock()
        flow.async_abort = MagicMock(return_value={"type": "abort"})

        with patch(
            "custom_components.alexa_media.config_flow.async_dismiss_persistent_notification"
        ):
            await flow._test_login()

        # Despite reload failure, reauth should still complete successfully
        flow.async_abort.assert_called_once_with(reason="reauth_successful")
        # Credentials should have been updated
        flow.hass.config_entries.async_update_entry.assert_called_once()

    @pytest.mark.asyncio
    async def test_reauth_moves_account_when_email_changes(self):
        """Test that email-changing reauth preserves runtime account state."""

        old_email = "old@example.com"
        new_email = "new@example.com"

        flow = AlexaMediaFlowHandler()
        flow.hass = MagicMock()

        flow.config = {
            "email": new_email,
            "reauth": True,
        }

        mock_login = MagicMock()
        mock_login.email = new_email
        mock_login.url = "https://amazon.com"
        mock_login.status = {"login_successful": True}
        mock_login.access_token = "test_token"  # nosec B105
        mock_login.refresh_token = "test_refresh"  # nosec B105
        mock_login.expires_in = 3600
        mock_login.mac_dms = "test_mac"
        mock_login.code_verifier = "test_verifier"
        mock_login.authorization_code = "test_code"

        flow.login = mock_login

        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry_id"
        mock_entry.data = {"email": old_email}

        account_data = {
            "devices": {"device1": {}},
            "entities": {"media_player": {}},
            "login_obj": MagicMock(),
            "config_entry": mock_entry,
        }

        flow.hass.data = {
            DATA_ALEXAMEDIA: {
                "accounts": {
                    old_email: account_data,
                },
                "config_flows": {},
            }
        }

        flow.async_set_unique_id = AsyncMock(return_value=mock_entry)

        flow.hass.config_entries.async_update_entry = MagicMock()
        flow.hass.config_entries.async_reload = AsyncMock()

        flow.hass.bus.async_fire = MagicMock()

        flow.async_abort = MagicMock(return_value={"type": "abort"})

        with patch(
            "custom_components.alexa_media.config_flow.async_dismiss_persistent_notification"
        ):
            await flow._test_login()

        accounts = flow.hass.data[DATA_ALEXAMEDIA]["accounts"]

        assert old_email not in accounts
        assert new_email in accounts

        assert accounts[new_email]["config_entry"] is mock_entry
        assert accounts[new_email]["login_obj"] is flow.login

        flow.hass.config_entries.async_reload.assert_called_once_with(
            mock_entry.entry_id
        )

        flow.hass.config_entries.async_update_entry.assert_called_once()

        _, kwargs = flow.hass.config_entries.async_update_entry.call_args

        assert kwargs["unique_id"] == f"{new_email} - {mock_login.url}"
        assert kwargs["title"] == f"{new_email} - {mock_login.url}"

    @pytest.mark.asyncio
    async def test_reauth_aborts_when_other_config_entry_owns_unique_id(self):
        """Reauth must abort if an unloaded/disabled entry already owns the account."""
        new_email = "new@example.com"

        flow = AlexaMediaFlowHandler()
        flow.hass = MagicMock()
        flow.config = {"email": new_email, "reauth": True}

        mock_login = MagicMock()
        mock_login.email = new_email
        mock_login.url = "https://amazon.com"
        mock_login.status = {"login_successful": True}
        flow.login = mock_login

        mock_entry = MagicMock()
        mock_entry.entry_id = "reauth_entry_id"
        mock_entry.data = {"email": "old@example.com"}

        # Not loaded, so absent from runtime accounts.
        other_entry = MagicMock()
        other_entry.entry_id = "other_entry_id"
        other_entry.unique_id = f"{new_email} - {mock_login.url}"

        flow.hass.data = {
            DATA_ALEXAMEDIA: {"accounts": {}, "config_flows": {}},
        }
        flow.hass.config_entries.async_entries = MagicMock(
            return_value=[mock_entry, other_entry]
        )
        flow.hass.config_entries.async_update_entry = MagicMock()
        flow.hass.config_entries.async_reload = AsyncMock()
        flow.async_set_unique_id = AsyncMock(return_value=mock_entry)
        flow.async_abort = MagicMock(return_value={"type": "abort"})

        await flow._test_login()

        flow.async_abort.assert_called_once_with(reason="already_configured")
        flow.hass.config_entries.async_update_entry.assert_not_called()
        flow.hass.config_entries.async_reload.assert_not_called()


class TestConfigFlowInvalidOtpKeyDataSchema:
    """Tests for handling invalid OTP key errors in config flow.

    These tests verify that when a user provides an invalid 2FA/OTP key,
    the configuration flow properly displays an error form WITH the data
    schema so the user can correct their input.

    The bug: async_show_form was called without data_schema parameter when
    AlexapyPyotpInvalidKey was raised, causing the error form to display
    without any input fields. Users could see the error but had no way to
    correct their invalid OTP key.

    The fix: Add data_schema=vol.Schema(self.proxy_schema) to the
    async_show_form call in the exception handler.

    Related issues: #3254, #3243, #3189
    """

    def test_bugfix_adds_data_schema_to_exception_handler(self):
        """Test that the bugfix adds data_schema to the AlexapyPyotpInvalidKey handler.

        This test reads the actual config_flow.py source code and verifies
        that the exception handler includes data_schema in the async_show_form call.
        """
        with open(
            "custom_components/alexa_media/config_flow.py", encoding="utf-8"
        ) as f:
            content = f.read()

        # Check that the exception handler exists
        assert (
            "except AlexapyPyotpInvalidKey:" in content
        ), "AlexapyPyotpInvalidKey exception handler not found in config_flow.py"

        # Find the exception handler block
        handler_start = content.find("except AlexapyPyotpInvalidKey:")
        assert handler_start != -1

        # Get the next ~500 characters to capture the full handler
        handler_block = content[handler_start : handler_start + 500]

        # Verify the handler returns async_show_form
        assert (
            "async_show_form" in handler_block
        ), "async_show_form not found in AlexapyPyotpInvalidKey handler"

        # CRITICAL: Verify data_schema is present in the handler
        assert "data_schema" in handler_block, (
            "BUGFIX MISSING: data_schema parameter not found in "
            "AlexapyPyotpInvalidKey exception handler. "
            "Without data_schema, users cannot correct their invalid OTP key. "
            "See issues #3254, #3243, #3189."
        )

        # Verify it uses proxy_schema
        assert "proxy_schema" in handler_block, (
            "proxy_schema not found in AlexapyPyotpInvalidKey handler. "
            "The handler should use vol.Schema(self.proxy_schema) for data_schema."
        )

    def test_error_form_includes_2fa_key_invalid_error(self):
        """Test that the exception handler sets the correct error key."""
        with open(
            "custom_components/alexa_media/config_flow.py", encoding="utf-8"
        ) as f:
            content = f.read()

        handler_start = content.find("except AlexapyPyotpInvalidKey:")
        handler_block = content[handler_start : handler_start + 500]

        assert (
            "2fa_key_invalid" in handler_block
        ), "Error key '2fa_key_invalid' not found in exception handler"

    def test_error_form_includes_otp_secret_placeholder(self):
        """Test that the exception handler includes otp_secret in placeholders."""
        with open(
            "custom_components/alexa_media/config_flow.py", encoding="utf-8"
        ) as f:
            content = f.read()

        handler_start = content.find("except AlexapyPyotpInvalidKey:")
        handler_block = content[handler_start : handler_start + 500]

        assert "otp_secret" in handler_block, (
            "otp_secret placeholder not found in exception handler. "
            "Users should see which OTP key was invalid."
        )

    def test_handler_returns_user_step(self):
        """Test that the exception handler returns to the 'user' step."""
        with open(
            "custom_components/alexa_media/config_flow.py", encoding="utf-8"
        ) as f:
            content = f.read()

        handler_start = content.find("except AlexapyPyotpInvalidKey:")
        handler_block = content[handler_start : handler_start + 500]

        assert 'step_id="user"' in handler_block, (
            "step_id='user' not found in exception handler. "
            "The handler should return users to the user step for correction."
        )


class TestConfigFlowUrlCleanup:
    """Tests for cleaning Amazon region domains in config flow."""

    def test_save_user_input_strips_whitespace_from_url(self):
        """Test that accidental whitespace is removed from the Amazon domain."""
        flow = AlexaMediaFlowHandler()

        flow._save_user_input_to_config({CONF_URL: "amazon.com. au"})

        assert flow.config[CONF_URL] == "amazon.com.au"


class TestConfigFlowProxyReuse:
    """Exercise the registered router across fresh attempts and parallel flows."""

    @pytest.mark.asyncio
    async def test_router_dispatch_and_code_ownership(self):
        """Rewritten requests and callbacks keep each code on its owning login."""
        from aiohttp import web
        from aiohttp.test_utils import make_mocked_request

        from custom_components.alexa_media.const import AUTH_PROXY_NAME, DOMAIN

        hass = MagicMock()
        hass.data = {}
        hass.is_stopping = False
        flows = {}
        hass.config_entries.flow.async_progress.side_effect = lambda: [
            {"flow_id": flow_id, "handler": DOMAIN} for flow_id in flows
        ]
        app = web.Application()
        app["hass"] = hass

        def register_view(view):
            view.register(hass, app, app.router)

        hass.http.register_view.side_effect = register_view

        class RouterClient:
            """Run the real router and HA handlers without opening sockets."""

            async def __aenter__(self):
                app.freeze()
                return self

            async def __aexit__(self, *args):
                pass

            async def request(self, method, path):
                request = make_mocked_request(method, path, app=app)
                match_info = await app.router.resolve(request)
                match_info.add_app(app)
                request._match_info = match_info
                try:
                    response = await match_info.handler(request)
                except web.HTTPException as ex:
                    response = ex
                result = MagicMock()
                result.status = response.status
                result.text = AsyncMock(return_value=response.text)
                return result

            async def get(self, path):
                return await self.request("GET", path)

            async def post(self, path):
                return await self.request("POST", path)

        async def start(flow_id):
            flow = AlexaMediaFlowHandler()
            flow.hass = hass
            flow.flow_id = flow_id
            flow.config[CONF_HASS_URL] = "http://localhost"
            flow.login = MagicMock()
            flow.login.email = "test@example.com"
            flow.login.url = "amazon.com"
            flow.login.authorization_code = None
            flows[flow_id] = flow

            def proxy_factory(login, url):
                proxy = MagicMock()
                proxy.access_url.return_value = URL(url)
                proxy._login = login
                proxy.init_query = {
                    "config_flow_id": flow_id,
                    "callback_url": f"http://localhost/auth/alexamedia/callback?flow_id={flow_id}",
                }
                proxy.reset_data = AsyncMock()

                async def handle(request, **kwargs):
                    code = request.query.get("openid.oa2.authorization_code")
                    if code:
                        from alexapy import AlexaProxy

                        response = MagicMock()
                        response.url = URL(
                            "https://www.amazon.com/ap/maplanding"
                        ).with_query({"openid.oa2.authorization_code": code})
                        callback_url = await AlexaProxy.test_amazon_url(
                            proxy, response, {}, {}
                        )
                        assert URL(callback_url).query["flow_id"] == flow_id
                    return web.Response(text=flow_id)

                proxy.all_handler = AsyncMock(side_effect=handle)
                return proxy

            with patch(
                "custom_components.alexa_media.config_flow.AlexaProxy",
                side_effect=proxy_factory,
            ):
                result = await flow.async_step_start_proxy()
            assert URL(result["url"]).path.endswith("/" + flow_id)
            return flow

        first = await start("first")
        view = hass.data[AUTH_PROXY_NAME]
        async with RouterClient() as client:
            response = await client.get(
                "/auth/alexamedia/proxy/first?config_flow_id=first"
            )
            assert await response.text() == "first"
            # Abandon the first attempt, then create a fresh flow after routes freeze.
            del flows["first"]
            second = await start("second")
            third = await start("third")
            assert hass.data[AUTH_PROXY_NAME] is view
            assert hass.http.register_view.call_count == 2
            assert "first" not in view.handlers
            for flow_id, code in (("second", "code2"), ("third", "code3")):
                response = await client.post(
                    f"/auth/alexamedia/proxy/{flow_id}/ap/maplanding"
                    f"?openid.oa2.authorization_code={code}"
                )
                assert await response.text() == flow_id
            assert first.login.authorization_code is None
            assert second.login.authorization_code == "code2"
            assert third.login.authorization_code == "code3"
            # The same client/IP cannot revive a stale flow or override ownership.
            for path in (
                "/auth/alexamedia/proxy/first/ap/signin",
                "/auth/alexamedia/proxy/second?config_flow_id=third",
                "/auth/alexamedia/proxy?config_flow_id=second",
                "/auth/alexamedia/proxy/unknown/ap/signin",
            ):
                assert (await client.get(path)).status == 401

            async def configure(flow_id, user_input):
                assert flow_id == "second"
                assert second.login.authorization_code == "code2"
                await second.async_step_check_proxy()

            hass.config_entries.flow.async_configure = AsyncMock(side_effect=configure)
            response = await client.get("/auth/alexamedia/callback?flow_id=second")
            assert response.status == 200
            hass.config_entries.flow.async_configure.assert_awaited_once_with(
                flow_id="second", user_input=None
            )
            assert "second" not in view.handlers
            response = await client.post("/auth/alexamedia/proxy/third/ap/signin")
            assert await response.text() == "third"
            assert (await client.get("/auth/alexamedia/callback")).status == 400
            from homeassistant.data_entry_flow import UnknownFlow

            hass.config_entries.flow.async_configure.side_effect = UnknownFlow
            assert (
                await client.get("/auth/alexamedia/callback?flow_id=expired")
            ).status == 400

    @pytest.mark.asyncio
    @pytest.mark.parametrize("method", ["get", "post"])
    @pytest.mark.parametrize(
        ("callback_url", "allowed"),
        [
            (None, True),
            ("http://localhost/auth/alexamedia/callback?flow_id=first", True),
            ("http://localhost/auth/alexamedia/callback?flow_id=second", False),
            ("http://localhost/auth/alexamedia/callback", False),
            ("http://localhost/auth/alexamedia/callback?flow_id=", False),
            ("", False),
            ("not-a-url", False),
            ("http://[invalid/?flow_id=first", False),
        ],
    )
    async def test_callback_flow_ownership(self, method, callback_url, allowed):
        """Validate supplied callbacks before invoking the owning flow's handler."""
        from aiohttp import web
        from aiohttp.test_utils import make_mocked_request
        from homeassistant.exceptions import Unauthorized

        from custom_components.alexa_media.const import DOMAIN

        hass = MagicMock()
        hass.config_entries.flow.async_progress.return_value = [
            {"flow_id": flow_id, "handler": DOMAIN} for flow_id in ("first", "second")
        ]
        view = AlexaMediaAuthorizationProxyView()
        handler = AsyncMock(return_value=web.Response(text="first"))
        other = AsyncMock()
        view.register_handler(hass, "first", handler)
        view.register_handler(hass, "second", other)
        url = URL("/auth/alexamedia/proxy/first/ap/signin")
        if callback_url is not None:
            url = url.with_query({"callback_url": callback_url})
        app = web.Application()
        app["hass"] = hass
        request = make_mocked_request(method.upper(), str(url), app=app)

        if allowed:
            result = await getattr(view, method)(
                request, config_flow_id="first", tail="ap/signin"
            )
            assert result.text == "first"
            handler.assert_awaited_once_with(request, tail="ap/signin")
        else:
            with pytest.raises(Unauthorized):
                await getattr(view, method)(
                    request, config_flow_id="first", tail="ap/signin"
                )
            handler.assert_not_awaited()
        other.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_refresh_one_flow_does_not_replace_another(self):
        """A retry updates only its own handler, even from the same client."""
        from custom_components.alexa_media.const import DOMAIN

        hass = MagicMock()
        hass.config_entries.flow.async_progress.return_value = [
            {"flow_id": flow_id, "handler": DOMAIN} for flow_id in ("first", "second")
        ]
        view = AlexaMediaAuthorizationProxyView()
        old, other, fresh = AsyncMock(), AsyncMock(), AsyncMock()
        view.register_handler(hass, "first", old)
        view.register_handler(hass, "second", other)
        view.register_handler(hass, "first", fresh)
        request = MagicMock()
        request.app = {"hass": hass}
        request.query = {}
        await view.post(request, config_flow_id="first", tail="ap/signin")
        await view.get(request, config_flow_id="second")
        fresh.assert_awaited_once_with(request, tail="ap/signin")
        other.assert_awaited_once_with(request)
        old.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_inflight_request_keeps_handler_when_another_flow_retries(self):
        """Overlapping requests retain ownership while a third handler is installed."""
        from aiohttp import web

        from custom_components.alexa_media.const import DOMAIN

        hass = MagicMock()
        hass.config_entries.flow.async_progress.return_value = [
            {"flow_id": flow_id, "handler": DOMAIN} for flow_id in ("first", "second")
        ]
        view = AlexaMediaAuthorizationProxyView()
        entered = asyncio.Event()
        release = asyncio.Event()

        async def slow_handler(request, **kwargs):
            entered.set()
            await release.wait()
            return web.Response(text="first")

        first = AsyncMock(side_effect=slow_handler)
        old_second = AsyncMock()
        fresh_second = AsyncMock(return_value=web.Response(text="second"))
        view.register_handler(hass, "first", first)
        view.register_handler(hass, "second", old_second)
        request = MagicMock()
        request.app = {"hass": hass}
        request.query = {}
        pending = asyncio.create_task(view.post(request, config_flow_id="first"))
        try:
            await asyncio.wait_for(entered.wait(), timeout=2)
            view.register_handler(hass, "second", fresh_second)
            response = await view.post(request, config_flow_id="second")
            assert response.text == "second"
        finally:
            release.set()
            response = await asyncio.wait_for(pending, timeout=2)
        assert response.text == "first"
        first.assert_awaited_once_with(request)
        fresh_second.assert_awaited_once_with(request)
        old_second.assert_not_awaited()


class TestConfigFlowRegionalDomain:
    """Tests for country defaults and reported Amazon account domains."""

    @pytest.fixture
    def flow(self):
        """Create a flow with a successful login on the configured domain."""
        flow = AlexaMediaFlowHandler()
        flow.hass = MagicMock()
        flow.hass.config.country = "IT"
        flow.config[CONF_URL] = "amazon.com"
        flow.login = MagicMock()
        flow.login.url = "amazon.com"
        flow.login.email = "test@example.com"
        flow.login.password = "test_password"  # nosec B105
        flow.login.test_loggedin = AsyncMock(return_value=True)
        flow.login.finalize_login = AsyncMock()
        flow.login.close = AsyncMock()
        flow._test_login = AsyncMock(return_value={"type": "create_entry"})
        return flow

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("country", "expected_domain"),
        [("IT", "amazon.it"), ("ZZ", "amazon.com")],
    )
    async def test_initial_domain_default(self, country, expected_domain):
        """The initial user form defaults to the HA country or amazon.com."""
        flow = AlexaMediaFlowHandler()
        flow.hass = MagicMock()
        flow.hass.config.country = country

        with patch(
            "custom_components.alexa_media.config_flow.get_url",
            return_value="http://homeassistant.local:8123",
        ):
            result = await flow.async_step_user()

        assert result["type"] == "form"
        assert result["step_id"] == "user"
        url_field = next(key for key in result["data_schema"].schema if key == CONF_URL)
        assert url_field.default() == expected_domain
        assert flow.login is None

    @pytest.mark.asyncio
    @pytest.mark.parametrize("reported_domain", ["amazon.com", None])
    async def test_finish_proxy_without_mismatch(self, flow, reported_domain):
        """Matching or absent reported domains continue the normal login flow."""
        flow.login.reported_account_domain = reported_domain

        result = await flow.async_step_finish_proxy()

        assert result == {"type": "create_entry"}
        flow.login.test_loggedin.assert_awaited_once_with()
        flow.login.finalize_login.assert_awaited_once_with()
        flow._test_login.assert_awaited_once_with()
        flow.login.close.assert_not_awaited()
        assert flow.config[CONF_URL] == "amazon.com"

    @pytest.mark.asyncio
    async def test_finish_proxy_domain_mismatch(self, flow):
        """A mismatch offers the reported domain with both domain placeholders."""
        flow.login.reported_account_domain = "amazon.it"

        result = await flow.async_step_finish_proxy()

        assert result["type"] == "form"
        assert result["step_id"] == "domain_mismatch"
        assert result["description_placeholders"] == {
            "configured_domain": "amazon.com",
            "reported_domain": "amazon.it",
        }
        assert result["data_schema"]({}) == {CONF_USE_REPORTED_DOMAIN: True}
        flow.login.finalize_login.assert_awaited_once_with()
        flow._test_login.assert_not_awaited()
        flow.login.close.assert_not_awaited()
        assert flow.config[CONF_URL] == "amazon.com"

    @pytest.mark.asyncio
    async def test_use_reported_domain_restarts_login(self, flow):
        """Accepting the domain closes and discards the login and shows user form."""
        login = flow.login
        login.reported_account_domain = "amazon.it"
        flow.proxy = MagicMock()
        await flow.async_step_finish_proxy()

        with patch(
            "custom_components.alexa_media.config_flow.get_url",
            return_value="http://homeassistant.local:8123",
        ):
            result = await flow.async_step_domain_mismatch(
                {CONF_USE_REPORTED_DOMAIN: True}
            )

        assert flow.config[CONF_URL] == "amazon.it"
        login.close.assert_awaited_once_with()
        assert flow.login is None
        assert flow.proxy is None
        assert result["type"] == "form"
        assert result["step_id"] == "user"
        url_field = next(key for key in result["data_schema"].schema if key == CONF_URL)
        assert url_field.default() == "amazon.it"
        flow._test_login.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_use_reported_domain_keeps_loaded_account_login_open(self, flow):
        """A login reused from a loaded account is not closed or reused again."""
        login = flow.login
        login.session.closed = False
        login.reported_account_domain = "amazon.it"
        flow.config[CONF_EMAIL] = "test@example.com"
        flow.config[CONF_DEBUG] = False
        flow._loaded_login = login
        flow.hass.data = {
            DATA_ALEXAMEDIA: {"accounts": {"test@example.com": {"login_obj": login}}}
        }
        flow.proxy = MagicMock()
        await flow.async_step_finish_proxy()

        with patch(
            "custom_components.alexa_media.config_flow.get_url",
            return_value="http://homeassistant.local:8123",
        ):
            await flow.async_step_domain_mismatch({CONF_USE_REPORTED_DOMAIN: True})
            with (
                patch(
                    "custom_components.alexa_media.config_flow.calculate_uuid",
                    AsyncMock(return_value={"uuid": "uuid"}),
                ),
                patch(
                    "custom_components.alexa_media.config_flow.AlexaLogin"
                ) as new_login,
            ):
                response = MagicMock(status=200)
                get_ctx = MagicMock()
                get_ctx.__aenter__ = AsyncMock(return_value=response)
                get_ctx.__aexit__ = AsyncMock(return_value=False)
                client = MagicMock()
                client.get.return_value = get_ctx
                client_ctx = MagicMock()
                client_ctx.__aenter__ = AsyncMock(return_value=client)
                client_ctx.__aexit__ = AsyncMock(return_value=False)
                with (
                    patch(
                        "custom_components.alexa_media.config_flow.ClientSession",
                        return_value=client_ctx,
                    ),
                    patch.object(
                        flow, "async_step_start_proxy", AsyncMock()
                    ) as start_proxy,
                ):
                    await flow.async_step_user(
                        {
                            CONF_URL: "amazon.it",
                            CONF_HASS_URL: "http://homeassistant.local:8123",
                            CONF_EMAIL: "test@example.com",
                            CONF_PASSWORD: "test_password",  # nosec B105
                        }
                    )

        login.close.assert_not_awaited()
        new_login.assert_called_once()
        start_proxy.assert_awaited_once()
        assert flow.login is new_login.return_value

    @pytest.mark.asyncio
    async def test_keep_configured_domain_continues_login(self, flow):
        """Unchecking the option continues with the current login and domain."""
        login = flow.login
        login.reported_account_domain = "amazon.it"
        proxy = flow.proxy = MagicMock()
        await flow.async_step_finish_proxy()

        result = await flow.async_step_domain_mismatch(
            {CONF_USE_REPORTED_DOMAIN: False}
        )

        assert result == {"type": "create_entry"}
        flow._test_login.assert_awaited_once_with()
        assert flow.config[CONF_URL] == "amazon.com"
        assert login.url == "amazon.com"
        assert flow.login is login
        assert flow.proxy is proxy
        login.close.assert_not_awaited()
