"""Tests for notify module."""

from unittest.mock import MagicMock


from custom_components.alexa_media.const import DATA_ALEXAMEDIA


class TestAlexaNotificationServiceDevices:
    """Test the devices property of AlexaNotificationService."""

    def test_devices_returns_empty_when_accounts_key_missing(self):
        """Test devices returns empty list when 'accounts' key doesn't exist."""
        from custom_components.alexa_media.notify import AlexaNotificationService

        hass = MagicMock()
        # DATA_ALEXAMEDIA exists but 'accounts' key is missing
        hass.data = {DATA_ALEXAMEDIA: {}}

        service = AlexaNotificationService(hass)
        result = service.devices

        assert result == []

    def test_devices_returns_empty_when_accounts_is_empty(self):
        """Test devices returns empty list when accounts dict is empty."""
        from custom_components.alexa_media.notify import AlexaNotificationService

        hass = MagicMock()
        hass.data = {DATA_ALEXAMEDIA: {"accounts": {}}}

        service = AlexaNotificationService(hass)
        result = service.devices

        assert result == []

    def test_devices_returns_media_players_when_accounts_exist(self):
        """Test devices returns media players from all accounts."""
        from custom_components.alexa_media.notify import AlexaNotificationService

        hass = MagicMock()

        mock_player1 = MagicMock()
        mock_player2 = MagicMock()

        hass.data = {
            DATA_ALEXAMEDIA: {
                "accounts": {
                    "test@example.com": {
                        "entities": {
                            "media_player": {
                                "device1": mock_player1,
                                "device2": mock_player2,
                            }
                        }
                    }
                }
            }
        }

        service = AlexaNotificationService(hass)
        result = service.devices

        assert len(result) == 2
        assert mock_player1 in result
        assert mock_player2 in result

    def test_devices_handles_multiple_accounts(self):
        """Test devices aggregates media players from multiple accounts."""
        from custom_components.alexa_media.notify import AlexaNotificationService

        hass = MagicMock()

        mock_player1 = MagicMock()
        mock_player2 = MagicMock()
        mock_player3 = MagicMock()

        hass.data = {
            DATA_ALEXAMEDIA: {
                "accounts": {
                    "user1@example.com": {
                        "entities": {
                            "media_player": {
                                "device1": mock_player1,
                            }
                        }
                    },
                    "user2@example.com": {
                        "entities": {
                            "media_player": {
                                "device2": mock_player2,
                                "device3": mock_player3,
                            }
                        }
                    },
                }
            }
        }

        service = AlexaNotificationService(hass)
        result = service.devices

        assert len(result) == 3
        assert mock_player1 in result
        assert mock_player2 in result
        assert mock_player3 in result

    def test_devices_logic_fix_prevents_keyerror(self):
        """Test that the 'or' logic prevents KeyError when accounts key is missing.

        This test specifically verifies the bug fix where 'and' was changed to 'or'.
        With 'and', if 'accounts' was not in DATA_ALEXAMEDIA, Python would still
        evaluate the second condition, causing a KeyError.
        With 'or', if 'accounts' is not present, the function returns early.
        """
        from custom_components.alexa_media.notify import AlexaNotificationService

        hass = MagicMock()
        # Simulate the edge case: DATA_ALEXAMEDIA exists but without 'accounts'
        hass.data = {DATA_ALEXAMEDIA: {"other_key": "value"}}

        service = AlexaNotificationService(hass)

        # This should NOT raise KeyError - the fix ensures early return
        result = service.devices

        assert result == []
