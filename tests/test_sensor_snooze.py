"""Pytest cases for the four key alarm snooze states.

Covers _normalize_alarm_snooze_state and the _is_active_notification
filter logic introduced in PR `#3440`.
"""

import datetime
from unittest.mock import MagicMock, patch

from custom_components.alexa_media.sensor import AlexaMediaNotificationSensor

UTC = datetime.timezone.utc


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_alarm_sensor():
    """Return a bare AlexaMediaNotificationSensor wired for Alarm type."""
    sensor = object.__new__(AlexaMediaNotificationSensor)
    sensor._type = "Alarm"
    sensor._sensor_property = "date_time"
    client = MagicMock()
    client._timezone = "UTC"
    sensor._client = client
    return sensor


def _alarm_value(status, alarm_time, snoozed_to=None):
    """Build a (key, dict) tuple as produced by _fix_alarm_date_time."""
    return (
        "test_alarm_id",
        {
            "status": status,
            "date_time": alarm_time,
            "snoozedToTime": snoozed_to,
            "type": "Alarm",
        },
    )


# ---------------------------------------------------------------------------
# 1. _normalize_alarm_snooze_state — four states
# ---------------------------------------------------------------------------


class TestCoerceDatetime:
    """Unit tests for _coerce_datetime."""

    UTC = datetime.timezone.utc

    def test_aware_datetime_passes_through_unchanged(self):
        """Aware datetimes should be returned unchanged."""
        sensor = _make_alarm_sensor()

        aware = datetime.datetime(2024, 6, 1, 8, 0, tzinfo=self.UTC)

        result = sensor._coerce_datetime(aware)

        assert result is aware

    def test_epoch_seconds_converted_correctly(self):
        """Epoch timestamps in seconds should convert correctly."""
        sensor = _make_alarm_sensor()

        epoch_seconds = 1717228800  # 2024-06-01 08:00:00 UTC

        result = sensor._coerce_datetime(epoch_seconds)

        expected = datetime.datetime.fromtimestamp(epoch_seconds, tz=self.UTC)

        assert result == expected
        assert result.tzinfo == self.UTC

    def test_epoch_milliseconds_converted_correctly(self):
        """Epoch timestamps in milliseconds should convert correctly."""
        sensor = _make_alarm_sensor()

        epoch_ms = 1717228800000  # 2024-06-01 08:00:00 UTC

        result = sensor._coerce_datetime(epoch_ms)

        expected = datetime.datetime.fromtimestamp(epoch_ms / 1000, tz=self.UTC)

        assert result == expected
        assert result.tzinfo == self.UTC

    def test_iso_datetime_string_parsed_correctly(self):
        """ISO datetime strings should parse into aware datetimes."""
        sensor = _make_alarm_sensor()

        result = sensor._coerce_datetime("2024-06-01T08:00:00+00:00")

        expected = datetime.datetime(2024, 6, 1, 8, 0, tzinfo=self.UTC)

        assert result == expected

    def test_none_returns_none(self):
        """None should short-circuit to None."""
        sensor = _make_alarm_sensor()

        assert sensor._coerce_datetime(None) is None

    def test_empty_string_returns_none(self):
        """Empty string should short-circuit to None."""
        sensor = _make_alarm_sensor()

        assert sensor._coerce_datetime("") is None

    def test_naive_datetime_made_aware_using_sensor_timezone(self):
        """Naive datetimes should be localized using sensor timezone."""
        sensor = _make_alarm_sensor()

        naive = datetime.datetime(2024, 6, 1, 8, 0)

        result = sensor._coerce_datetime(naive)

        expected = naive.replace(tzinfo=self.UTC)

        assert result == expected
        assert result.tzinfo == self.UTC


class TestNormalizeAlarmSnoozeState:
    """Unit tests for _normalize_alarm_snooze_state."""

    NOW = datetime.datetime(2024, 6, 1, 8, 0, 0, tzinfo=UTC)

    # --- State 1: ON ---

    def test_on_alarm_passes_through_unchanged(self):
        """ON alarm with no snoozedToTime must not be modified."""
        sensor = _make_alarm_sensor()
        alarm_at = self.NOW + datetime.timedelta(hours=1)
        value = _alarm_value("ON", alarm_at, snoozed_to=None)

        with patch(
            "custom_components.alexa_media.sensor.dt.now", return_value=self.NOW
        ):
            result = sensor._normalize_alarm_snooze_state(value)

        assert result[1]["status"] == "ON"
        assert result[1]["date_time"] == alarm_at
        assert result[1]["snoozedToTime"] is None

    # --- State 2: SNOOZED with future snoozedToTime ---

    def test_future_snoozed_to_time_sets_status_and_updates_timestamp(self):
        """When snoozedToTime is in the future, status must become SNOOZED
        and date_time must be updated to the snooze time."""
        sensor = _make_alarm_sensor()
        original_alarm = self.NOW - datetime.timedelta(minutes=5)  # already rang
        snooze_until = self.NOW + datetime.timedelta(minutes=9)  # snooze active
        value = _alarm_value("ON", original_alarm, snoozed_to=snooze_until)

        with patch(
            "custom_components.alexa_media.sensor.dt.now", return_value=self.NOW
        ):
            result = sensor._normalize_alarm_snooze_state(value)

        assert result[1]["status"] == "SNOOZED"
        assert result[1]["date_time"] == snooze_until
        assert result[1]["snoozedToTime"] == snooze_until

    def test_future_snoozed_to_time_overrides_existing_snoozed_status(self):
        """Future snoozedToTime normalizes regardless of original status value."""
        sensor = _make_alarm_sensor()
        snooze_until = self.NOW + datetime.timedelta(minutes=3)
        value = _alarm_value(
            "SNOOZED", self.NOW - datetime.timedelta(hours=1), snoozed_to=snooze_until
        )

        with patch(
            "custom_components.alexa_media.sensor.dt.now", return_value=self.NOW
        ):
            result = sensor._normalize_alarm_snooze_state(value)

        assert result[1]["status"] == "SNOOZED"
        assert result[1]["date_time"] == snooze_until
        assert result[1]["snoozedToTime"] == snooze_until

    # --- State 3: SNOOZED with missing snoozedToTime ---

    def test_snoozed_missing_snooze_time_backfills_from_alarm_time(self):
        """SNOOZED alarm whose snoozedToTime is None must have snoozedToTime
        backfilled from date_time."""
        sensor = _make_alarm_sensor()
        alarm_at = self.NOW + datetime.timedelta(minutes=5)
        value = _alarm_value("SNOOZED", alarm_at, snoozed_to=None)

        with patch(
            "custom_components.alexa_media.sensor.dt.now", return_value=self.NOW
        ):
            result = sensor._normalize_alarm_snooze_state(value)

        assert result[1]["status"] == "SNOOZED"
        assert result[1]["snoozedToTime"] == alarm_at
        assert result[1]["date_time"] == alarm_at

    # --- State 4: expired SNOOZED ---

    def test_expired_snoozed_left_unchanged_by_normalize(self):
        """SNOOZED alarm whose snoozedToTime is in the past must not be modified
        by normalization (exclusion is handled downstream by the active filter)."""
        sensor = _make_alarm_sensor()
        expired_snooze = self.NOW - datetime.timedelta(minutes=5)
        original_alarm = self.NOW - datetime.timedelta(hours=1)
        value = _alarm_value("SNOOZED", original_alarm, snoozed_to=expired_snooze)

        with patch(
            "custom_components.alexa_media.sensor.dt.now", return_value=self.NOW
        ):
            result = sensor._normalize_alarm_snooze_state(value)

        # normalize does not touch expired snooze; filtering is done elsewhere
        assert result[1]["status"] == "SNOOZED"
        assert result[1]["snoozedToTime"] == expired_snooze
        assert result[1]["date_time"] == original_alarm

    # --- Non-Alarm type guard ---

    def test_non_alarm_type_skipped(self):
        """Non-Alarm sensors must be returned unchanged regardless of payload."""
        sensor = _make_alarm_sensor()
        sensor._type = "Reminder"
        alarm_at = self.NOW + datetime.timedelta(hours=1)
        value = _alarm_value("SNOOZED", alarm_at)

        with patch(
            "custom_components.alexa_media.sensor.dt.now", return_value=self.NOW
        ):
            result = sensor._normalize_alarm_snooze_state(value)

        assert result is value  # exact same object, no copy


# ---------------------------------------------------------------------------
# 2. Active-notification filter
# ---------------------------------------------------------------------------


class TestIsActiveNotification:
    """Unit tests for _is_active_notification."""

    NOW = datetime.datetime(2024, 6, 1, 8, 0, 0, tzinfo=UTC)

    # --- State 1: ON ---

    def test_on_alarm_is_active(self):
        """ON alarm must always be considered active."""
        sensor = _make_alarm_sensor()
        item = _alarm_value("ON", self.NOW + datetime.timedelta(hours=1))
        assert sensor._is_active_notification(item, self.NOW) is True

    def test_on_alarm_is_active_even_if_in_past(self):
        """ON alarm is active regardless of whether date_time is past."""
        sensor = _make_alarm_sensor()
        item = _alarm_value("ON", self.NOW - datetime.timedelta(hours=2))
        assert sensor._is_active_notification(item, self.NOW) is True

    # --- State 2: SNOOZED with future snoozedToTime ---

    def test_snoozed_future_snooze_time_is_active(self):
        """SNOOZED alarm whose snoozedToTime is still in the future must be active."""
        sensor = _make_alarm_sensor()
        snooze_until = self.NOW + datetime.timedelta(minutes=9)
        item = _alarm_value("SNOOZED", self.NOW, snoozed_to=snooze_until)
        assert sensor._is_active_notification(item, self.NOW) is True

    # --- State 3: SNOOZED with missing snoozedToTime ---

    def test_snoozed_none_snooze_time_treated_as_active(self):
        """SNOOZED alarm with snoozedToTime=None is treated as active (fail-open)."""
        sensor = _make_alarm_sensor()
        item = _alarm_value(
            "SNOOZED", self.NOW + datetime.timedelta(hours=1), snoozed_to=None
        )
        assert sensor._is_active_notification(item, self.NOW) is True

    # --- State 4: expired SNOOZED ---

    def test_expired_snoozed_is_not_active(self):
        """SNOOZED alarm whose snoozedToTime is in the past must be excluded."""
        sensor = _make_alarm_sensor()
        expired_snooze = self.NOW - datetime.timedelta(minutes=5)
        item = _alarm_value(
            "SNOOZED", self.NOW - datetime.timedelta(hours=1), snoozed_to=expired_snooze
        )
        assert sensor._is_active_notification(item, self.NOW) is False

    def test_expired_snooze_at_exact_boundary_is_not_active(self):
        """snoozedToTime == now (not strictly greater) is treated as expired."""
        sensor = _make_alarm_sensor()
        item = _alarm_value("SNOOZED", self.NOW, snoozed_to=self.NOW)
        assert sensor._is_active_notification(item, self.NOW) is False

    # --- Unrelated statuses ---

    def test_off_alarm_is_not_active(self):
        """OFF alarm must never be active."""
        sensor = _make_alarm_sensor()
        item = _alarm_value("OFF", self.NOW + datetime.timedelta(hours=1))
        assert sensor._is_active_notification(item, self.NOW) is False
