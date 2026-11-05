"""
Echo display controls.

SPDX-License-Identifier: Apache-2.0

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
import json
import logging
from typing import Any

from alexapy import AlexaAPI, AlexaLogin
from homeassistant.components.number import NumberEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.event import async_track_time_interval

from .const import DOMAIN, MODEL_IDS

_LOGGER = logging.getLogger(__name__)

DISPLAY_SCAN_INTERVAL = timedelta(minutes=15)

SETTING_DISPLAY_POWER = "displayPower"
SETTING_BRIGHTNESS = "brightness"
SETTING_ADAPTIVE_BRIGHTNESS = "adaptiveBrightness"

DISPLAY_SETTINGS = (
    SETTING_DISPLAY_POWER,
    SETTING_BRIGHTNESS,
    SETTING_ADAPTIVE_BRIGHTNESS,
)

DISPLAY_MODEL_MARKERS = ("Echo Show", "Echo Spot", "Echo Dot Clock")


def supports_display(device: dict[str, Any]) -> bool:
    """Return whether the device is a known model with an Echo display."""
    model = MODEL_IDS.get(device.get("deviceType"), "")
    return any(marker in model for marker in DISPLAY_MODEL_MARKERS)


def _decode_setting(value: Any) -> Any:
    """Decode the JSON-encoded value used by the device settings API."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return value
    return value


async def async_get_device_setting(
    login: AlexaLogin, device_account_id: str, setting: str
) -> Any | None:
    """Read one device setting."""
    if not device_account_id:
        return None

    response = await AlexaAPI._static_request(
        "get",
        login,
        f"/api/v1/devices/{device_account_id}/settings/{setting}",
    )
    if response is None:
        return None

    try:
        data = await response.json(content_type=None)
    except (TypeError, ValueError):
        return None
    if not isinstance(data, dict) or "value" not in data:
        return None
    return _decode_setting(data["value"])


async def async_set_device_setting(
    login: AlexaLogin, device_account_id: str, setting: str, value: Any
) -> bool:
    """Write one device setting."""
    if not device_account_id:
        return False

    response = await AlexaAPI._static_request(
        "put",
        login,
        f"/api/v1/devices/{device_account_id}/settings/{setting}",
        data={"value": json.dumps(value)},
    )
    return response is not None


class DisplayState:
    """Shared display settings for one Echo."""

    def __init__(
        self,
        hass: HomeAssistant,
        login: AlexaLogin,
        device: dict[str, Any],
    ) -> None:
        """Initialize the display state."""
        self.hass = hass
        self.login = login
        self.device = device
        self.serial = device["serialNumber"]
        self.device_account_id = device.get("deviceAccountId", "")
        self._values: dict[str, Any] = {setting: None for setting in DISPLAY_SETTINGS}
        self._listeners: list = []
        self._refresh_lock = asyncio.Lock()
        self._unsub = None

    @property
    def client(self):
        """Return the media player client, if it is registered."""
        return self._client

    @client.setter
    def client(self, value) -> None:
        """Store the media player client for entity identity."""
        self._client = value

    def value(self, setting: str) -> Any | None:
        """Return the last known value of a setting."""
        return self._values.get(setting)

    @callback
    def async_add_listener(self, update_callback) -> callable:
        """Register an entity callback; returns an unsubscribe function."""
        self._listeners.append(update_callback)

        @callback
        def _remove() -> None:
            if update_callback in self._listeners:
                self._listeners.remove(update_callback)

        return _remove

    @callback
    def _async_notify(self) -> None:
        for update_callback in list(self._listeners):
            update_callback()

    async def async_start(self) -> None:
        """Start polling the display settings."""
        if self._unsub is not None:
            return
        self._unsub = async_track_time_interval(
            self.hass, self._async_interval, DISPLAY_SCAN_INTERVAL
        )
        await self.async_refresh()

    @callback
    def async_stop(self) -> None:
        """Stop polling the display settings."""
        if self._unsub:
            self._unsub()
            self._unsub = None

    async def _async_interval(self, now) -> None:
        """Refresh the display settings periodically."""
        await self.async_refresh()

    async def async_refresh(self) -> None:
        """Refresh all display settings for this Echo."""
        async with self._refresh_lock:
            values = await asyncio.gather(
                *(
                    async_get_device_setting(
                        self.login, self.device_account_id, setting
                    )
                    for setting in DISPLAY_SETTINGS
                ),
                return_exceptions=True,
            )
            for setting, value in zip(DISPLAY_SETTINGS, values, strict=True):
                if isinstance(value, Exception):
                    _LOGGER.debug(
                        "%s: Unable to read display setting %s: %s",
                        self.serial,
                        setting,
                        value,
                    )
                    continue
                self._values[setting] = value
            self._async_notify()

    async def async_set(self, setting: str, value: Any) -> bool:
        """Set one display setting and update the cached value."""
        async with self._refresh_lock:
            try:
                success = await async_set_device_setting(
                    self.login, self.device_account_id, setting, value
                )
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning("Unable to set %s: %s", setting, err)
                success = False
            if success:
                self._values[setting] = value
                self._async_notify()
                return True

        # Do not call async_refresh while holding the lock: it is not re-entrant.
        await self.async_refresh()
        return False


async def async_get_display_state(
    hass: HomeAssistant,
    account_dict: dict[str, Any],
    login: AlexaLogin,
    device: dict[str, Any],
    client,
) -> DisplayState:
    """Return (creating if needed) the shared display state for an Echo."""
    states = account_dict.setdefault("display_states", {})
    state = states.get(device["serialNumber"])
    if state is None:
        state = DisplayState(hass, login, device)
        state.client = client
        states[device["serialNumber"]] = state
    return state


def _device_info(client) -> dict[str, Any]:
    """Return the device registry information for display entities."""
    return {"identifiers": {(DOMAIN, client.unique_id)}}


class AlexaDisplayPowerSwitch(SwitchEntity):
    """Turn the Echo display on or off."""

    _attr_has_entity_name = True
    _attr_translation_key = "display_power"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:monitor"

    def __init__(self, state: DisplayState) -> None:
        """Initialize the display power switch."""
        self._state = state
        self._attr_unique_id = f"{state.client.unique_id}_display_power"
        self._attr_device_info = _device_info(state.client)

    @property
    def is_on(self) -> bool | None:
        """Return whether the display is on."""
        value = self._state.value(SETTING_DISPLAY_POWER)
        return None if value is None else value == "ON"

    @property
    def available(self) -> bool:
        """Return whether the display power setting is available."""
        return self._state.value(SETTING_DISPLAY_POWER) is not None

    async def async_added_to_hass(self) -> None:
        """Subscribe to display state updates."""
        self.async_on_remove(self._state.async_add_listener(self.async_write_ha_state))
        await self._state.async_start()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the display on."""
        if not await self._state.async_set(SETTING_DISPLAY_POWER, "ON"):
            raise HomeAssistantError("Unable to turn the Echo display on")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the display off."""
        if not await self._state.async_set(SETTING_DISPLAY_POWER, "OFF"):
            raise HomeAssistantError("Unable to turn the Echo display off")


class AlexaAdaptiveBrightnessSwitch(SwitchEntity):
    """Enable or disable adaptive brightness on an Echo display."""

    _attr_has_entity_name = True
    _attr_translation_key = "adaptive_brightness"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:brightness-auto"

    def __init__(self, state: DisplayState) -> None:
        """Initialize the adaptive brightness switch."""
        self._state = state
        self._attr_unique_id = f"{state.client.unique_id}_adaptive_brightness"
        self._attr_device_info = _device_info(state.client)

    @property
    def is_on(self) -> bool | None:
        """Return whether adaptive brightness is enabled."""
        value = self._state.value(SETTING_ADAPTIVE_BRIGHTNESS)
        return None if value is None else value == "ON"

    @property
    def available(self) -> bool:
        """Return whether the adaptive brightness setting is available."""
        return self._state.value(SETTING_ADAPTIVE_BRIGHTNESS) is not None

    async def async_added_to_hass(self) -> None:
        """Subscribe to display state updates."""
        self.async_on_remove(self._state.async_add_listener(self.async_write_ha_state))
        await self._state.async_start()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable adaptive brightness."""
        if not await self._state.async_set(SETTING_ADAPTIVE_BRIGHTNESS, "ON"):
            raise HomeAssistantError("Unable to enable adaptive brightness")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable adaptive brightness."""
        if not await self._state.async_set(SETTING_ADAPTIVE_BRIGHTNESS, "OFF"):
            raise HomeAssistantError("Unable to disable adaptive brightness")


class AlexaDisplayBrightness(NumberEntity):
    """Set the brightness of an Echo display."""

    _attr_has_entity_name = True
    _attr_translation_key = "display_brightness"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:brightness-6"
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, state: DisplayState) -> None:
        """Initialize the display brightness number."""
        self._state = state
        self._attr_unique_id = f"{state.client.unique_id}_display_brightness"
        self._attr_device_info = _device_info(state.client)

    @property
    def native_value(self) -> float | None:
        """Return the current brightness."""
        value = self._state.value(SETTING_BRIGHTNESS)
        return None if value is None else float(value)

    @property
    def available(self) -> bool:
        """Return whether the brightness setting is available."""
        return self._state.value(SETTING_BRIGHTNESS) is not None

    async def async_added_to_hass(self) -> None:
        """Subscribe to display state updates."""
        self.async_on_remove(self._state.async_add_listener(self.async_write_ha_state))
        await self._state.async_start()

    async def async_set_native_value(self, value: float) -> None:
        """Set the display brightness."""
        if not await self._state.async_set(SETTING_BRIGHTNESS, int(value)):
            raise HomeAssistantError("Unable to set the Echo display brightness")
