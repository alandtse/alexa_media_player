"""
Alexa Devices Sensors.

SPDX-License-Identifier: Apache-2.0

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""

import logging
from typing import List  # noqa pylint: disable=unused-import

from alexapy import hide_serial
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
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
    devices: List[BinarySensorEntity] = []
    account = config[CONF_EMAIL] if config else discovery_info["config"][CONF_EMAIL]
    account_dict = hass.data[DATA_ALEXAMEDIA]["accounts"][account]
    include_filter = config.get(CONF_INCLUDE_DEVICES, [])
    exclude_filter = config.get(CONF_EXCLUDE_DEVICES, [])
    coordinator = account_dict["coordinator"]
    binary_entities = account_dict.get("devices", {}).get("binary_sensor", [])
    if binary_entities and account_dict["options"].get(CONF_EXTENDED_ENTITY_DISCOVERY):
        for be in binary_entities:
            _LOGGER.debug(
                "Creating entity %s for a binary_sensor with name %s",
                hide_serial(be["id"]),
                be["name"],
            )
            contact_sensor = AlexaContact(coordinator, be)
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

    def __init__(self, coordinator, details):
        super().__init__(coordinator)
        self.alexa_entity_id = details["id"]
        self._name = details["name"]

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return self.alexa_entity_id

    @property
    def is_on(self):
        detection = parse_detection_state_from_coordinator(
            self.coordinator, self.alexa_entity_id
        )

        return detection == 'DETECTED' if detection is not None else None

    @property
    def assumed_state(self) -> bool:
        last_refresh_success = (
            self.coordinator.data and self.alexa_entity_id in self.coordinator.data
        )
        return not last_refresh_success
