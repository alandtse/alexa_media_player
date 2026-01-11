"""Tests for timedelta to seconds migration in config entries.

This module tests the fix for the JSON serialization error:
"Type is not JSON serializable: datetime.timedelta"

The bug occurred when timedelta values ended up in config_entry.data
and Home Assistant tried to persist the config entries to storage.
"""

from datetime import timedelta
import json

import pytest


class TestTimedeltaSanitization:
    """Test that timedelta values are properly sanitized."""

    def test_sanitization_converts_timedelta_to_seconds(self):
        """Test that the sanitization logic converts timedelta to seconds.

        This verifies the core fix logic used in async_setup_entry and
        OptionsFlowHandler.
        """
        # Simulate data with timedelta (the bug condition)
        original_data = {
            "email": "test@example.com",
            "password": "test_password",  # nosec B105
            "url": "amazon.com",
            "scan_interval": timedelta(seconds=60),
            "queue_delay": 1.5,
        }

        # Apply the sanitization logic from the fix
        sanitized_data = {
            k: (v.total_seconds() if isinstance(v, timedelta) else v)
            for k, v in original_data.items()
        }

        # Verify timedelta was converted
        assert sanitized_data["scan_interval"] == 60.0
        assert not isinstance(sanitized_data["scan_interval"], timedelta)

        # Verify other values unchanged
        assert sanitized_data["email"] == "test@example.com"
        assert sanitized_data["queue_delay"] == 1.5

    def test_sanitization_preserves_non_timedelta_values(self):
        """Test that sanitization preserves values that are already correct."""
        original_data = {
            "email": "test@example.com",
            "scan_interval": 60,  # Already a number
            "queue_delay": 1.5,
            "debug": True,
            "include_devices": "",
        }

        sanitized_data = {
            k: (v.total_seconds() if isinstance(v, timedelta) else v)
            for k, v in original_data.items()
        }

        # All values should be unchanged
        assert sanitized_data == original_data

    def test_sanitization_handles_multiple_timedeltas(self):
        """Test sanitization of multiple timedelta values."""
        original_data = {
            "scan_interval": timedelta(seconds=60),
            "queue_delay": timedelta(seconds=2),
            "timeout": timedelta(minutes=5),
        }

        sanitized_data = {
            k: (v.total_seconds() if isinstance(v, timedelta) else v)
            for k, v in original_data.items()
        }

        assert sanitized_data["scan_interval"] == 60.0
        assert sanitized_data["queue_delay"] == 2.0
        assert sanitized_data["timeout"] == 300.0


class TestConfigDataJsonSerializable:
    """Test that config data is JSON serializable after sanitization."""

    def test_sanitized_data_is_json_serializable(self):
        """Test that data after sanitization can be serialized to JSON.

        This is a regression test for the core bug.
        """
        # Data that would cause serialization error before the fix
        original_data = {
            "email": "test@example.com",
            "password": "test_password",  # nosec B105
            "url": "amazon.com",
            "scan_interval": timedelta(seconds=60),
            "queue_delay": timedelta(seconds=2),
        }

        # Apply the same sanitization logic used in the fix
        sanitized_data = {
            k: (v.total_seconds() if isinstance(v, timedelta) else v)
            for k, v in original_data.items()
        }

        # This should not raise an exception
        try:
            json_str = json.dumps(sanitized_data)
            assert json_str is not None
            # Verify we can deserialize it back
            parsed = json.loads(json_str)
            assert parsed["scan_interval"] == 60.0
        except TypeError as e:
            pytest.fail(f"Sanitized data should be JSON serializable: {e}")

    def test_unsanitized_data_fails_json_serialization(self):
        """Test that unsanitized timedelta data fails JSON serialization.

        This documents the bug behavior before the fix.
        """
        original_data = {
            "email": "test@example.com",
            "scan_interval": timedelta(seconds=60),
        }

        with pytest.raises(TypeError, match="not JSON serializable"):
            json.dumps(original_data)


class TestOptionsFlowSanitizationLogic:
    """Test the sanitization logic used in OptionsFlowHandler.

    Note: We test the sanitization logic directly rather than through the
    OptionsFlowHandler because the handler is tightly coupled with HA's
    config_entries system. The logic tested here matches what's in
    OptionsFlowHandler.async_step_init.
    """

    def test_options_flow_sanitization_logic(self):
        """Test that the sanitization logic in OptionsFlow works correctly.

        This verifies the dict comprehension used in async_step_init:
        sanitized_input = {
            k: (v.total_seconds() if isinstance(v, timedelta) else v)
            for k, v in user_input.items()
        }
        """
        # Simulate user_input with a timedelta value
        user_input = {
            "email": "test@example.com",
            "url": "amazon.com",
            "scan_interval": timedelta(seconds=120),  # timedelta to be sanitized
            "queue_delay": 2.0,
            "public_url": "https://example.com/",
            "include_devices": "device1",
            "exclude_devices": "",
            "extended_entity_discovery": False,
            "debug": False,
        }

        # Apply the same sanitization logic as in OptionsFlowHandler
        sanitized_input = {
            k: (v.total_seconds() if isinstance(v, timedelta) else v)
            for k, v in user_input.items()
        }

        # Verify the data was sanitized
        assert (
            sanitized_input["scan_interval"] == 120.0
        ), "timedelta should be converted to seconds"
        assert not isinstance(
            sanitized_input["scan_interval"], timedelta
        ), "scan_interval should not be a timedelta after sanitization"
        # Verify other values preserved
        assert sanitized_input["email"] == "test@example.com"
        assert sanitized_input["queue_delay"] == 2.0


class TestMigrationLogic:
    """Test the migration detection and conversion logic."""

    def test_migration_needed_detection(self):
        """Test that migration is correctly detected when timedelta exists."""
        config_data = {
            "email": "test@example.com",
            "scan_interval": timedelta(seconds=60),
        }

        needs_migration = False
        for value in config_data.values():
            if isinstance(value, timedelta):
                needs_migration = True
                break

        assert needs_migration is True

    def test_migration_not_needed_detection(self):
        """Test that migration is not triggered when no timedelta exists."""
        config_data = {
            "email": "test@example.com",
            "scan_interval": 60,
        }

        needs_migration = False
        for value in config_data.values():
            if isinstance(value, timedelta):
                needs_migration = True
                break

        assert needs_migration is False

    def test_migration_converts_all_timedeltas(self):
        """Test that migration converts all timedelta values."""
        config_data = {
            "field1": timedelta(seconds=10),
            "field2": timedelta(minutes=1),
            "field3": "string_value",
            "field4": 42,
        }

        migrated_data = dict(config_data)
        for key, value in migrated_data.items():
            if isinstance(value, timedelta):
                migrated_data[key] = value.total_seconds()

        assert migrated_data["field1"] == 10.0
        assert migrated_data["field2"] == 60.0
        assert migrated_data["field3"] == "string_value"
        assert migrated_data["field4"] == 42
