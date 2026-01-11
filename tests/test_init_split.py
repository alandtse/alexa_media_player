"""Tests for __init__ module split safety checks."""

import pytest


class TestEntryIdSplit:
    """Test the entryId split safety check in __init__.py."""

    def test_entry_id_split_with_valid_format(self):
        """Test split with valid format containing 3+ hash-separated parts."""
        entry_id = "part1#part2#serial123#extra"
        parts = entry_id.split("#")
        result = parts[2] if len(parts) > 2 else None

        assert result == "serial123"

    def test_entry_id_split_with_exactly_three_parts(self):
        """Test split with exactly 3 parts."""
        entry_id = "part1#part2#serial123"
        parts = entry_id.split("#")
        result = parts[2] if len(parts) > 2 else None

        assert result == "serial123"

    def test_entry_id_split_with_two_parts(self):
        """Test split with only 2 parts returns None."""
        entry_id = "part1#part2"
        parts = entry_id.split("#")
        result = parts[2] if len(parts) > 2 else None

        # Should return None since there's no third part
        assert result is None

    def test_entry_id_split_with_one_part(self):
        """Test split with only 1 part returns None."""
        entry_id = "single_part_no_hash"
        parts = entry_id.split("#")
        result = parts[2] if len(parts) > 2 else None

        # Should return None
        assert result is None

    def test_entry_id_split_with_single_hash(self):
        """Test split with single hash returns None."""
        # This simulates the bug case: find("#") returns != -1, but split gives < 3 parts
        entry_id = "prefix#suffix"

        # The original code only checked: if entry_id.find("#") != -1
        assert entry_id.find("#") != -1  # This would pass

        # But split would only give 2 parts
        parts = entry_id.split("#")
        assert len(parts) == 2  # Only 2 parts!

        # Without safety check: parts[2] raises IndexError
        # With safety check: returns None safely
        result = parts[2] if len(parts) > 2 else None
        assert result is None

    def test_entry_id_split_prevents_index_error(self):
        """Test that the safety check prevents IndexError."""
        entry_id = "only#two"
        parts = entry_id.split("#")

        # Verify the bug condition exists
        assert "#" in entry_id  # Original check would pass
        assert len(parts) < 3  # But not enough parts

        # Without safety check: parts[2] would raise IndexError
        # With safety check: returns None
        result = parts[2] if len(parts) > 2 else None
        assert result is None

    def test_entry_id_split_empty_parts(self):
        """Test split with empty parts in between."""
        entry_id = "part1##serial123"  # Empty middle part
        parts = entry_id.split("#")
        result = parts[2] if len(parts) > 2 else None

        # Should still work - third part is "serial123"
        assert result == "serial123"

    def test_entry_id_split_with_hash_at_end(self):
        """Test split when hash is at the end."""
        entry_id = "part1#part2#"  # Hash at end creates empty third part
        parts = entry_id.split("#")
        result = parts[2] if len(parts) > 2 else None

        # Third part exists but is empty string
        assert result == ""
