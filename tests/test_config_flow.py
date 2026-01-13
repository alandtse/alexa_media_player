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
        mock_login.access_token = "test_token"  # noqa: S105
        mock_login.refresh_token = "test_refresh"  # noqa: S105
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
