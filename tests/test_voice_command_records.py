"""Tests for _collect_new_voice_records in custom_components.alexa_media."""

from custom_components.alexa_media import _collect_new_voice_records

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
