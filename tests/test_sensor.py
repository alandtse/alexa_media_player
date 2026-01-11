"""Tests for sensor module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.alexa_media.const import DATA_ALEXAMEDIA


class TestAsyncUnloadEntry:
    """Test the async_unload_entry function."""

    @pytest.mark.asyncio
    async def test_async_unload_entry_with_sensors(self):
        """Test unloading sensors iterates over sensors.values() correctly."""
        from custom_components.alexa_media.sensor import async_unload_entry

        hass = MagicMock()
        entry = MagicMock()
        entry.data = {"email": "test@example.com"}

        # Create mock sensors with async_remove method (must be AsyncMock)
        mock_sensor1 = MagicMock()
        mock_sensor1.async_remove = AsyncMock()

        mock_sensor2 = MagicMock()
        mock_sensor2.async_remove = AsyncMock()

        # Structure: account_dict["entities"]["sensor"][device_serial][sensor_type] = sensor
        hass.data = {
            DATA_ALEXAMEDIA: {
                "accounts": {
                    "test@example.com": {
                        "entities": {
                            "sensor": {
                                "device_serial_1": {
                                    "Alarm": mock_sensor1,
                                    "Timer": mock_sensor2,
                                }
                            }
                        }
                    }
                }
            }
        }

        result = await async_unload_entry(hass, entry)

        assert result is True
        mock_sensor1.async_remove.assert_called_once()
        mock_sensor2.async_remove.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_unload_entry_empty_sensors(self):
        """Test unloading when no sensors exist."""
        from custom_components.alexa_media.sensor import async_unload_entry

        hass = MagicMock()
        entry = MagicMock()
        entry.data = {"email": "test@example.com"}

        hass.data = {
            DATA_ALEXAMEDIA: {
                "accounts": {"test@example.com": {"entities": {"sensor": {}}}}
            }
        }

        result = await async_unload_entry(hass, entry)
        assert result is True

    @pytest.mark.asyncio
    async def test_async_unload_entry_sensor_without_async_remove(self):
        """Test unloading sensors that don't have async_remove method."""
        from custom_components.alexa_media.sensor import async_unload_entry

        hass = MagicMock()
        entry = MagicMock()
        entry.data = {"email": "test@example.com"}

        # Create a mock sensor without async_remove attribute
        mock_sensor = MagicMock(spec=[])  # Empty spec = no attributes

        hass.data = {
            DATA_ALEXAMEDIA: {
                "accounts": {
                    "test@example.com": {
                        "entities": {
                            "sensor": {
                                "device_serial_1": {
                                    "Alarm": mock_sensor,
                                }
                            }
                        }
                    }
                }
            }
        }

        # Should not raise, just skip the sensor
        result = await async_unload_entry(hass, entry)
        assert result is True


class TestTriggerEvent:
    """Test the _trigger_event method of AlexaMediaNotificationSensor."""

    def test_trigger_event_with_empty_active_list(self):
        """Test that _trigger_event handles empty _active list gracefully."""
        from custom_components.alexa_media.sensor import AlexaMediaNotificationSensor

        # Create a minimal mock for the sensor
        sensor = object.__new__(AlexaMediaNotificationSensor)
        sensor._active = []  # Empty list - the race condition case
        sensor._account = "test@example.com"
        sensor.hass = MagicMock()

        # Should not raise IndexError
        sensor._trigger_event(MagicMock())

        # bus.fire should NOT be called when _active is empty
        sensor.hass.bus.fire.assert_not_called()

    def test_trigger_event_with_active_notifications(self):
        """Test that _trigger_event fires event when _active has items."""
        from custom_components.alexa_media.sensor import AlexaMediaNotificationSensor

        # Create a minimal mock for the sensor
        sensor = object.__new__(AlexaMediaNotificationSensor)
        sensor._active = [("id1", {"id": "notification1", "status": "ON"})]
        sensor._account = "test@example.com"
        sensor.name = "Test Sensor"
        sensor.entity_id = "sensor.test_sensor"
        sensor.hass = MagicMock()

        mock_time = MagicMock()
        sensor._trigger_event(mock_time)

        # bus.fire should be called
        sensor.hass.bus.fire.assert_called_once()
        call_args = sensor.hass.bus.fire.call_args
        assert call_args[0][0] == "alexa_media_notification_event"
        assert call_args[1]["event_data"]["event"] == sensor._active[0]
