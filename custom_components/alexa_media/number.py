"""
Alexa Devices Numbers.

SPDX-License-Identifier: Apache-2.0

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""

import asyncio
import logging

from alexapy import AlexaAPI, hide_serial
from homeassistant.components.number import NumberEntity
from homeassistant.const import PERCENTAGE
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers.entity import EntityCategory

from . import CONF_EMAIL, DATA_ALEXAMEDIA, DOMAIN as ALEXA_DOMAIN, hide_email
from .alexa_media import AlexaMedia
from .display import (
    SETTING_BRIGHTNESS,
    AlexaDisplayBrightness,
    async_get_display_state,
    can_probe_display,
    display_registration_is_current,
)
from .helpers import _catch_login_errors, add_devices, config_entry_config, safe_get

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, add_devices_callback, discovery_info=None):
    """Set up the Alexa number platform."""
    account = None
    if config:
        account = config.get(CONF_EMAIL)
    if account is None and discovery_info:
        account = safe_get(discovery_info, ["config", CONF_EMAIL])
    if account is None:
        raise ConfigEntryNotReady
    account_dict = hass.data[DATA_ALEXAMEDIA]["accounts"][account]
    numbers = account_dict["entities"]["number"]
    staged: dict[str, NumberEntity] = {}
    _LOGGER.debug("%s: Loading numbers", hide_email(account))

    # Display probing is best-effort and must not block notification volumes
    # for devices whose media-player client is already available.
    login_obj = account_dict.get("login_obj")

    async def _probe_displays():
        async def _probe_one(key, device):
            client = account_dict["entities"]["media_player"].get(key)
            if client is None or login_obj is None:
                return key, None
            try:
                state = await async_get_display_state(
                    hass, account_dict, login_obj, device, client
                )
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug(
                    "%s: Unable to probe display brightness: %s",
                    hide_serial(key),
                    err,
                )
                return key, None
            return key, state

        results = await asyncio.gather(
            *(
                _probe_one(key, device)
                for key, device in list(account_dict["devices"]["media_player"].items())
                if can_probe_display(device)
            ),
            return_exceptions=True,
        )
        states = {}
        for result in results:
            if isinstance(result, BaseException):
                continue
            key, state = result
            if state is not None and state.supports(SETTING_BRIGHTNESS):
                states[key] = state
        return states

    registration_key = "display_registration_number"

    async def _register_displays():
        """Probe display settings and add brightness entities after setup."""
        display_states = await _probe_displays()
        if not display_registration_is_current(hass, account, account_dict):
            return
        display_staged = {}
        for key, display_state in display_states.items():
            if getattr(display_state, "_stopped", False) is True:
                continue
            current = account_dict.get("display_states")
            if current and current.get(key) is not display_state:
                continue
            entity_key = f"{key}_display_brightness"
            if entity_key in numbers:
                continue
            display_staged[entity_key] = AlexaDisplayBrightness(display_state)

        if display_staged:
            added = await add_devices(
                hide_email(account),
                list(display_staged.values()),
                add_devices_callback,
            )
            if added:
                numbers.update(display_staged)

    for key in account_dict["devices"]["number"]:
        client = account_dict["entities"]["media_player"].get(key)
        if client is None or key in numbers:
            continue
        staged[key] = AlexaNotificationVolume(client)

    # Submit notification volumes without waiting for display discovery.
    added = await add_devices(
        hide_email(account), list(staged.values()), add_devices_callback
    )
    if not added:
        return False
    numbers.update(staged)

    if any(
        can_probe_display(device)
        for device in account_dict["devices"]["media_player"].values()
    ):
        previous = account_dict.get(registration_key)
        if isinstance(previous, asyncio.Task) and not previous.done():
            previous.cancel()
        display_task = asyncio.create_task(_register_displays())
        account_dict[registration_key] = display_task
        setup_tasks = account_dict.setdefault("display_setup_tasks", set())
        setup_tasks.add(display_task)
        display_task.add_done_callback(setup_tasks.discard)
    return True


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Set up the Alexa number platform by config_entry."""
    return await async_setup_platform(
        hass, config_entry_config(config_entry), async_add_devices, discovery_info=None
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
                f"Could not set the alarm volume of {self._client.device_name}"
            )
        device["notification_volume"] = int(value)
        self.async_write_ha_state()
