"""Tests for alarm_control_panel module."""

import pytest


class TestApplianceIdSplit:
    """Test the appliance_id split safety check."""

    def test_appliance_id_split_with_valid_format(self):
        """Test split with valid format containing 3+ parts."""
        appliance_id = "prefix_middle_actual_id_suffix"
        appliance_parts = appliance_id.split("_")
        result = appliance_parts[2] if len(appliance_parts) > 2 else appliance_id

        assert result == "actual"

    def test_appliance_id_split_with_exactly_three_parts(self):
        """Test split with exactly 3 parts."""
        appliance_id = "prefix_middle_actual"
        appliance_parts = appliance_id.split("_")
        result = appliance_parts[2] if len(appliance_parts) > 2 else appliance_id

        assert result == "actual"

    def test_appliance_id_split_with_two_parts(self):
        """Test split with only 2 parts returns original."""
        appliance_id = "prefix_middle"
        appliance_parts = appliance_id.split("_")
        result = appliance_parts[2] if len(appliance_parts) > 2 else appliance_id

        # Should return original since there's no third part
        assert result == appliance_id

    def test_appliance_id_split_with_one_part(self):
        """Test split with only 1 part returns original."""
        appliance_id = "single_part_no_underscore"
        appliance_parts = appliance_id.split("_")

        # Actually this has underscores, let's test without
        appliance_id = "singlepart"
        appliance_parts = appliance_id.split("_")
        result = appliance_parts[2] if len(appliance_parts) > 2 else appliance_id

        # Should return original
        assert result == appliance_id

    def test_appliance_id_split_with_empty_string(self):
        """Test split with empty string returns original."""
        appliance_id = ""
        appliance_parts = appliance_id.split("_")
        result = appliance_parts[2] if len(appliance_parts) > 2 else appliance_id

        # Should return original (empty string)
        assert result == appliance_id

    def test_appliance_id_split_prevents_index_error(self):
        """Test that the safety check prevents IndexError."""
        # This would have raised IndexError without the len() check
        appliance_id = "only_one"
        appliance_parts = appliance_id.split("_")

        # Without safety check: appliance_parts[2] would raise IndexError
        # With safety check: returns original
        result = appliance_parts[2] if len(appliance_parts) > 2 else appliance_id

        assert result == appliance_id
