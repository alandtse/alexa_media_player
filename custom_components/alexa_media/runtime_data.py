"""Runtime data for Alexa Media Player integration.

This module implements the Platinum architecture using entry.runtime_data
instead of the legacy hass.data[DOMAIN] pattern.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import logging
from typing import TYPE_CHECKING, Any, Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    DEFAULT_EXTENDED_ENTITY_DISCOVERY,
    DEFAULT_PUBLIC_URL,
    DEFAULT_QUEUE_DELAY,
)

if TYPE_CHECKING:
    from alexapy import AlexaLogin, HTTP2EchoClient

    from .alexa_entity import AlexaEntityData

_LOGGER = logging.getLogger(__name__)


@dataclass
class AlexaRuntimeData:
    """Runtime data for Alexa Media Player.

    This replaces the legacy dict-based storage in hass.data[DATA_ALEXAMEDIA]["accounts"][email].
    All fields are type-safe and properly initialized.
    """

    # Core components (optional to support partial initialisation)
    login_obj: AlexaLogin | None = None
    config_entry: ConfigEntry | None = None
    coordinator: DataUpdateCoordinator[AlexaEntityData] | None = None

    # HTTP2 Push connection
    http2: HTTP2EchoClient | None = None
    http2_error: int = 0
    http2_lastattempt: float = 0.0
    http2_commands: dict[str, float] = field(default_factory=dict)
    http2_activity: dict[str, Any] = field(
        default_factory=lambda: {"serials": {}, "refreshed": {}}
    )

    # Device storage
    devices: dict[str, Any] = field(
        default_factory=lambda: {
            "media_player": {},
            "switch": {},
            "guard": [],
            "light": [],
            "binary_sensor": [],
            "temperature": [],
            "smart_switch": [],
        }
    )
    entities: dict[str, Any] = field(
        default_factory=lambda: {
            "media_player": {},
            "switch": {},
            "sensor": {},
            "light": [],
            "binary_sensor": [],
            "alarm_control_panel": {},
            "smart_switch": [],
        }
    )
    excluded: dict[str, Any] = field(default_factory=dict)

    # State tracking
    new_devices: bool = True
    auth_info: dict[str, Any] | None = None
    should_get_network: bool = True
    second_account_index: int = 0

    # Notifications
    notifications: dict[str, Any] = field(default_factory=dict)
    notifications_pending: set[str] = field(default_factory=set)
    notifications_refresh_task: asyncio.Task | None = None
    notifications_retry_count: int = 0
    last_notif_poll: float = 0.0

    # Last called tracking
    last_called: dict[str, Any] | None = None
    last_called_customer_history_ts: int = 0
    last_called_probe_task: asyncio.Task | None = None
    last_called_probe_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    last_called_probe_last_run: float = 0.0
    last_push_activity: float = 0.0

    # Options (mirrored from config_entry)
    options: dict[str, Any] = field(default_factory=dict)

    # Listeners for cleanup
    listeners: list[Callable] = field(default_factory=list)

    def __post_init__(self):
        """Initialize computed fields after dataclass creation."""
        # Initialize options from config_entry if available
        if self.config_entry:
            from .const import (
                CONF_DEBUG,
                CONF_EXCLUDE_DEVICES,
                CONF_EXTENDED_ENTITY_DISCOVERY,
                CONF_INCLUDE_DEVICES,
                CONF_PUBLIC_URL,
                CONF_QUEUE_DELAY,
                CONF_SCAN_INTERVAL,
                DEFAULT_SCAN_INTERVAL,
            )

            self.options = {
                CONF_INCLUDE_DEVICES: self.config_entry.data.get(
                    CONF_INCLUDE_DEVICES, ""
                ),
                CONF_EXCLUDE_DEVICES: self.config_entry.data.get(
                    CONF_EXCLUDE_DEVICES, ""
                ),
                CONF_QUEUE_DELAY: self.config_entry.data.get(
                    CONF_QUEUE_DELAY, DEFAULT_QUEUE_DELAY
                ),
                CONF_SCAN_INTERVAL: self.config_entry.data.get(
                    CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                ),
                CONF_PUBLIC_URL: self.config_entry.data.get(
                    CONF_PUBLIC_URL, DEFAULT_PUBLIC_URL
                ),
                CONF_EXTENDED_ENTITY_DISCOVERY: self.config_entry.data.get(
                    CONF_EXTENDED_ENTITY_DISCOVERY, DEFAULT_EXTENDED_ENTITY_DISCOVERY
                ),
                CONF_DEBUG: self.config_entry.data.get(CONF_DEBUG, False),
            }

    @property
    def email(self) -> str:
        """Return account email."""
        return self.login_obj.email if self.login_obj else ""

    @property
    def url(self) -> str:
        """Return account URL."""
        return self.login_obj.url if self.login_obj else ""

    def get_device(self, device_type: str, serial: str) -> Any | None:
        """Get a device by type and serial."""
        devices = self.devices.get(device_type, {})
        if isinstance(devices, dict):
            return devices.get(serial)
        if isinstance(devices, list):
            for device in devices:
                if isinstance(device, dict) and device.get("serialNumber") == serial:
                    return device
                if (
                    device
                    and hasattr(device, "serialNumber")
                    and device.serialNumber == serial
                ):
                    return device
        return None

    def get_entity(self, entity_type: str, key: str) -> Any | None:
        """Get an entity by type and key."""
        entities = self.entities.get(entity_type, {})
        if isinstance(entities, dict):
            return entities.get(key)
        if isinstance(entities, list):
            for entity in entities:
                if hasattr(entity, "unique_id") and entity.unique_id == key:
                    return entity
                if hasattr(entity, "serial") and entity.serial == key:
                    return entity
        return None

    def add_listener(self, unsub: Callable) -> None:
        """Add a listener for cleanup."""
        self.listeners.append(unsub)
