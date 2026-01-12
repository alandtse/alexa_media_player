"""Tests for diagnostics.py (collection, redaction, obfuscation, and coordinator discovery)."""

from __future__ import annotations

from datetime import timedelta
import logging
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
import pytest

from custom_components.alexa_media.const import DOMAIN, TO_REDACT
from custom_components.alexa_media.diagnostics import (
    _find_coordinators,
    _maybe_keys,
    _obfuscate_identifier,
    _obfuscate_title_with_email,
    _summarize_amp_entry_runtime,
    _summarize_coordinator,
    async_get_config_entry_diagnostics,
    async_get_device_diagnostics,
)


@pytest.fixture
def mock_hass():
    """Create a minimal hass-like object for unit tests."""
    hass = MagicMock()
    hass.data = {}
    return hass


@pytest.mark.parametrize(
    ("val", "expected"),
    [
        (None, "****"),
        ("", "****"),
        ("abc", "****"),
        ("abcd", "****"),
        ("abcde", "ab...de"),
        (12345, "****"),
    ],
)
def test_obfuscate_identifier(val, expected):
    assert _obfuscate_identifier(val) == expected


def test_obfuscate_title_with_email_uses_hide_email_when_available(monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "alexapy",
        SimpleNamespace(hide_email=lambda _s: "h***@example.com"),
    )

    title = "Alexa Media Player (daniel@example.com)"
    assert _obfuscate_title_with_email(title, "daniel@example.com") == (
        "Alexa Media Player (h***@example.com)"
    )


def test_obfuscate_title_with_email_falls_back_when_import_fails(monkeypatch):
    monkeypatch.delitem(sys.modules, "alexapy", raising=False)

    title = "Alexa Media Player (daniel@example.com)"
    out = _obfuscate_title_with_email(title, "daniel@example.com")

    assert out is not None
    assert "daniel@example.com" not in out
    assert "****" in out or "da...om" in out


def test_maybe_keys_non_mapping_returns_none():
    assert _maybe_keys(["not", "a", "mapping"]) is None
    assert _maybe_keys("nope") is None


def test_maybe_keys_sanitizes_email_keys_and_limits(monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "alexapy",
        SimpleNamespace(hide_email=lambda _s: "h***@example.com"),
    )

    val = {
        "daniel@example.com": 1,
        "some_token_value_abcdef": 2,
        "ok": 3,
    }

    keys = _maybe_keys(val, limit=2)
    assert keys is not None
    assert len(keys) == 2
    assert all("daniel@example.com" not in k for k in keys)


def test_find_coordinators_finds_nested_coordinator(mock_hass):
    coordinator = DataUpdateCoordinator(
        mock_hass,
        logger=logging.getLogger(__name__),
        name="test",
        update_interval=timedelta(seconds=30),
    )

    tree = {"a": [{"b": coordinator}], "c": {"d": "nope"}}
    found = _find_coordinators(tree)

    assert coordinator in found
    assert len(found) == 1


def test_summarize_coordinator_error_handling(mock_hass):
    coordinator = DataUpdateCoordinator(
        mock_hass,
        logger=logging.getLogger(__name__),
        name="test",
        update_interval=timedelta(seconds=30),
    )

    with patch(
        "custom_components.alexa_media.diagnostics._summarize_coordinator_data",
        side_effect=RuntimeError("boom"),
    ):
        summary = _summarize_coordinator(coordinator)

    assert summary["data_summary_error"] == "RuntimeError"
    assert summary["data_summary_error_present"] is True


def test_summarize_amp_entry_runtime_mapping(monkeypatch):
    monkeypatch.setattr(
        "custom_components.alexa_media.diagnostics._maybe_keys",
        lambda v, limit=50: ["aa...zz"],
    )

    entry_runtime = {"devices": [1, 2, 3]}
    out = _summarize_amp_entry_runtime(entry_runtime)

    assert out["present"] is True
    assert out["runtime_type"] == "mapping"
    assert out["runtime_keys"] == ["aa...zz"]


@pytest.mark.asyncio
async def test_async_get_config_entry_diagnostics_redacts_sensitive_fields(
    mock_hass, monkeypatch
):
    assert TO_REDACT, "TO_REDACT must be non-empty"


@pytest.mark.asyncio
async def test_async_get_config_entry_diagnostics_redacts_sensitive_fields(
    mock_hass, monkeypatch
):
    redact_key = next(iter(TO_REDACT))
    secret_value = "supersecret123"  # nosec B105

    entry = SimpleNamespace(
        entry_id="entry123",
        title="Alexa Media Player (daniel@example.com)",
        domain=DOMAIN,
        version=1,
        minor_version=0,
        data={"email": "daniel@example.com", redact_key: secret_value},
        options={redact_key: secret_value},
    )

    mock_hass.data.setdefault(DOMAIN, {})
    monkeypatch.setattr(
        "custom_components.alexa_media.diagnostics._get_safe_config_entry_title",
        lambda _entry: "Alexa Media Player (h***@example.com)",
    )

    out = await async_get_config_entry_diagnostics(mock_hass, entry)

    assert out["data"].get(redact_key) != secret_value
    assert out["options"].get(redact_key) != secret_value
    title = out["entry"]["title"]
    assert isinstance(title, str) or title is None
    if title:
        assert "daniel@example.com" not in title


@pytest.mark.asyncio
async def test_async_get_device_diagnostics_obfuscates_ids_and_serial(
    monkeypatch, mock_hass
):
    monkeypatch.setitem(
        sys.modules, "alexapy", SimpleNamespace(hide_serial=lambda _s: "12...90")
    )

    entry = SimpleNamespace(
        entry_id="entry123",
        title="Alexa Media Player (daniel@example.com)",
        domain=DOMAIN,
        version=1,
        minor_version=0,
        data={"email": "daniel@example.com"},
        options={},
    )

    device = SimpleNamespace(
        id="device_id_ABCDEFGH",
        name="Kitchen Echo",
        name_by_user="Kitchen",
        manufacturer="Amazon",
        model="Echo",
        sw_version="1.0",
        serial_number="G090X01234567890",
        identifiers={("alexa_media", "identifier_ABCDEFGH")},
        via_device_id="via_id_ABCDEFGH",
    )

    out = await async_get_device_diagnostics(mock_hass, entry, device)

    assert out["device"]["id"] != "device_id_ABCDEFGH"
    assert out["device"]["via_device_id"] != "via_id_ABCDEFGH"
    assert out["device"]["serial_number"] != "G090X01234567890"


@pytest.mark.asyncio
async def test_async_get_config_entry_diagnostics_domain_data_not_mapping_is_robust(
    mock_hass, monkeypatch
):
    monkeypatch.setattr(
        "custom_components.alexa_media.diagnostics._summarize_amp_entry_runtime",
        lambda v: {"present": v is not None},
    )
    monkeypatch.setattr(
        "custom_components.alexa_media.diagnostics._summarize_amp_domain",
        lambda domain_data, entry: {"present": domain_data is not None},
    )

    entry = SimpleNamespace(
        entry_id="entry123",
        title="Alexa Media Player (daniel@example.com)",
        domain=DOMAIN,
        version=1,
        minor_version=0,
        data={},
        options={},
    )

    mock_hass.data[DOMAIN] = "not-a-mapping"

    out = await async_get_config_entry_diagnostics(mock_hass, entry)

    assert out["account"]["searched_for_coordinators_in"] == []
    assert out["account"]["coordinator_count"] == 0
    assert out["account"]["coordinators"] == []
