"""Tests for the Alexa Media config flow.

These tests verify the configuration flow behavior, particularly around error handling
and form display when users encounter issues during setup.
"""

import sys
from unittest.mock import MagicMock

import pytest

# Mock the homeassistant and alexapy modules before importing config_flow
sys.modules["homeassistant"] = MagicMock()
sys.modules["homeassistant.config_entries"] = MagicMock()
sys.modules["homeassistant.components"] = MagicMock()
sys.modules["homeassistant.components.http"] = MagicMock()
sys.modules["homeassistant.components.http.view"] = MagicMock()
sys.modules["homeassistant.components.persistent_notification"] = MagicMock()
sys.modules["homeassistant.const"] = MagicMock()
sys.modules["homeassistant.core"] = MagicMock()
sys.modules["homeassistant.data_entry_flow"] = MagicMock()
sys.modules["homeassistant.exceptions"] = MagicMock()
sys.modules["homeassistant.helpers"] = MagicMock()
sys.modules["homeassistant.helpers.network"] = MagicMock()
sys.modules["homeassistant.util"] = MagicMock()
sys.modules["awesomeversion"] = MagicMock()
sys.modules["dictor"] = MagicMock()
sys.modules["aiohttp"] = MagicMock()
sys.modules["aiohttp.web"] = MagicMock()
sys.modules["aiohttp.web_response"] = MagicMock()
sys.modules["aiohttp.web_exceptions"] = MagicMock()
sys.modules["httpx"] = MagicMock()
sys.modules["yarl"] = MagicMock()
sys.modules["async_timeout"] = MagicMock()
sys.modules["wrapt"] = MagicMock()


# Define the exception class that will be raised
class AlexapyPyotpInvalidKey(Exception):
    """Exception raised when an invalid OTP key is provided."""

    pass


# Mock alexapy with our exception
mock_alexapy = MagicMock()
mock_alexapy.AlexapyPyotpInvalidKey = AlexapyPyotpInvalidKey
mock_alexapy.AlexaLogin = MagicMock()
mock_alexapy.AlexaProxy = MagicMock()
mock_alexapy.AlexapyConnectionError = Exception
mock_alexapy.hide_email = MagicMock(return_value="***@***.com")
mock_alexapy.obfuscate = MagicMock(return_value="***")
sys.modules["alexapy"] = mock_alexapy


# Configuration constants
CONF_URL = "url"
CONF_EMAIL = "email"
CONF_PASSWORD = "password"  # nosec B105 - This is a config key name, not a value
CONF_OTPSECRET = "otp_secret"
CONF_HASS_URL = "hass_url"
CONF_DEBUG = "debug"
CONF_OAUTH = "oauth"
CONF_SECURITYCODE = "securitycode"
CONF_PUBLIC_URL = "public_url"
CONF_INCLUDE_DEVICES = "include_devices"
CONF_EXCLUDE_DEVICES = "exclude_devices"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_QUEUE_DELAY = "queue_delay"
CONF_EXTENDED_ENTITY_DISCOVERY = "extended_entity_discovery"
DATA_ALEXAMEDIA = "alexa_media"


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

        # Find the AlexapyPyotpInvalidKey exception handler
        # The code should look like:
        # except AlexapyPyotpInvalidKey:
        #     return self.async_show_form(
        #         step_id="user",
        #         data_schema=vol.Schema(self.proxy_schema),
        #         errors={"base": "2fa_key_invalid"},
        #         ...

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

    def test_data_schema_appears_before_errors_in_form_call(self):
        """Test that data_schema appears in the correct position.

        Best practice: data_schema should come after step_id but before errors,
        matching the pattern used in other async_show_form calls in the file.
        """
        with open(
            "custom_components/alexa_media/config_flow.py", encoding="utf-8"
        ) as f:
            content = f.read()

        handler_start = content.find("except AlexapyPyotpInvalidKey:")
        handler_block = content[handler_start : handler_start + 500]

        # Find positions in the handler block
        data_schema_pos = handler_block.find("data_schema")
        errors_pos = handler_block.find('errors={"base"')

        assert data_schema_pos != -1, "data_schema not found"
        assert errors_pos != -1, "errors not found"

        # data_schema should come before errors
        assert data_schema_pos < errors_pos, (
            "data_schema should appear before errors in async_show_form call "
            "to match the code style used elsewhere in the file."
        )


class TestConfigFlowConsistency:
    """Tests to verify consistency with other async_show_form calls."""

    def test_other_error_handlers_have_data_schema(self):
        """Verify consistency: other error form calls also include data_schema.

        This test checks that the AlexapyPyotpInvalidKey handler follows the
        same pattern as other error handling in config_flow.py.
        """
        with open(
            "custom_components/alexa_media/config_flow.py", encoding="utf-8"
        ) as f:
            content = f.read()

        # Find the NoURLAvailableError handler which correctly uses data_schema
        url_error_handler = content.find("NoURLAvailableError:")
        if url_error_handler == -1:
            pytest.skip("NoURLAvailableError handler not present, skipping check")

        url_error_block = content[url_error_handler : url_error_handler + 400]

        # This handler uses data_schema - our fix should match this pattern
        if "async_show_form" not in url_error_block:
            pytest.skip("NoURLAvailableError handler does not use async_show_form")

        assert "data_schema" in url_error_block, (
            "NoURLAvailableError handler uses async_show_form without "
            "data_schema - this may indicate a broader issue."
        )

    def test_vol_schema_import_exists(self):
        """Verify that voluptuous is imported for Schema creation."""
        with open(
            "custom_components/alexa_media/config_flow.py", encoding="utf-8"
        ) as f:
            content = f.read()

        # Check for voluptuous import
        assert (
            "import voluptuous as vol" in content or "from voluptuous" in content
        ), "voluptuous not imported - required for vol.Schema(self.proxy_schema)"
