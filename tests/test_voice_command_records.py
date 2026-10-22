"""Tests for the alexa_media_voice_command record helpers."""

from custom_components.alexa_media import (
    _collect_new_voice_records,
    _take_new_voice_records,
)
from custom_components.alexa_media.const import LAST_CALLED_STALE_FUDGE_MS as FUDGE

SERIALS = {"ECHO_A", "ECHO_B"}


def _record(serial, ts, summary, response=None, utterance_type="GENERAL"):
    return {
        "deviceSerialNumber": serial,
        "creationTimestamp": ts,
        "description": {"summary": summary},
        "alexaResponse": response,
        "utteranceType": utterance_type,
    }


def test_burst_on_one_device_returns_every_record_oldest_first():
    """Rapid commands on one device are all returned, in spoken order."""
    records = [
        _record("ECHO_A", 4000, "add butter", "Added butter."),
        _record("ECHO_A", 3000, "add bread"),
        _record("ECHO_A", 2000, "add eggs"),
        _record("ECHO_A", 1000, "add milk"),
    ]

    result = _collect_new_voice_records(records, 0, 4000, SERIALS)

    assert [r["summary"] for r in result] == [
        "add milk",
        "add eggs",
        "add bread",
        "add butter",
    ]
    assert result[-1] == {
        "serial": "ECHO_A",
        "timestamp": 4000,
        "summary": "add butter",
        "response": "Added butter.",
    }
    assert result[0]["response"] is None


def test_window_is_exclusive_below_and_inclusive_above():
    """Records at the watermark were already reported; newer ones wait."""
    records = [
        _record("ECHO_A", 1000, "already reported"),
        _record("ECHO_A", 2000, "new one"),
        _record("ECHO_A", 3000, "selected payload"),
        _record("ECHO_A", 4000, "newer than payload"),
    ]

    result = _collect_new_voice_records(records, 1000, 3000, SERIALS)

    assert [r["timestamp"] for r in result] == [2000, 3000]


def test_invalid_records_are_skipped():
    """Unknown devices, filtered utterance types and junk are ignored."""
    records = [
        "not a dict",
        _record("UNKNOWN", 1100, "other account device"),
        _record(None, 1200, "no serial"),
        _record("ECHO_A", 1300, "", utterance_type="WAKE_WORD_ONLY"),
        _record("ECHO_A", 1400, "arbitrated", utterance_type="DEVICE_ARBITRATION"),
        _record("ECHO_A", 1500, "   "),
        _record("ECHO_A", 1600, "?!"),
        _record("ECHO_A", "garbage", "bad timestamp"),
        _record("ECHO_B", 1700, "  turn on the light  "),
        {"deviceSerialNumber": "ECHO_A", "creationTimestamp": 1800},
    ]

    result = _collect_new_voice_records(records, 0, 2000, SERIALS)

    assert result == [
        {
            "serial": "ECHO_B",
            "timestamp": 1700,
            "summary": "turn on the light",
            "response": None,
        }
    ]


def test_other_device_newer_than_upper_bound_is_left_for_later():
    """A newer record on another device waits for the next probe."""
    records = [
        _record("ECHO_A", 2000, "selected payload"),
        _record("ECHO_B", 2500, "spoken just after"),
    ]

    result = _collect_new_voice_records(records, 0, 2000, SERIALS)

    assert [r["serial"] for r in result] == ["ECHO_A"]


def test_string_timestamp_and_non_string_fields():
    """String timestamps parse; odd description/response shapes don't raise."""
    records = [
        _record("ECHO_A", "2000", "string timestamp", response=42),
        {
            "deviceSerialNumber": "ECHO_A",
            "creationTimestamp": 2100,
            "description": "not a dict",
        },
        {
            "deviceSerialNumber": "ECHO_A",
            "creationTimestamp": 2200,
            "description": {"summary": ["not", "a", "string"]},
        },
    ]

    result = _collect_new_voice_records(records, 0, 3000, SERIALS)

    assert result == [
        {
            "serial": "ECHO_A",
            "timestamp": 2000,
            "summary": "string timestamp",
            "response": "42",
        }
    ]


def test_empty_or_missing_records():
    """None and empty inputs yield nothing."""
    assert _collect_new_voice_records(None, 0, 1000, SERIALS) == []
    assert _collect_new_voice_records([], 0, 1000, SERIALS) == []


def _take(account, records, upper_ts, earliest_ts=0):
    return [
        r["summary"]
        for r in _take_new_voice_records(
            account, records, upper_ts, earliest_ts, SERIALS
        )
    ]


def _emit(account, records, payload_ts, earliest_ts=0):
    """Mimic the probe worker: take records, then advance the watermark."""
    taken = _take(account, records, payload_ts, earliest_ts)
    account["last_called_customer_history_ts"] = max(
        account.get("last_called_customer_history_ts", 0), payload_ts
    )
    return taken


def test_take_does_not_replay_history_before_startup_watermark():
    """The startup watermark is a hard floor, now and on later probes."""
    account = {"last_called_customer_history_ts": 100_000}
    before = _record("ECHO_A", 99_000, "before startup")
    startup = _record("ECHO_A", 100_000, "startup last_called")

    assert _emit(
        account, [before, startup, _record("ECHO_A", 102_000, "a")], 102_000
    ) == ["a"]
    assert _emit(
        account, [before, startup, _record("ECHO_A", 103_000, "b")], 103_000
    ) == ["b"]


def test_take_emits_late_record_below_watermark_exactly_once():
    """A record that shows up after a newer one still fires, but only once."""
    account = {"last_called_customer_history_ts": 100_000}
    newer = _record("ECHO_B", 110_000, "newer")
    late = _record("ECHO_A", 108_000, "late")
    next_cmd = _record("ECHO_B", 111_000, "next")
    last_cmd = _record("ECHO_B", 112_000, "last")

    assert _emit(account, [newer], 110_000) == ["newer"]
    assert _emit(account, [newer, late, next_cmd], 111_000) == ["late", "next"]
    assert _emit(account, [newer, late, next_cmd, last_cmd], 112_000) == ["last"]


def test_take_drops_records_older_than_the_overlap():
    """Records further back than the overlap are not replayed or kept."""
    account = {"last_called_customer_history_ts": 100_000}
    assert _emit(account, [_record("ECHO_A", 110_000, "a")], 110_000) == ["a"]
    too_old = _record("ECHO_A", 110_000 - FUDGE, "too old")

    assert _emit(account, [too_old, _record("ECHO_A", 111_000, "b")], 111_000) == ["b"]
    assert _emit(account, [_record("ECHO_A", 120_000, "c")], 120_000) == ["c"]
    assert _emit(account, [], 130_000) == []
    assert account["last_called_voice_emitted"] == {("ECHO_A", 120_000)}


def test_take_does_not_replay_records_of_a_refresh_without_events():
    """A watermark moved by a refresh path is not overlapped later."""
    account = {"last_called_customer_history_ts": 100_000}
    assert _emit(account, [_record("ECHO_A", 102_000, "a")], 102_000) == ["a"]
    # POLL_REFRESH / fallback: update_last_called without any event.
    account["last_called_customer_history_ts"] = 600_000
    polled = [
        _record("ECHO_A", 598_000, "before polled"),
        _record("ECHO_A", 600_000, "polled"),
    ]

    assert _emit(
        account, [*polled, _record("ECHO_A", 1_200_000, "new")], 1_200_000
    ) == ["new"]


def test_take_without_watermark_bounds_by_queue_or_payload():
    """No watermark yet: bound by the queued burst, else by the payload."""
    records = [
        _record("ECHO_A", 50_000, "old history"),
        _record("ECHO_A", 87_000, "queued burst start"),
        _record("ECHO_A", 98_000, "milk"),
        _record("ECHO_A", 100_000, "eggs"),
    ]

    assert _take({}, records, 100_000, earliest_ts=90_000) == [
        "queued burst start",
        "milk",
        "eggs",
    ]
    assert _take({}, records, 100_000) == ["milk", "eggs"]
