"""Pytest cases for Alexa alarm snooze handling.

Covers _normalize_alarm_snooze_state and _is_active_notification for
current Alexa payloads where SNOOZED alarms may have missing or expired
snoozedToTime values. SNOOZED status is treated as authoritative so the
sensor does not drop to unknown/off while an alarm is snoozed.
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
# 1. _coerce_datetime
# ---------------------------------------------------------------------------


class TestCoerceDatetime:
    """Unit tests for _coerce_datetime."""

    def test_aware_datetime_passes_through_unchanged(self):
        """Aware datetimes should be returned unchanged."""
        sensor = _make_alarm_sensor()
        aware = datetime.datetime(2024, 6, 1, 8, 0, tzinfo=UTC)

        result = sensor._coerce_datetime(aware)

        assert result is aware

    def test_epoch_seconds_converted_correctly(self):
        """Epoch timestamps in seconds should convert correctly."""
        sensor = _make_alarm_sensor()
        epoch_seconds = 1717228800  # 2024-06-01 08:00:00 UTC

        result = sensor._coerce_datetime(epoch_seconds)

        expected = datetime.datetime.fromtimestamp(epoch_seconds, tz=UTC)
        assert result == expected
        assert result.tzinfo is not None
        assert result.utcoffset() is not None

    def test_epoch_milliseconds_converted_correctly(self):
        """Epoch timestamps in milliseconds should convert correctly."""
        sensor = _make_alarm_sensor()
        epoch_ms = 1717228800000  # 2024-06-01 08:00:00 UTC

        result = sensor._coerce_datetime(epoch_ms)

        expected = datetime.datetime.fromtimestamp(epoch_ms / 1000, tz=UTC)
        assert result == expected
        assert result.tzinfo is not None

    def test_iso_datetime_string_parsed_correctly(self):
        """ISO datetime strings should parse into aware datetimes."""
        sensor = _make_alarm_sensor()

        result = sensor._coerce_datetime("2024-06-01T08:00:00+00:00")

        expected = datetime.datetime(2024, 6, 1, 8, 0, tzinfo=UTC)
        assert result == expected

    def test_none_returns_none(self):
        """None should short-circuit to None."""
        sensor = _make_alarm_sensor()

        assert sensor._coerce_datetime(None) is None

    def test_empty_string_returns_none(self):
        """Empty string should short-circuit to None."""
        sensor = _make_alarm_sensor()

        assert sensor._coerce_datetime("") is None

    def test_naive_datetime_made_aware_using_sensor_timezone(self, monkeypatch):
        """Naive datetimes should be localized using sensor timezone."""
        sensor = _make_alarm_sensor()
        monkeypatch.setattr(
            "custom_components.alexa_media.sensor.dt.get_time_zone",
            lambda _: UTC,
        )
        naive = datetime.datetime(2024, 6, 1, 8, 0)

        result = sensor._coerce_datetime(naive)

        expected = naive.replace(tzinfo=UTC)
        assert result == expected
        assert result.tzinfo is not None
        assert result.utcoffset() is not None


# ---------------------------------------------------------------------------
# 2. _normalize_alarm_snooze_state
# ---------------------------------------------------------------------------


class TestNormalizeAlarmSnoozeState:
    """Unit tests for _normalize_alarm_snooze_state."""

    NOW = datetime.datetime(2024, 6, 1, 8, 0, 0, tzinfo=UTC)

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

    def test_on_alarm_with_snoozed_to_time_passes_through_unchanged(self):
        """Normalization must not invent SNOOZED status for an ON alarm."""
        sensor = _make_alarm_sensor()
        alarm_at = self.NOW - datetime.timedelta(minutes=5)
        snooze_until = self.NOW + datetime.timedelta(minutes=9)
        value = _alarm_value("ON", alarm_at, snoozed_to=snooze_until)

        with patch(
            "custom_components.alexa_media.sensor.dt.now", return_value=self.NOW
        ):
            result = sensor._normalize_alarm_snooze_state(value)

        assert result[1]["status"] == "ON"
        assert result[1]["date_time"] == alarm_at
        assert result[1]["snoozedToTime"] == snooze_until

    def test_snoozed_future_snoozed_to_time_updates_timestamp(self):
        """Future snoozedToTime should be used as the displayed snoozed time."""
        sensor = _make_alarm_sensor()
        original_alarm = self.NOW - datetime.timedelta(minutes=5)
        snooze_until = self.NOW + datetime.timedelta(minutes=9)
        value = _alarm_value("SNOOZED", original_alarm, snoozed_to=snooze_until)

        with patch(
            "custom_components.alexa_media.sensor.dt.now", return_value=self.NOW
        ):
            result = sensor._normalize_alarm_snooze_state(value)

        assert result[1]["status"] == "SNOOZED"
        assert result[1]["date_time"] == snooze_until
        assert result[1]["snoozedToTime"] == snooze_until

    def test_snoozed_missing_snooze_time_is_preserved(self):
        """SNOOZED alarm with missing snoozedToTime must stay snoozed.

        Amazon may omit the real snooze expiry. Normalization should not
        backfill snoozedToTime from date_time because that value can be the
        original alarm time, not the next snooze fire time.
        """
        sensor = _make_alarm_sensor()
        alarm_at = self.NOW + datetime.timedelta(minutes=5)
        value = _alarm_value("SNOOZED", alarm_at, snoozed_to=None)

        with patch(
            "custom_components.alexa_media.sensor.dt.now", return_value=self.NOW
        ):
            result = sensor._normalize_alarm_snooze_state(value)

        assert result[1]["status"] == "SNOOZED"
        assert result[1]["snoozedToTime"] is None
        assert result[1]["date_time"] == alarm_at

    def test_expired_snoozed_clears_unusable_snooze_time(self):
        """Expired snoozedToTime should be cleared, not used for filtering.

        Current Alexa payloads can report stale snooze times. The alarm status
        remains SNOOZED, while the unusable snoozedToTime is set to None so
        status remains the source of truth.
        """
        sensor = _make_alarm_sensor()
        expired_snooze = self.NOW - datetime.timedelta(minutes=5)
        original_alarm = self.NOW - datetime.timedelta(hours=1)
        value = _alarm_value("SNOOZED", original_alarm, snoozed_to=expired_snooze)

        with patch(
            "custom_components.alexa_media.sensor.dt.now", return_value=self.NOW
        ):
            result = sensor._normalize_alarm_snooze_state(value)

        assert result[1]["status"] == "SNOOZED"
        assert result[1]["snoozedToTime"] is None
        assert result[1]["date_time"] == original_alarm

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

        assert result is value


# ---------------------------------------------------------------------------
# 3. Active-notification filter
# ---------------------------------------------------------------------------


class TestIsActiveNotification:
    """Unit tests for _is_active_notification."""

    NOW = datetime.datetime(2024, 6, 1, 8, 0, 0, tzinfo=UTC)

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

    def test_snoozed_future_snooze_time_is_active(self):
        """SNOOZED alarm whose snoozedToTime is in the future must be active."""
        sensor = _make_alarm_sensor()
        snooze_until = self.NOW + datetime.timedelta(minutes=9)
        item = _alarm_value("SNOOZED", self.NOW, snoozed_to=snooze_until)

        assert sensor._is_active_notification(item, self.NOW) is True

    def test_snoozed_none_snooze_time_treated_as_active(self):
        """SNOOZED alarm with snoozedToTime=None is treated as active."""
        sensor = _make_alarm_sensor()
        item = _alarm_value(
            "SNOOZED", self.NOW + datetime.timedelta(hours=1), snoozed_to=None
        )

        assert sensor._is_active_notification(item, self.NOW) is True

    def test_expired_snoozed_is_active(self):
        """SNOOZED alarm with expired snoozedToTime remains active.

        Amazon may return stale snooze timestamps during repeated tap snoozes,
        so SNOOZED status is treated as authoritative.
        """
        sensor = _make_alarm_sensor()
        expired_snooze = self.NOW - datetime.timedelta(minutes=5)
        item = _alarm_value(
            "SNOOZED", self.NOW - datetime.timedelta(hours=1), snoozed_to=expired_snooze
        )

        assert sensor._is_active_notification(item, self.NOW) is True

    def test_expired_snooze_at_exact_boundary_is_active(self):
        """snoozedToTime == now is still active when status is SNOOZED."""
        sensor = _make_alarm_sensor()
        item = _alarm_value("SNOOZED", self.NOW, snoozed_to=self.NOW)

        assert sensor._is_active_notification(item, self.NOW) is True

    def test_off_alarm_is_not_active(self):
        """OFF alarm must never be active."""
        sensor = _make_alarm_sensor()
        item = _alarm_value("OFF", self.NOW + datetime.timedelta(hours=1))

        assert sensor._is_active_notification(item, self.NOW) is False
