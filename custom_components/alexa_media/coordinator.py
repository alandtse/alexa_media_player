"""Optimized DataUpdateCoordinator for Alexa Media Player.

Optimizations:
- Debouncer for request coalescing
- Type-safe runtime data integration
"""

from __future__ import annotations

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


class AlexaMediaCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for Alexa Media Player.

    Features:
    - Debounced refresh requests to avoid API hammering
    - Type-safe integration with runtime_data
    """

    def __init__(
        self,
        hass: HomeAssistant,
        runtime_data: AlexaRuntimeData | None,
        update_method: Callable,
        scan_interval: float | None = None,
    ) -> None:
        """Initialize the coordinator.

        Args:
            hass: Home Assistant instance
            runtime_data: Runtime data for this config entry
            update_method: Async method to fetch data
            scan_interval: Polling interval in seconds (default: SCAN_INTERVAL)
        """
        self.runtime_data = runtime_data
        self._scan_interval = scan_interval or SCAN_INTERVAL.total_seconds()

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
            immediate=True,
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_method=update_method,
            update_interval=update_interval,
            request_refresh_debouncer=debouncer,
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
