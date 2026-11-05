"""
Alexa Devices buttons.

SPDX-License-Identifier: Apache-2.0

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""

import logging

from alexapy import AlexapyConnectionError, AlexapyLoginError
from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.const import CONF_EMAIL
from homeassistant.core import callback
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.event import async_track_state_change_event

from . import DATA_ALEXAMEDIA, DOMAIN
from .helpers import (
    add_devices,
    async_restart_device,
    hide_email,
    report_relogin_required,
    safe_get,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, add_devices_callback, discovery_info=None):
    """Set up the Alexa button platform."""
    devices: list[AlexaRestartButton] = []
    account = None
    if config:
        account = config.get(CONF_EMAIL)
    if account is None and discovery_info:
        account = safe_get(discovery_info, ["config", CONF_EMAIL])
    if account is None:
        raise ConfigEntryNotReady

    account_dict = hass.data[DATA_ALEXAMEDIA]["accounts"][account]
    entities = account_dict.setdefault("entities", {})
    buttons = entities.setdefault("button", {})
    staged: dict[str, AlexaRestartButton] = {}

    for key, device in account_dict["devices"]["media_player"].items():
        if "ALEXA_DEVICE_REBOOT" not in device.get("capabilities", []):
            continue
        if key in buttons:
            continue

        client = account_dict["entities"]["media_player"].get(key)
        if client is None:
            _LOGGER.debug(
                "%s: Media player %s not loaded yet; delaying button setup",
                hide_email(account),
                key,
            )
            raise ConfigEntryNotReady

        button = AlexaRestartButton(client, device)
        staged[key] = button
        devices.append(button)

    added = await add_devices(hide_email(account), devices, add_devices_callback)
    if added:
        buttons.update(staged)
    return added


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Set up the Alexa button platform by config_entry."""
    return await async_setup_platform(
        hass, config_entry.data, async_add_devices, discovery_info=None
    )


async def async_unload_entry(hass, entry) -> bool:
    """Unload the Alexa button platform."""
    account = entry.data[CONF_EMAIL]
    account_dict = hass.data[DATA_ALEXAMEDIA]["accounts"][account]
    _LOGGER.debug("Attempting to unload buttons")
    for button in account_dict.get("entities", {}).get("button", {}).values():
        await button.async_remove()
    return True


class AlexaRestartButton(ButtonEntity):
    """Restart button for an Echo device."""

    _attr_has_entity_name = True
    _attr_translation_key = "restart"
    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, client, device) -> None:
        """Initialize the restart button."""
        self._client = client
        self._device_type = device["deviceType"]
        self._attr_unique_id = f"{client.unique_id}_restart"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, client.unique_id)},
        }

    @property
    def available(self) -> bool:
        """Return whether the Echo is available."""
        return bool(self._client.available)

    async def async_added_to_hass(self) -> None:
        """Track media player availability changes."""
        entity_id = getattr(self._client, "entity_id", None)
        if entity_id:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass, [entity_id], self._handle_client_state
                )
            )

    @callback
    def _handle_client_state(self, _event) -> None:
        """Refresh the button when its media player state changes."""
        self.async_write_ha_state()

    async def async_press(self) -> None:
        """Restart the Echo."""
        self._client.check_login_changes()
        try:
            success = await async_restart_device(
                self._client._login,
                self._device_type,
                self._client.device_serial_number,
            )
        except AlexapyLoginError as err:
            report_relogin_required(
                self.hass, self._client._login, self._client._login.email
            )
            raise HomeAssistantError(
                f"Unable to restart {self._client.name}: {err}"
            ) from err
        except AlexapyConnectionError as err:
            raise HomeAssistantError(
                f"Unable to restart {self._client.name}: {err}"
            ) from err

        if not success:
            raise HomeAssistantError(f"Unable to restart {self._client.name}")
