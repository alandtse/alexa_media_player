"""
Alexa Devices Numbers.

SPDX-License-Identifier: Apache-2.0

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""

import logging

from alexapy import AlexaAPI
from homeassistant.components.number import NumberEntity
from homeassistant.const import PERCENTAGE
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers.entity import EntityCategory

from . import CONF_EMAIL, DATA_ALEXAMEDIA, DOMAIN as ALEXA_DOMAIN, hide_email
from .alexa_media import AlexaMedia
from .helpers import _catch_login_errors, add_devices, safe_get

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, add_devices_callback, discovery_info=None):
    """Set up the Alexa number platform."""
    devices: list[AlexaNotificationVolume] = []
    account = None
    if config:
        account = config.get(CONF_EMAIL)
    if account is None and discovery_info:
        account = safe_get(discovery_info, ["config", CONF_EMAIL])
    if account is None:
        raise ConfigEntryNotReady
    account_dict = hass.data[DATA_ALEXAMEDIA]["accounts"][account]
    _LOGGER.debug("%s: Loading numbers", hide_email(account))
    for key in account_dict["devices"]["number"]:
        client = account_dict["entities"]["media_player"].get(key)
        if client is None or key in account_dict["entities"]["number"]:
            continue
        number = AlexaNotificationVolume(client)
        account_dict["entities"]["number"][key] = number
        devices.append(number)
    return await add_devices(hide_email(account), devices, add_devices_callback)


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Set up the Alexa number platform by config_entry."""
    return await async_setup_platform(
        hass, config_entry.data, async_add_devices, discovery_info=None
    )


async def async_unload_entry(hass, entry) -> bool:
    """Unload a config entry."""
    account = entry.data[CONF_EMAIL]
    _LOGGER.debug("Attempting to unload numbers")
    account_dict = hass.data[DATA_ALEXAMEDIA]["accounts"][account]
    for number in account_dict["entities"]["number"].values():
        await number.async_remove()
    return True


class AlexaNotificationVolume(NumberEntity, AlexaMedia):
    """Representation of an Alexa alarm and notification volume."""

    _attr_has_entity_name = True
    _attr_translation_key = "notification_volume"
    _attr_icon = "mdi:alarm-bell"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, client):
        """Initialize the Alexa number."""
        self._client = client
        self._attr_unique_id = f"{client.unique_id}_notification_volume"
        self._attr_device_info = {"identifiers": {(ALEXA_DOMAIN, client.unique_id)}}
        super().__init__(client, client._login)

    @property
    def _device(self) -> dict:
        return self.hass.data[DATA_ALEXAMEDIA]["accounts"][self.email]["devices"][
            "media_player"
        ].get(self._client.device_serial_number, {})

    @property
    def available(self):
        """Return the availability of the number."""
        return (
            self._client.available
            and self._device.get("notification_volume") is not None
        )

    @property
    def native_value(self):
        """Return the volume."""
        return self._device.get("notification_volume")

    @_catch_login_errors
    async def async_set_native_value(self, value: float) -> None:
        """Set the volume."""
        device = self._device
        if not await AlexaAPI.set_notification_volume(
            self._login,
            self._client.device_serial_number,
            device["deviceType"],
            device["notification_software_version"],
            int(value),
        ):
            raise HomeAssistantError(
                f"Could not set the alarm volume of {self._client.name}"
            )
        device["notification_volume"] = int(value)
        self.async_write_ha_state()
