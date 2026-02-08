"""Performance metrics and caching for Alexa Media Player.

Provides boot time tracking and intelligent data caching.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import time
from typing import Any

from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass
class BootMetrics:
    """Track boot performance metrics."""

    start_time: float = field(default_factory=time.monotonic)
    stages: dict[str, float] = field(default_factory=dict)

    def record_stage(self, stage_name: str) -> None:
        """Record a boot stage completion."""
        elapsed = time.monotonic() - self.start_time
        self.stages[stage_name] = elapsed
        _LOGGER.debug(
            "[BOOT METRICS] %s completed in %.3fs",
            stage_name,
            elapsed,
        )

    def get_summary(self) -> dict[str, Any]:
        """Get boot metrics summary."""
        total = time.monotonic() - self.start_time
        return {
            "total_time_seconds": round(total, 3),
            "stages": {k: round(v, 3) for k, v in self.stages.items()},
        }


class DataCache:
    """Simple TTL cache for API responses.

    Reduces redundant API calls during startup and normal operation.
    """

    def __init__(self, ttl_seconds: float = 30.0, max_entries: int = 128) -> None:
        """Initialize cache with TTL.

        Args:
            ttl_seconds: Time-to-live for cached entries
            max_entries: Maximum number of entries before evicting oldest
        """
        self._cache: dict[str, tuple[Any, float]] = {}
        self._ttl = ttl_seconds
        self._max_entries = max_entries
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Any | None:
        """Get value from cache if not expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if expired/missing
        """
        if key not in self._cache:
            self._misses += 1
            return None

        value, timestamp = self._cache[key]
        if time.monotonic() - timestamp > self._ttl:
            # Expired
            del self._cache[key]
            self._misses += 1
            return None

        self._hits += 1
        return value

    def set(self, key: str, value: Any) -> None:
        """Store value in cache.

        Note: Stores a direct reference (not a copy) for performance.
        Callers should not mutate cached values.

        Args:
            key: Cache key
            value: Value to cache
        """
        if len(self._cache) >= self._max_entries and key not in self._cache:
            oldest_key = min(self._cache, key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]
        self._cache[key] = (value, time.monotonic())

    def invalidate(self, key: str) -> None:
        """Remove key from cache."""
        self._cache.pop(key, None)

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    def get_stats(self) -> dict[str, int]:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        return {
            "entries": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate_percent": round(hit_rate, 1),
        }


class AlexaMetrics:
    """Central metrics collector for Alexa Media Player."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize metrics collector."""
        self.hass = hass
        self.boot_metrics: BootMetrics | None = None
        self.api_cache = DataCache(ttl_seconds=30.0)
        self._api_calls: dict[str, tuple[int, float]] = {}  # count, total_time

    def start_boot_tracking(self) -> None:
        """Start tracking boot performance."""
        self.boot_metrics = BootMetrics()
        _LOGGER.debug("[BOOT METRICS] Started tracking")

    def record_boot_stage(self, stage_name: str) -> None:
        """Record a boot stage completion."""
        if self.boot_metrics:
            self.boot_metrics.record_stage(stage_name)

    def record_api_call(self, endpoint: str, duration: float) -> None:
        """Record API call metrics.

        Args:
            endpoint: API endpoint name
            duration: Call duration in seconds
        """
        if endpoint not in self._api_calls:
            self._api_calls[endpoint] = (0, 0.0)

        count, total = self._api_calls[endpoint]
        self._api_calls[endpoint] = (count + 1, total + duration)

    def get_api_stats(self) -> dict[str, Any]:
        """Get API call statistics."""
        stats = {}
        for endpoint, (count, total) in self._api_calls.items():
            stats[endpoint] = {
                "calls": count,
                "total_time": round(total, 3),
                "avg_time": round(total / count, 3) if count > 0 else 0,
            }
        return stats

    def get_full_report(self) -> dict[str, Any]:
        """Get complete metrics report."""
        return {
            "boot": self.boot_metrics.get_summary() if self.boot_metrics else None,
            "cache": self.api_cache.get_stats(),
            "api_calls": self.get_api_stats(),
        }


def get_metrics(hass: HomeAssistant) -> AlexaMetrics | None:
    """Get metrics instance from hass data.

    Args:
        hass: Home Assistant instance

    Returns:
        AlexaMetrics instance or None if not initialized
    """
    if DOMAIN in hass.data and "metrics" in hass.data[DOMAIN]:
        return hass.data[DOMAIN]["metrics"]
    return None
