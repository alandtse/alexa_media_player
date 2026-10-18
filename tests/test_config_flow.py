"""Tests for config_flow module."""

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
    """Tests for refreshing the proxy handler between authentication rounds."""

    @pytest.mark.asyncio
    async def test_start_proxy_updates_existing_view_handler(self):
        """A reused view dispatches requests to the fresh proxy's handler."""
        flow = AlexaMediaFlowHandler()
        flow.hass = MagicMock()
        flow.flow_id = "test_flow_id"
        flow.config[CONF_HASS_URL] = "http://homeassistant.local:8123"
        flow.login = MagicMock()
        flow.login.email = "test@example.com"
        flow.login.url = "amazon.it"
        old_handler = AsyncMock()
        fresh_proxy = MagicMock()
        fresh_proxy.all_handler = AsyncMock()
        fresh_proxy.access_url.return_value = URL(
            "http://homeassistant.local:8123/auth/alexamedia/proxy"
        )

        # Restore shared view state after the test.
        with (
            patch.object(AlexaMediaAuthorizationProxyView, "known_ips", {}),
            patch(
                "custom_components.alexa_media.config_flow.AlexaProxy",
                return_value=fresh_proxy,
            ) as proxy_class,
        ):
            view = flow.proxy_view = AlexaMediaAuthorizationProxyView(old_handler)
            assert view.handler is old_handler

            result = await flow.async_step_start_proxy()

            assert result["step_id"] == "check_proxy"
            assert flow.proxy_view is view
            assert view.handler is fresh_proxy.all_handler
            proxy_class.assert_called_once()
            fresh_proxy.change_login.assert_called_once_with(flow.login)

            request = MagicMock()
            request.app = {"hass": flow.hass}
            request.remote = "127.0.0.1"
            request.url = URL("http://localhost/?config_flow_id=test_flow_id")
            flow.hass.config_entries.flow.async_progress.return_value = [
                {"flow_id": flow.flow_id}
            ]

            response = await view.get(request)

            assert response is fresh_proxy.all_handler.return_value
            fresh_proxy.all_handler.assert_awaited_once_with(request)
            old_handler.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_separate_views_keep_isolated_handlers(self):
        """Creating or refreshing another view cannot change a view's dispatch."""
        first_handler = AsyncMock()
        second_handler = AsyncMock()
        fresh_handler = AsyncMock()
        with patch.object(AlexaMediaAuthorizationProxyView, "known_ips", {}):
            first_view = AlexaMediaAuthorizationProxyView(first_handler)
            second_view = AlexaMediaAuthorizationProxyView(second_handler)
            request = MagicMock()
            request.remote = "127.0.0.1"
            request.url = URL("http://localhost/?config_flow_id=test_flow_id")
            hass = MagicMock()
            request.app = {"hass": hass}
            hass.config_entries.flow.async_progress.return_value = [
                {"flow_id": "test_flow_id"}
            ]

            assert await first_view.get(request) is first_handler.return_value
            assert await second_view.post(request) is second_handler.return_value
            second_view.handler = fresh_handler
            assert await first_view.get(request) is first_handler.return_value
            assert await second_view.post(request) is fresh_handler.return_value

            first_handler.assert_has_awaits([((request,), {}), ((request,), {})])
            assert first_handler.await_count == 2
            second_handler.assert_awaited_once_with(request)
            fresh_handler.assert_awaited_once_with(request)


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
