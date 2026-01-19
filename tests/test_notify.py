"""Tests for notify module.

Tests the notification service using pytest-homeassistant-custom-component.
"""

from unittest.mock import MagicMock

import pytest

from custom_components.alexa_media.const import DATA_ALEXAMEDIA
from custom_components.alexa_media.notify import AlexaNotificationService

# =============================================================================
# Tests for AlexaNotificationService.devices property
# =============================================================================


class TestNotifyDevicesProperty:
    """Test the devices property of AlexaNotificationService.

    These tests cover a critical bug fix where the `devices` property raised
    KeyError when the 'accounts' key was missing from hass.data[DATA_ALEXAMEDIA].

    The Bug (BEFORE fix):
        if "accounts" not in data and not data["accounts"].items():

    Python evaluates BOTH sides of `and`. When "accounts" is missing, accessing
    data["accounts"] raises KeyError.

    The Fix (AFTER):
        if "accounts" not in data or not data["accounts"].items():

    With `or`, Python short-circuits and skips data["accounts"] when the first
    condition is True.
    """

    def _create_service(self, hass_data: dict) -> AlexaNotificationService:
        """Create a notification service with the given hass.data."""
        service = object.__new__(AlexaNotificationService)
        service.hass = MagicMock()
        service.hass.data = hass_data
        return service

    def test_devices_keyerror_when_accounts_missing(self):
        """Test that devices property does NOT raise KeyError when accounts missing.

        This is the PRIMARY regression test for the and->or bug fix.

        The bug: Using `and` instead of `or` caused Python to evaluate
        `data["accounts"]` even when "accounts" was not in the dict.
        """
        service = self._create_service(
            {
                DATA_ALEXAMEDIA: {
                    # 'accounts' key is intentionally MISSING
                    "config_flows": {},
                }
            }
        )

        # This MUST NOT raise KeyError
        try:
            result = service.devices
        except KeyError as exc:
            pytest.fail(
                f"BUG DETECTED: KeyError raised: {exc}\n\n"
                "CAUSE: The condition uses 'and' instead of 'or':\n"
                "  WRONG: 'accounts' not in data AND data['accounts'].items()\n"
                "  RIGHT: 'accounts' not in data OR  data['accounts'].items()\n\n"
                "With 'and', Python evaluates BOTH conditions. When 'accounts'\n"
                "is missing, accessing data['accounts'] raises KeyError.\n"
                "With 'or', Python short-circuits and never accesses the key."
            )

        assert result == []

    def test_devices_empty_when_accounts_key_missing(self):
        """Test devices returns empty list when accounts key is missing."""
        service = self._create_service({DATA_ALEXAMEDIA: {"config_flows": {}}})

        result = service.devices

        assert result == [], f"Expected empty list, got: {result}"

    def test_devices_empty_when_accounts_is_empty_dict(self):
        """Test devices returns empty list when accounts exists but is empty."""
        service = self._create_service(
            {
                DATA_ALEXAMEDIA: {
                    "accounts": {},
                    "config_flows": {},
                }
            }
        )

        result = service.devices

        assert result == [], f"Expected empty list, got: {result}"

    def test_devices_empty_when_data_alexamedia_missing(self):
        """Test devices handles missing DATA_ALEXAMEDIA gracefully."""
        service = self._create_service({})

        # Should raise KeyError for DATA_ALEXAMEDIA - this is expected behavior
        # The fix only addresses the accounts key, not DATA_ALEXAMEDIA itself
        with pytest.raises(KeyError):
            _ = service.devices

    def test_devices_returns_media_players(self):
        """Test devices returns media players when accounts exist."""
        mock_player_1 = MagicMock()
        mock_player_1.name = "Living Room Echo"
        mock_player_2 = MagicMock()
        mock_player_2.name = "Kitchen Echo"

        service = self._create_service(
            {
                DATA_ALEXAMEDIA: {
                    "accounts": {
                        "test@example.com": {
                            "entities": {
                                "media_player": {
                                    "serial1": mock_player_1,
                                    "serial2": mock_player_2,
                                }
                            }
                        }
                    },
                    "config_flows": {},
                }
            }
        )

        result = service.devices

        assert len(result) == 2
        assert mock_player_1 in result
        assert mock_player_2 in result

    def test_devices_aggregates_multiple_accounts(self):
        """Test devices aggregates media players from all accounts."""
        mock_player_1 = MagicMock()
        mock_player_2 = MagicMock()

        service = self._create_service(
            {
                DATA_ALEXAMEDIA: {
                    "accounts": {
                        "user1@example.com": {
                            "entities": {"media_player": {"serial1": mock_player_1}}
                        },
                        "user2@example.com": {
                            "entities": {"media_player": {"serial2": mock_player_2}}
                        },
                    },
                    "config_flows": {},
                }
            }
        )

        result = service.devices

        assert len(result) == 2
        assert mock_player_1 in result
        assert mock_player_2 in result
