"""
Alexa Devices Sensors.

SPDX-License-Identifier: Apache-2.0

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""

import logging

from alexapy import hide_serial
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import (
    CONF_EMAIL,
    CONF_EXCLUDE_DEVICES,
    CONF_INCLUDE_DEVICES,
    DATA_ALEXAMEDIA,
    hide_email,
)
from .alexa_entity import parse_detection_state_from_coordinator
from .const import CONF_EXTENDED_ENTITY_DISCOVERY
from .helpers import add_devices

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, add_devices_callback, discovery_info=None):
    """Set up the Alexa sensor platform."""
    devices: list[BinarySensorEntity] = []
    account = None
    if config:
        account = config.get(CONF_EMAIL)
    if account is None and discovery_info:
        account = discovery_info.get("config", {}).get(CONF_EMAIL)
    if account is None:
        raise ConfigEntryNotReady
    account_dict = hass.data[DATA_ALEXAMEDIA]["accounts"][account]
    include_filter = config.get(CONF_INCLUDE_DEVICES, [])
    exclude_filter = config.get(CONF_EXCLUDE_DEVICES, [])
    coordinator = account_dict["coordinator"]
    binary_entities = account_dict.get("devices", {}).get("binary_sensor", [])
    if binary_entities and account_dict["options"].get(CONF_EXTENDED_ENTITY_DISCOVERY):
        for binary_entity in binary_entities:
            _LOGGER.debug(
                "Creating entity %s for a binary_sensor with name %s",
                hide_serial(binary_entity["id"]),
                binary_entity["name"],
            )
            contact_sensor = AlexaContact(coordinator, binary_entity)
            account_dict["entities"]["binary_sensor"].append(contact_sensor)
            devices.append(contact_sensor)

    return await add_devices(
        hide_email(account),
        devices,
        add_devices_callback,
        include_filter,
        exclude_filter,
    )


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Set up the Alexa sensor platform by config_entry."""
    return await async_setup_platform(
        hass, config_entry.data, async_add_devices, discovery_info=None
    )


async def async_unload_entry(hass, entry) -> bool:
    """Unload a config entry."""
    account = entry.data[CONF_EMAIL]
    account_dict = hass.data[DATA_ALEXAMEDIA]["accounts"][account]
    _LOGGER.debug("Attempting to unload binary sensors")
    for binary_sensor in account_dict["entities"]["binary_sensor"]:
        await binary_sensor.async_remove()
    return True


class AlexaContact(CoordinatorEntity, BinarySensorEntity):
    """A contact sensor controlled by an Echo."""

    _attr_device_class = BinarySensorDeviceClass.DOOR

    def __init__(self, coordinator: CoordinatorEntity, details: dict):
        """Initialize alexa contact sensor.

        Args
            coordinator (CoordinatorEntity): Coordinator
            details (dict): Details dictionary

        """
        super().__init__(coordinator)
        self.alexa_entity_id = details["id"]
        self._name = details["name"]

    @property
    def name(self):
        """Return name."""
        return self._name

    @property
    def unique_id(self):
        """Return unique id."""
        return self.alexa_entity_id

    @property
    def is_on(self):
        """Return whether on."""
        detection = parse_detection_state_from_coordinator(
            self.coordinator, self.alexa_entity_id
        )

        return detection == "DETECTED" if detection is not None else None

    @property
    def assumed_state(self) -> bool:
        """Return assumed state."""
        last_refresh_success = (
            self.coordinator.data and self.alexa_entity_id in self.coordinator.data
        )
        return not last_refresh_success
