"""Tests for config_flow module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.alexa_media.config_flow import AlexaMediaFlowHandler
from custom_components.alexa_media.const import DATA_ALEXAMEDIA


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
