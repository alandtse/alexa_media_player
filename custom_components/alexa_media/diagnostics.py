"""Diagnostics support for Alexa Media Player."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.redact import async_redact_data
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .helpers import hide_email

# Be conservative: diagnostics often get pasted into GitHub issues.
# Redact both common HA auth keys and AMP/Alexa-ish keys.
_TO_REDACT: set[str] = {
    "email",
    "password",
    "access_token",
    "refresh_token",
    "token",
    "csrf",
    "cookie",
    "cookies",
    "session",
    "sessionid",
    "macDms",
    "mac_dms",
    "otp_secret",
    "authorization_code",
    "code_verifier",
    "adp_token",
    "device_private_key",
    "customerId",
    "serialNumber",
    "serial_number",
}


# --------------------
# Small utilities
# --------------------
def _safe_dt(val: Any) -> str | None:
    """Serialize datetimes safely for JSON diagnostics."""
    if isinstance(val, datetime):
        return val.isoformat()
    return None


def _redact_serial(serial: str | None) -> str | None:
    """Return a partially-redacted serial number for diagnostics."""
    if not serial:
        return serial
    if len(serial) <= 6:
        return "****"
    return f"{serial[:2]}***{serial[-4:]}"


def _maybe_len(val: Any) -> int | None:
    if isinstance(val, (list, tuple, dict, set)):
        return len(val)
    return None


def _maybe_keys(val: Any, limit: int = 50) -> list[str] | None:
    if isinstance(val, Mapping):
        try:
            return sorted([str(k) for k in val.keys()])[:limit]
        except Exception:
            return None
    return None


def _sample_names(val: Any, *, limit: int = 5) -> list[str] | None:
    """Try to sample human-friendly names from a list/dict of device-like objects."""
    names: list[str] = []

    def add_name(x: Any) -> None:
        if isinstance(x, Mapping):
            for key in ("name", "deviceName", "accountName", "friendlyName", "title"):
                v = x.get(key)
                if isinstance(v, str) and v:
                    names.append(v)
                    return
        v = getattr(x, "name", None)
        if isinstance(v, str) and v:
            names.append(v)

    if isinstance(val, Mapping):
        for v in list(val.values())[: limit * 2]:
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

    def walk(x: Any) -> None:
        if isinstance(x, DataUpdateCoordinator):
            found.append(x)
            return
        if is_dataclass(x):
            walk(asdict(x))
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
        # Preserve insertion order (avoids "sample vs full" order mismatch),
        # and keep payload small.
        keys = list(cdata.keys())
        out["data_key_count"] = len(keys)
        out["data_key_sample"] = [str(k) for k in keys[:10]]

        # For AMP, keys are often opaque UUIDs; the *value types* are often more helpful.
        sample_vals = []
        for k in keys[:3]:
            try:
                sample_vals.append(type(cdata[k]).__name__)
            except Exception:
                sample_vals.append("unknown")
        if sample_vals:
            out["data_value_types_sample"] = sample_vals

        # If coordinator.data sometimes contains named buckets (future-proof),
        # include just counts (but only if those keys actually exist).
        for key in (
            "devices",
            "devices_list",
            "media_players",
            "players",
            "notifications",
            "entities",
            "accounts",
        ):
            if key in cdata:
                out[f"{key}_count"] = _maybe_len(cdata.get(key))

        # If AMP ever exposes last_called through coordinator.data, include only safe fields.
        last_called = cdata.get("last_called")
        if isinstance(last_called, Mapping):
            out["last_called"] = {
                "timestamp": last_called.get("timestamp"),
                "summary": last_called.get("summary"),
            }

        # If there are device/player buckets, sample friendly names (no IDs).
        for key in ("devices", "media_players", "players"):
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
    data = {
        "name": getattr(coordinator, "name", None),
        "last_update_success": getattr(coordinator, "last_update_success", None),
        "last_exception": (
            repr(getattr(coordinator, "last_exception", None))
            if getattr(coordinator, "last_exception", None)
            else None
        ),
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
    except Exception:
        data["data_summary_error"] = True

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
        for key in (
            "accounts",
            "devices",
            "media_players",
            "players",
            "notifications",
            "entities",
        ):
            if key in entry_runtime:
                out[f"{key}_count"] = _maybe_len(entry_runtime.get(key))
        # Small sample of names
        for key in ("devices", "media_players", "players"):
            if key in entry_runtime:
                sample = _sample_names(entry_runtime.get(key))
                if sample:
                    out[f"{key}_sample_names"] = sample
                break
    else:
        if entry_runtime is not None:
            out["runtime_type"] = type(entry_runtime).__name__

    return out


def _obfuscate_title_with_email(title: str | None, email: str | None) -> str | None:
    """Obfuscate email in config entry title using the same mechanism as AMP logs."""
    if not title or not email:
        return title
    return title.replace(email, hide_email(email))


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
    for key in ("accounts", "account", "logins", "login", "sessions", "session"):
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
    email = config_entry.data.get("email")
    safe_title = _obfuscate_title_with_email(config_entry.title, email)

    # AMP *might* store runtime under entry_id, but often doesn't.
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

    return async_redact_data(data, _TO_REDACT)


async def async_get_device_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry, device: dr.DeviceEntry
) -> dict:
    """Return diagnostics for a specific device."""
    email = config_entry.data.get("email")
    safe_title = _obfuscate_title_with_email(config_entry.title, email)
    data: dict = {
        "device": {
            "id": device.id,
            "name": device.name,
            "name_by_user": device.name_by_user,
            "manufacturer": device.manufacturer,
            "model": device.model,
            "sw_version": device.sw_version,
            "serial_number": _redact_serial(device.serial_number),
            "identifiers": sorted(device.identifiers),
            "via_device_id": device.via_device_id,
        },
        "config_entry": {
            "entry_id": config_entry.entry_id,
            "title": safe_title,
        },
    }

    return async_redact_data(data, _TO_REDACT)

