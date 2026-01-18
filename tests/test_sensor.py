"""Tests for sensor module.

Tests the sensor functionality using pytest-homeassistant-custom-component.
"""

import datetime
import importlib
import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def _ensure_homeassistant_const_version(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure `homeassistant.const.__version__` exists for sensor import."""
    ha_const = importlib.import_module("homeassistant.const")
    monkeypatch.setattr(ha_const, "__version__", "2025.1.0", raising=False)


@pytest.fixture
def sensor_cls() -> type:
    from custom_components.alexa_media.sensor import AlexaMediaNotificationSensor
    return AlexaMediaNotificationSensor


class TestUpdateRecurringAlarm:
    """Test the _update_recurring_alarm method of AlexaMediaNotificationSensor.

    This class tests the fix for a critical bug where alarm.isoweekday was used
    instead of alarm.isoweekday() - missing the parentheses to actually call the
    method. Without the parentheses, the condition would compare a method object
    to integers, which would always be True, causing incorrect alarm scheduling.
    """

    def test_isoweekday_method_is_called_correctly(self, sensor_cls) -> None:
        """Test that isoweekday() is called as a method, not accessed as attribute.

        This is a regression test for a bug where alarm.isoweekday was used instead
        of alarm.isoweekday(). Without the parentheses, a method object would be
        compared to integers in the recurrence set, which would never match,
        causing the while loop to run indefinitely or produce wrong results.

        The bug would manifest when:
        - An alarm is set to ON
        - The alarm has a recurring pattern (e.g., "every Monday")
        - The current alarm time is in the past
        - The current alarm day doesn't match the recurrence pattern

        With the bug, the condition `alarm.isoweekday not in recurrence` would
        always be True (method object never equals an integer), potentially
        causing infinite loops or incorrect alarm times.
        """
        # Create a minimal mock for the sensor
        sensor = object.__new__(sensor_cls)
        sensor._sensor_property = "alarmTime"

        # Create a datetime that is a Wednesday (isoweekday() == 3)
        # and set it in the past so the while loop condition is met
        wednesday_in_past = datetime.datetime(2024, 1, 3, 8, 0, 0)  # Wednesday
        assert wednesday_in_past.isoweekday() == 3  # Verify it's Wednesday

        # Create recurrence that only allows Fridays (isoweekday 5)
        # This means the alarm should advance to the next Friday
        recurrence_fridays_only = {5}

        # Create the alarm notification data
        value = (
            "alarm_id",
            {
                "status": "ON",
                "alarmTime": wednesday_in_past,
                "type": "Alarm",
                "recurringPattern": "XXXX-WXX-5",  # Every Friday
            },
        )

        # Mock dt.now() to return a time after the alarm
        # so the condition `alarm < dt.now()` is True
        future_time = datetime.datetime(2024, 1, 10, 8, 0, 0)

        with (
            patch(
                "custom_components.alexa_media.sensor.dt.now", return_value=future_time
            ),
            patch(
                "custom_components.alexa_media.sensor.RECURRING_PATTERN_ISO_SET",
                {"XXXX-WXX-5": recurrence_fridays_only},
            ),
        ):
            result = sensor._update_recurring_alarm(value)

        # The alarm should have been advanced from Wednesday (Jan 3)
        # to Friday (Jan 5) since only Fridays are in the recurrence
        result_alarm = result[1]["alarmTime"]

        # With the fix: isoweekday() returns 3, which is not in {5},
        # so days are added until isoweekday() returns 5 (Friday)
        assert result_alarm.isoweekday() == 5, (
            f"Alarm should be on Friday (isoweekday 5), "
            f"but got isoweekday {result_alarm.isoweekday()}"
        )

        # Verify the alarm moved forward (not backward)
        assert result_alarm >= wednesday_in_past

    def test_recurring_alarm_advances_to_correct_weekday(self, sensor_cls) -> None:
        """Test that a recurring alarm advances to the correct weekday."""
        sensor = object.__new__(sensor_cls)
        sensor._sensor_property = "alarmTime"

        # Monday January 1, 2024
        monday = datetime.datetime(2024, 1, 1, 8, 0, 0)
        assert monday.isoweekday() == 1

        # Recurrence only on weekends (Saturday=6, Sunday=7)
        weekend_recurrence = {6, 7}

        value = (
            "alarm_id",
            {
                "status": "ON",
                "alarmTime": monday,
                "type": "Alarm",
                "recurringPattern": "XXXX-WE",  # Weekends
            },
        )

        future_time = datetime.datetime(2024, 1, 10, 8, 0, 0)

        with (
            patch(
                "custom_components.alexa_media.sensor.dt.now", return_value=future_time
            ),
            patch(
                "custom_components.alexa_media.sensor.RECURRING_PATTERN_ISO_SET",
                {"XXXX-WE": weekend_recurrence},
            ),
        ):
            result = sensor._update_recurring_alarm(value)

        result_alarm = result[1]["alarmTime"]

        # Should advance to Saturday (Jan 6, 2024)
        assert result_alarm.isoweekday() in {
            6,
            7,
        }, f"Alarm should be on weekend, but got isoweekday {result_alarm.isoweekday()}"
        assert result_alarm == datetime.datetime(2024, 1, 6, 8, 0, 0)

    def test_alarm_on_correct_day_not_modified(self, sensor_cls) -> None:
        """Test that an alarm already on a correct day is not modified."""
        sensor = object.__new__(sensor_cls)
        sensor._sensor_property = "alarmTime"

        # Friday January 5, 2024
        friday = datetime.datetime(2024, 1, 5, 8, 0, 0)
        assert friday.isoweekday() == 5

        # Recurrence includes Friday
        recurrence_with_friday = {5}

        value = (
            "alarm_id",
            {
                "status": "ON",
                "alarmTime": friday,
                "type": "Alarm",
                "recurringPattern": "XXXX-WXX-5",
            },
        )

        # Even with future time, alarm should not advance if it's already on correct day
        # Note: the loop only runs if alarm < dt.now(), so if alarm is in the past
        # but on correct day, it won't advance
        past_time = datetime.datetime(2024, 1, 4, 8, 0, 0)  # Thursday before alarm

        with (
            patch(
                "custom_components.alexa_media.sensor.dt.now", return_value=past_time
            ),
            patch(
                "custom_components.alexa_media.sensor.RECURRING_PATTERN_ISO_SET",
                {"XXXX-WXX-5": recurrence_with_friday},
            ),
        ):
            result = sensor._update_recurring_alarm(value)

        # Alarm should not be modified since it's in the future relative to now
        assert result[1]["alarmTime"] == friday

    def test_alarm_off_not_advanced(self, sensor_cls) -> None:
        """Test that an alarm with status OFF is not advanced."""
        sensor = object.__new__(sensor_cls)
        sensor._sensor_property = "alarmTime"

        wednesday = datetime.datetime(2024, 1, 3, 8, 0, 0)

        value = (
            "alarm_id",
            {
                "status": "OFF",  # Alarm is OFF
                "alarmTime": wednesday,
                "type": "Alarm",
                "recurringPattern": "XXXX-WXX-5",
            },
        )

        future_time = datetime.datetime(2024, 1, 10, 8, 0, 0)

        with (
            patch(
                "custom_components.alexa_media.sensor.dt.now", return_value=future_time
            ),
            patch(
                "custom_components.alexa_media.sensor.RECURRING_PATTERN_ISO_SET",
                {"XXXX-WXX-5": {5}},
            ),
        ):
            result = sensor._update_recurring_alarm(value)

        # Alarm should NOT be advanced since status is OFF
        assert result[1]["alarmTime"] == wednesday

    def test_alarm_without_recurrence_not_modified(self, sensor_cls) -> None:
        """Test that an alarm without recurring pattern is not modified."""
        sensor = object.__new__(sensor_cls)
        sensor._sensor_property = "alarmTime"

        wednesday = datetime.datetime(2024, 1, 3, 8, 0, 0)

        value = (
            "alarm_id",
            {
                "status": "ON",
                "alarmTime": wednesday,
                "type": "Alarm",
                # No recurringPattern
            },
        )

        future_time = datetime.datetime(2024, 1, 10, 8, 0, 0)

        with patch(
            "custom_components.alexa_media.sensor.dt.now", return_value=future_time
        ):
            result = sensor._update_recurring_alarm(value)

        # Alarm should NOT be advanced since there's no recurrence pattern
        assert result[1]["alarmTime"] == wednesday

    def test_reminder_type_handled(self, sensor_cls) -> None:
        """Test that reminder type alarms are handled correctly."""
        sensor = object.__new__(sensor_cls)
        sensor._sensor_property = "alarmTime"  # Reminders also use alarmTime

        wednesday = datetime.datetime(2024, 1, 3, 8, 0, 0)

        value = (
            "reminder_id",
            {
                "status": "ON",
                "alarmTime": wednesday,
                "type": "Reminder",
                "recurringPattern": "XXXX-WXX-5",
            },
        )

        future_time = datetime.datetime(2024, 1, 10, 8, 0, 0)

        with (
            patch(
                "custom_components.alexa_media.sensor.dt.now", return_value=future_time
            ),
            patch(
                "custom_components.alexa_media.sensor.RECURRING_PATTERN_ISO_SET",
                {"XXXX-WXX-5": {5}},
            ),
        ):
            result = sensor._update_recurring_alarm(value)

        result_alarm = result[1]["alarmTime"]
        # Reminders should also be advanced correctly
        assert result_alarm.isoweekday() == 5
