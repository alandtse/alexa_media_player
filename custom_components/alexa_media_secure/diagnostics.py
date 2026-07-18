"""Diagnostics support for Alexa Media Player."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from datetime import datetime
from itertools import islice
import re
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.redact import async_redact_data
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    COMMON_BUCKET_COUNTS,
    COMMON_DIAGNOSTIC_BUCKETS,
    COMMON_DIAGNOSTIC_NAMES,
    DEVICE_PLAYER_BUCKETS,
    DOMAIN,
    TO_REDACT,
)


# --------------------
# Local Functions
# --------------------
def _safe_dt(val: Any) -> str | None:
    """Serialize datetimes safely for JSON diagnostics."""
    if isinstance(val, datetime):
        return val.isoformat()
    return None


def _maybe_len(val: Any) -> int | None:
    """Return the length of common container types or None if not applicable."""
    if isinstance(val, (list, tuple, dict, set)):
        return len(val)
    return None


def _maybe_keys(val: Any, limit: int = 50) -> list[str] | None:
    """Return a sanitized sample of mapping keys for diagnostics.

    If ``val`` is a mapping, return up to ``limit`` obfuscated keys to provide
    structural insight without exposing sensitive data. Email-like keys are
    redacted when possible; otherwise keys are shortened to a non-identifying
    form. Returns ``None`` if ``val`` is not a mapping or keys cannot be read.
    """

    if isinstance(val, Mapping):
        try:
            # Sample up to `limit` keys to keep diagnostics small.
            def _safe_key(k: Any) -> str:
                s = str(k)
                # Emails/titles/tokens sometimes appear as keys in AMP structures.
                if re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", s):
                    try:
                        from alexapy import (  # pylint: disable=import-outside-toplevel
                            hide_email,
                        )

                        return hide_email(s)
                    except (ImportError, AttributeError, TypeError, ValueError):
                        pass
                return _obfuscate_identifier(s)

            return sorted(_safe_key(k) for k in islice(val.keys(), limit))
        except (TypeError, AttributeError):
            return None
    return None


def _sample_names(val: Any, *, limit: int = 5) -> list[str] | None:
    """Try to sample human-friendly names from a list/dict of device-like objects."""
    names: list[str] = []

    def add_name(x: Any) -> None:
        if isinstance(x, Mapping):
            for key in COMMON_DIAGNOSTIC_NAMES:
                v = x.get(key)
                if isinstance(v, str) and v:
                    names.append(v)
                    return
        v = getattr(x, "name", None)
        if isinstance(v, str) and v:
            names.append(v)

    if isinstance(val, Mapping):
        for v in islice(val.values(), limit * 2):
            add_name(v)
            if len(names) >= limit:
                break
        return names[:limit] if names else None

    if isinstance(val, (list, tuple)):
        for v in val[: limit * 2]:
            add_name(v)
            if len(names) >= limit:
                break
        return names[:limit] if names else None

    return None


# --------------------
# Coordinator discovery + summary
# --------------------
def _find_coordinators(obj: Any) -> list[DataUpdateCoordinator]:
    """Recursively find DataUpdateCoordinator instances in an object tree."""
    found: list[DataUpdateCoordinator] = []
    visited: set[int] = set()

    def walk(x: Any) -> None:
        obj_id = id(x)
        if obj_id in visited:
            return
        visited.add(obj_id)

        if isinstance(x, DataUpdateCoordinator):
            found.append(x)
            return
        if is_dataclass(x):
            try:
                # Walk dataclass attributes directly; asdict() can lose/mangle objects.
                for f in fields(x):
                    try:
                        walk(getattr(x, f.name))
                    except (AttributeError, TypeError, ValueError):
                        # Skip fields that can't be read safely
                        pass
            except (TypeError, ValueError):
                # Fallback: vars() can work for some dataclass/slots variations
                try:
                    for v in vars(x).values():
                        walk(v)
                except (AttributeError, TypeError, ValueError):
                    # Ignore attributes that cannot be introspected via vars()
                    pass
            return
        if isinstance(x, Mapping):
            for v in x.values():
                walk(v)
            return
        if isinstance(x, (list, tuple, set)):
            for v in x:
                walk(v)
            return
        # Ignore everything else.

    walk(obj)
    return found


def _summarize_coordinator_data(cdata: Any) -> dict:
    """
    Allowlisted summary of coordinator.data.

    Never dump raw coordinator data. Only return counts + small samples.
    Optimized for AMP: coordinator.data is often a mapping keyed by UUIDs.
    """
    out: dict[str, Any] = {}

    if isinstance(cdata, Mapping):
        out["data_key_count"] = len(cdata)

        key_sample = list(islice(cdata.keys(), 10))

        out["data_key_types_sample"] = [type(k).__name__ for k in key_sample]

        sample_vals = [type(cdata.get(k)).__name__ for k in key_sample[:3]]
        if sample_vals:
            out["data_value_types_sample"] = sample_vals

        # If coordinator.data sometimes contains named buckets (future-proof),
        # include just counts (but only if those keys actually exist).
        for key in COMMON_DIAGNOSTIC_BUCKETS:
            if key in cdata:
                out[f"{key}_count"] = _maybe_len(cdata.get(key))

        # If AMP ever exposes last_called through coordinator.data, include only safe fields.
        last_called = cdata.get("last_called")
        if isinstance(last_called, Mapping):
            ts = last_called.get("timestamp")
            out["last_called"] = {
                "timestamp": _safe_dt(ts) or ts,
                "summary": last_called.get("summary"),
            }

        # If there are device/player buckets, sample friendly names (no IDs).
        for key in DEVICE_PLAYER_BUCKETS:
            if key in cdata:
                sample = _sample_names(cdata.get(key))
                if sample:
                    out[f"{key}_sample_names"] = sample
                break

        return out

    if isinstance(cdata, (list, tuple)):
        out["data_len"] = len(cdata)
        sample = _sample_names(cdata)
        if sample:
            out["sample_names"] = sample
        return out

    if cdata is not None:
        out["data_type"] = type(cdata).__name__
    return out


def _summarize_coordinator(coordinator: DataUpdateCoordinator) -> dict:
    """Return a safe, compact view of a coordinator."""
    exc = getattr(coordinator, "last_exception", None)

    data = {
        "name": getattr(coordinator, "name", None),
        "last_update_success": getattr(coordinator, "last_update_success", None),
        "has_exception": exc is not None,
        "last_exception_type": type(exc).__name__ if exc else None,
        "update_interval": (
            str(getattr(coordinator, "update_interval", None))
            if getattr(coordinator, "update_interval", None) is not None
            else None
        ),
        "last_update": _safe_dt(getattr(coordinator, "last_update", None)),
    }

    try:
        data["data_summary"] = _summarize_coordinator_data(
            getattr(coordinator, "data", None)
        )
    except (
        Exception
    ) as exc:  # noqa: BLE001 - intentionally broad; diagnostics must not crash
        data["data_summary_error"] = type(exc).__name__
        data["data_summary_error_present"] = True

    return data


# --------------------
# AMP-specific (non-coordinator) runtime summaries
# --------------------
def _summarize_amp_entry_runtime(entry_runtime: Any) -> dict:
    """
    Best-effort summary of hass.data[DOMAIN][entry_id] runtime.

    AMP may not store anything here; keep robust.
    """
    out: dict[str, Any] = {"present": entry_runtime is not None}

    if isinstance(entry_runtime, Mapping):
        out["runtime_type"] = "mapping"
        out["runtime_keys"] = _maybe_keys(entry_runtime)
        # Common “bucket” counts if they happen to exist.
        for key in COMMON_BUCKET_COUNTS:
            if key in entry_runtime:
                out[f"{key}_count"] = _maybe_len(entry_runtime.get(key))
        # Small sample of names
        for key in DEVICE_PLAYER_BUCKETS:
            if key in entry_runtime:
                sample = _sample_names(entry_runtime.get(key))
                if sample:
                    out[f"{key}_sample_names"] = sample
                break
    else:
        if entry_runtime is not None:
            out["runtime_type"] = type(entry_runtime).__name__

    return out


def _obfuscate_identifier(val: Any) -> str:
    """Return a shortened, non-identifying representation of a value.

    Non-string, empty, or very short values are fully masked. Longer strings
    are reduced to a minimal prefix and suffix to aid debugging without
    exposing the original identifier.
    """
    if not isinstance(val, str) or not val or len(val) <= 4:
        return "****"
    return f"{val[:2]}...{val[-2:]}"


def _obfuscate_title_with_email(title: str | None, email: str | None) -> str | None:
    """Obfuscate email in config entry title using the same mechanism as AMP logs."""
    if not title or not email:
        return title

    try:
        # Lazy import to keep diagnostics import cheap
        from alexapy import hide_email  # pylint: disable=import-outside-toplevel

        redacted = hide_email(email)
    except (ImportError, AttributeError, TypeError, ValueError):
        redacted = _obfuscate_identifier(email)

    return title.replace(email, redacted)


def _get_safe_config_entry_title(config_entry: ConfigEntry) -> str | None:
    """Get obfuscated config entry title."""
    email = config_entry.data.get("email")
    return _obfuscate_title_with_email(config_entry.title, email)


def _summarize_amp_domain(domain_data: Any, config_entry: ConfigEntry) -> dict:
    """
    Best-effort summary of hass.data[DOMAIN] for AMP.

    AMP historically stores account/login state in custom structures, not always
    keyed by entry_id, and often not using DataUpdateCoordinator.
    """
    out: dict[str, Any] = {}
    out["domain_data_present"] = domain_data is not None
    out["domain_data_type"] = (
        type(domain_data).__name__ if domain_data is not None else None
    )

    if not isinstance(domain_data, Mapping):
        return out

    out["domain_keys"] = _maybe_keys(domain_data)

    # Try a few common/likely buckets without dumping contents.
    # NOTE: We deliberately avoid copying values; only report counts/types/samples.
    for key in COMMON_DIAGNOSTIC_BUCKETS:
        if key in domain_data:
            val = domain_data.get(key)
            out[f"{key}_type"] = type(val).__name__
            out[f"{key}_len"] = _maybe_len(val)
            sample = _sample_names(val)
            if sample:
                out[f"{key}_sample_names"] = sample

    # Try to locate the specific account blob by email/title if present.
    # The config entry title often contains "email - url". We'll only use it to
    # match keys; we won't add the email to diagnostics (redaction will remove it).
    raw_title = config_entry.title or ""
    email = config_entry.data.get("email")
    out["entry_title_hint"] = _obfuscate_title_with_email(raw_title, email)
    # Some integrations store per-entry runtime keyed by entry_id *or* by title/email.
    # Report whether those keys exist.
    out["has_entry_id_key"] = config_entry.entry_id in domain_data
    out["has_title_key"] = raw_title in domain_data if raw_title else False

    return out


# --------------------
# Diagnostics entry points
# --------------------
async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict:
    """Return diagnostics for a config entry."""
    domain_data = hass.data.get(DOMAIN)
    safe_title = _get_safe_config_entry_title(config_entry)

    # AMP currently doesn't store runtime under entry_id.
    # This adds future-proofing for if and when it does.
    entry_runtime = None
    if isinstance(domain_data, Mapping):
        entry_runtime = domain_data.get(config_entry.entry_id)

    # Coordinator discovery:
    # 1) Try under entry_runtime (best practice)
    # 2) If none found and domain_data is a mapping, try domain_data as a whole
    coordinators: list[DataUpdateCoordinator] = []
    searched: list[str] = []

    if entry_runtime is not None:
        searched.append("hass.data[DOMAIN][entry_id]")
        coordinators = _find_coordinators(entry_runtime)

    if not coordinators and isinstance(domain_data, Mapping):
        searched.append("hass.data[DOMAIN]")
        coordinators = _find_coordinators(domain_data)

    coordinator_summaries = [_summarize_coordinator(c) for c in coordinators]

    data: dict = {
        "entry": {
            "entry_id": config_entry.entry_id,
            "title": safe_title,
            "domain": config_entry.domain,
            "version": config_entry.version,
            "minor_version": config_entry.minor_version,
        },
        # Include config + options; sensitive values are redacted below.
        "data": dict(config_entry.data),
        "options": dict(config_entry.options),
        "account": {
            "searched_for_coordinators_in": searched,
            "coordinator_count": len(coordinator_summaries),
            "coordinators": coordinator_summaries,
            # AMP-specific summaries (useful when coordinator_count == 0)
            "amp_entry_runtime_summary": _summarize_amp_entry_runtime(entry_runtime),
            "amp_domain_summary": _summarize_amp_domain(domain_data, config_entry),
        },
    }

    return async_redact_data(data, TO_REDACT)


async def async_get_device_diagnostics(
    _hass: HomeAssistant, config_entry: ConfigEntry, device: dr.DeviceEntry
) -> dict:
    """Return diagnostics for a specific device."""
    safe_title = _get_safe_config_entry_title(config_entry)

    try:
        # Lazy import to keep diagnostics import cheap
        from alexapy import hide_serial  # pylint: disable=import-outside-toplevel

        safe_serial = hide_serial(device.serial_number)
    except (ImportError, AttributeError, TypeError, ValueError):
        safe_serial = _obfuscate_identifier(device.serial_number)

    data: dict = {
        "device": {
            "id": _obfuscate_identifier(device.id),
            "name": device.name,
            "name_by_user": device.name_by_user,
            "manufacturer": device.manufacturer,
            "model": device.model,
            "sw_version": device.sw_version,
            "serial_number": safe_serial,
            "identifiers": sorted(
                (domain, _obfuscate_identifier(value))
                for domain, value in device.identifiers
            ),
            "via_device_id": _obfuscate_identifier(device.via_device_id),
        },
        "config_entry": {
            "entry_id": config_entry.entry_id,
            "title": safe_title,
        },
    }

    return async_redact_data(data, TO_REDACT)
