"""
Alexa Devices Sensors.

SPDX-License-Identifier: Apache-2.0

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""
import asyncio
import datetime
import logging
from typing import Callable, List, Optional, Text  # noqa pylint: disable=unused-import

from alexapy import AlexaAPI, hide_serial
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    SUPPORT_BRIGHTNESS,
    LightEntity,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import (
    CONF_EMAIL,
    CONF_EXCLUDE_DEVICES,
    CONF_INCLUDE_DEVICES,
    DATA_ALEXAMEDIA,
    hide_email,
)
from .alexa_entity import (
    parse_brightness_from_coordinator,
    parse_power_from_coordinator,
)
from .const import CONF_EXTENDED_ENTITY_DISCOVERY
from .helpers import add_devices

_LOGGER = logging.getLogger(__name__)

LOCAL_TIMEZONE = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo


async def async_setup_platform(hass, config, add_devices_callback, discovery_info=None):
    """Set up the Alexa sensor platform."""
    devices: List[LightEntity] = []
    account = config[CONF_EMAIL] if config else discovery_info["config"][CONF_EMAIL]
    account_dict = hass.data[DATA_ALEXAMEDIA]["accounts"][account]
    include_filter = config.get(CONF_INCLUDE_DEVICES, [])
    exclude_filter = config.get(CONF_EXCLUDE_DEVICES, [])
    coordinator = account_dict["coordinator"]
    hue_emulated_enabled = "emulated_hue" in hass.config.as_dict().get("components", set())
    light_entities = account_dict.get("devices", {}).get("light", [])
    if light_entities and account_dict["options"].get(CONF_EXTENDED_ENTITY_DISCOVERY):
        for le in light_entities:
            if not (le["is_hue_v1"] and hue_emulated_enabled):
                _LOGGER.debug("Creating entity %s for a light with name %s", hide_serial(le["id"]), le["name"])
                light = AlexaLight(coordinator, account_dict["login_obj"], le)
                account_dict["entities"]["light"].append(light)
                devices.append(light)
            else:
                _LOGGER.debug("Light '%s' has not been added because it may originate from emulated_hue", le["name"])

    if devices:
        await coordinator.async_refresh()

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
    _LOGGER.debug("Attempting to unload lights")
    for light in account_dict["entities"]["light"]:
        await light.async_remove()
    return True


def ha_brightness_to_alexa(ha):
    return ha / 255 * 100


def alexa_brightness_to_ha(alexa):
    return alexa / 100 * 255


class AlexaLight(CoordinatorEntity, LightEntity):
    """A light controlled by an Echo. """

    def __init__(self, coordinator, login, details):
        super().__init__(coordinator)
        self.alexa_entity_id = details["id"]
        self._name = details["name"]
        self._login = login
        self._supported_features = SUPPORT_BRIGHTNESS if details["brightness"] else 0

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return self.alexa_entity_id

    @property
    def supported_features(self):
        return self._supported_features

    @property
    def is_on(self):
        return parse_power_from_coordinator(self.coordinator, self.alexa_entity_id) == "ON"

    @property
    def brightness(self):
        bright = parse_brightness_from_coordinator(self.coordinator, self.alexa_entity_id)
        return alexa_brightness_to_ha(bright) if bright is not None else 255

    @property
    def assumed_state(self) -> bool:
        last_refresh_success = self.coordinator.data and self.alexa_entity_id in self.coordinator.data
        return not last_refresh_success

    @staticmethod
    async def _wait_for_lights():
        await asyncio.sleep(2)

    async def async_turn_on(self, **kwargs):
        if self._supported_features & SUPPORT_BRIGHTNESS:
            bright = ha_brightness_to_alexa(kwargs.get(ATTR_BRIGHTNESS, 255))
            await AlexaAPI.set_light_state(self._login, self.alexa_entity_id, power_on=True, brightness=bright)
        else:
            await AlexaAPI.set_light_state(self._login, self.alexa_entity_id, power_on=True)
        await self._wait_for_lights()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        await AlexaAPI.set_light_state(self._login, self.alexa_entity_id, power_on=False)
        await self._wait_for_lights()
        await self.coordinator.async_request_refresh()
