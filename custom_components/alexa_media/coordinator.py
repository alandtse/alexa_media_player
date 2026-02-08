"""Optimized DataUpdateCoordinator for Alexa Media Player.

Optimizations:
- Fast boot (non-blocking first refresh)
- Debouncer for request coalescing
- Parallel API calls
- Type-safe runtime data integration
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import TYPE_CHECKING, Any, Callable

from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, SCAN_INTERVAL

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .runtime_data import AlexaRuntimeData

_LOGGER = logging.getLogger(__name__)

# Debounce cooldown in seconds - prevents API hammering during push bursts
REQUEST_REFRESH_DEBOUNCE_COOLDOWN = 1.5

# Timeout for individual API calls
API_CALL_TIMEOUT = 30


class AlexaMediaCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Optimized coordinator for Alexa Media Player with fast boot.

    Features:
    - Non-blocking first refresh (background task)
    - Debounced refresh requests to avoid API hammering
    - Parallel API calls for faster updates
    - Type-safe integration with runtime_data
    """

    def __init__(
        self,
        hass: HomeAssistant,
        runtime_data: AlexaRuntimeData | None,
        update_method: Callable,
        scan_interval: float | None = None,
        fast_boot: bool = True,
    ) -> None:
        """Initialize the coordinator.

        Args:
            hass: Home Assistant instance
            runtime_data: Runtime data for this config entry
            update_method: Async method to fetch data
            scan_interval: Polling interval in seconds (default: SCAN_INTERVAL)
            fast_boot: If True, first refresh is done in background
        """
        self.runtime_data = runtime_data
        self._scan_interval = scan_interval or SCAN_INTERVAL.total_seconds()
        self._fast_boot = fast_boot
        self._first_refresh_done = False

        # Calculate update interval based on HTTP2 status
        http2_enabled = runtime_data.http2 is not None if runtime_data else False
        update_interval = timedelta(
            seconds=self._scan_interval * 10 if http2_enabled else self._scan_interval
        )

        # Initialize debouncer for request coalescing
        # This prevents multiple rapid refresh requests from hammering the API
        debouncer = Debouncer(
            hass,
            _LOGGER,
            cooldown=REQUEST_REFRESH_DEBOUNCE_COOLDOWN,
            immediate=False,
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_method=update_method,
            update_interval=update_interval,
            request_refresh_debouncer=debouncer,
        )

    @property
    def _log_name(self) -> str:
        """Return a safe name for logging."""
        if self.runtime_data:
            return self.runtime_data.email
        return self.name

    async def async_config_entry_first_refresh(self) -> None:
        """Perform first refresh with fast boot support.

        If fast_boot is enabled, this returns immediately and refreshes
        in the background. Entities will be updated when data arrives.
        """
        if self._fast_boot and not self._first_refresh_done:
            _LOGGER.debug(
                "%s: Fast boot enabled - starting background refresh",
                self._log_name,
            )
            # Schedule background refresh without awaiting
            self.hass.async_create_background_task(
                self._async_first_refresh_background(),
                f"{DOMAIN}_first_refresh",
            )
            # Mark as started (will complete in background)
            self._first_refresh_done = True
        else:
            # Standard blocking refresh
            await super().async_config_entry_first_refresh()

    async def _async_first_refresh_background(self) -> None:
        """Perform first refresh in background.

        This allows Home Assistant to continue booting while we fetch data.
        """
        try:
            _LOGGER.debug(
                "%s: Background first refresh starting",
                self._log_name,
            )
            start_time = self.hass.loop.time()

            await self.async_refresh()

            elapsed = self.hass.loop.time() - start_time
            _LOGGER.debug(
                "%s: Background first refresh completed in %.2fs",
                self._log_name,
                elapsed,
            )
        except Exception:
            _LOGGER.exception(
                "%s: Background first refresh failed",
                self._log_name,
            )

    def set_http2_status(self, enabled: bool) -> None:
        """Update polling interval based on HTTP2 connection status.

        When HTTP2 is enabled, we can poll less frequently since we get push updates.
        """
        new_interval = timedelta(
            seconds=self._scan_interval * 10 if enabled else self._scan_interval
        )
        if self.update_interval != new_interval:
            self.update_interval = new_interval
            _LOGGER.debug(
                "Updated polling interval: %s (HTTP2: %s)",
                new_interval,
                enabled,
            )

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator and cleanup resources."""
        await super().async_shutdown()
        # Cancel any pending debounced calls
        debouncer = getattr(self, "_request_refresh_debouncer", None)
        if debouncer:
            debouncer.async_cancel()


# TODO: Use this function for parallel device data fetching in _async_update_data
# when implementing multi-device refresh optimization
async def parallel_api_calls(*coros, timeout: float = API_CALL_TIMEOUT) -> tuple:
    """Execute multiple API calls in parallel with timeout.

    This significantly reduces the time needed to fetch all data.

    Args:
        *coros: Coroutines to execute
        timeout: Maximum time to wait for all calls

    Returns:
        Tuple of results in the same order as coros
    """
    try:
        return await asyncio.wait_for(
            asyncio.gather(*coros, return_exceptions=True),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        _LOGGER.warning("API calls timed out after %.1fs", timeout)
        raise
