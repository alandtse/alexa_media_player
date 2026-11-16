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

from alexapy import AlexaAPI, AlexaLogin, hide_serial
from homeassistant.components.number import NumberEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.event import async_track_time_interval

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

DISPLAY_SCAN_INTERVAL = timedelta(minutes=15)
DISPLAY_REFRESH_TIMEOUT = 30
DISPLAY_PROBE_TIMEOUT = 10
DISPLAY_FAILURE_LIMIT = 3

SETTING_DISPLAY_POWER = "displayPower"
SETTING_BRIGHTNESS = "brightness"
SETTING_ADAPTIVE_BRIGHTNESS = "adaptiveBrightness"

DISPLAY_SETTINGS = (
    SETTING_DISPLAY_POWER,
    SETTING_BRIGHTNESS,
    SETTING_ADAPTIVE_BRIGHTNESS,
)


def can_probe_display(device: dict[str, Any]) -> bool:
    """Return whether the device has the identity needed to probe settings.

    There is no reliable model list for this: Amazon keeps adding displays
    (Echo Time, Echo Show 16, Alexa Photo Frame, ...) and the settings are
    capability-gated per device. Every media player with an account id and a
    serial is probed once, and only the settings that return a value become
    entities.
    """
    return bool(device.get("serialNumber") and device.get("deviceAccountId"))


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


async def async_probe_display_settings(
    login: AlexaLogin, device: dict[str, Any]
) -> tuple[dict[str, Any], bool]:
    """Return the settings the device reports and whether a probe failed.

    Amazon rejects unsupported settings with HTTP 400, which alexapy surfaces
    as ``None``. A transport failure is reported separately so a temporary
    network problem is not cached as "device does not support this".
    """
    serial = device.get("serialNumber", "")
    device_account_id = device.get("deviceAccountId", "")
    if not device_account_id:
        return {}, False

    async def _probe(setting: str) -> Any:
        try:
            return await asyncio.wait_for(
                async_get_device_setting(login, device_account_id, setting),
                timeout=DISPLAY_PROBE_TIMEOUT,
            )
        except Exception as err:  # noqa: BLE001
            return err

    results = await asyncio.gather(*(_probe(setting) for setting in DISPLAY_SETTINGS))

    supported: dict[str, Any] = {}
    failed = False
    for setting, value in zip(DISPLAY_SETTINGS, results, strict=True):
        if isinstance(value, Exception):
            failed = True
            _LOGGER.debug(
                "%s: Unable to probe display setting %s: %s",
                hide_serial(serial),
                setting,
                value,
            )
            continue
        if value is not None:
            supported[setting] = value
    return supported, failed


class DisplayState:
    """Shared display settings for one Echo."""

    def __init__(
        self,
        hass: HomeAssistant,
        login: AlexaLogin,
        device: dict[str, Any],
        supported: dict[str, Any] | None = None,
        *,
        probed: bool = False,
    ) -> None:
        """Initialize the display state."""
        self.hass = hass
        self.login = login
        self.device = device
        self.serial = device["serialNumber"]
        self.device_account_id = device.get("deviceAccountId", "")
        self._values: dict[str, Any] = {setting: None for setting in DISPLAY_SETTINGS}
        self._values.update(supported or {})
        self._supported: set[str] = set(
            DISPLAY_SETTINGS if supported is None else supported
        )
        self._failures = dict.fromkeys(DISPLAY_SETTINGS, 0)
        self._listeners: list = []
        self._refresh_lock = asyncio.Lock()
        self._unsub = None
        self._probed = probed

    @property
    def client(self):
        """Return the media player client, if it is registered."""
        return self._client

    @client.setter
    def client(self, value) -> None:
        """Store the media player client for entity identity."""
        self._client = value

    def supports(self, setting: str) -> bool:
        """Return whether the device exposed this setting during the probe."""
        return setting in self._supported

    def available(self, setting: str) -> bool:
        """Return whether the setting has a current, supported value."""
        return setting in self._supported and self._values.get(setting) is not None

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
        if not self._probed:
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
        """Refresh all supported display settings for this Echo."""
        if not self._supported:
            return
        async with self._refresh_lock:
            settings = tuple(sorted(self._supported))
            values = await asyncio.gather(
                *(self._read_setting(setting) for setting in settings),
                return_exceptions=True,
            )
            for setting, value in zip(settings, values, strict=True):
                if isinstance(value, Exception):
                    _LOGGER.debug(
                        "%s: Unable to read display setting %s: %s",
                        hide_serial(self.serial),
                        setting,
                        value,
                    )
                    continue
                if value is None:
                    self._failures[setting] += 1
                    if self._failures[setting] >= DISPLAY_FAILURE_LIMIT:
                        _LOGGER.debug(
                            "%s: Display setting %s is no longer supported; "
                            "stopping its refresh",
                            hide_serial(self.serial),
                            setting,
                        )
                        self._supported.discard(setting)
                        self._values[setting] = None
                    continue
                self._failures[setting] = 0
                self._values[setting] = value
            if not self._supported:
                self.async_stop()
            self._async_notify()

    async def _read_setting(self, setting: str) -> Any:
        """Read one setting without letting one failure cancel the others."""
        return await async_get_device_setting(
            self.login, self.device_account_id, setting
        )

    async def async_set(self, setting: str, value: Any) -> bool:
        """Set one supported display setting and update the cached value."""
        if setting not in self._supported:
            return False
        async with self._refresh_lock:
            try:
                success = await async_set_device_setting(
                    self.login, self.device_account_id, setting, value
                )
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning(
                    "%s: Unable to set %s: %s",
                    hide_serial(self.serial),
                    setting,
                    err,
                )
                success = False
            if success:
                self._values[setting] = value
                self._async_notify()
                return True

        # Do not call async_refresh while holding the lock: it is not re-entrant.
        try:
            await asyncio.wait_for(
                self.async_refresh(), timeout=DISPLAY_REFRESH_TIMEOUT
            )
        except asyncio.TimeoutError:
            _LOGGER.warning(
                "%s: Timed out refreshing display after failed %s write",
                hide_serial(self.serial),
                setting,
            )
        return False


async def async_get_display_state(
    hass: HomeAssistant,
    account_dict: dict[str, Any],
    login: AlexaLogin,
    device: dict[str, Any],
    client,
) -> DisplayState | None:
    """Return (creating and probing if needed) the shared display state."""
    states = account_dict.setdefault("display_states", {})
    unsupported = account_dict.setdefault("display_unsupported", set())
    serial = device.get("serialNumber")
    if not serial:
        return None
    if serial in unsupported:
        return None

    locks = account_dict.setdefault("display_locks", {})
    lock = locks.setdefault(serial, asyncio.Lock())
    async with lock:
        state = states.get(serial)
        if state is not None:
            # A setup retry can supply a new login/client while reusing the
            # probed state from the previous attempt.
            state.login = login
            state.client = client
            return state
        if serial in unsupported:
            return None

        values, failed = await async_probe_display_settings(login, device)
        if not values:
            if failed:
                _LOGGER.debug(
                    "%s: Display settings probe failed; will retry on the "
                    "next setup",
                    hide_serial(serial),
                )
            else:
                unsupported.add(serial)
                _LOGGER.debug(
                    "%s: Device does not expose any display settings; "
                    "skipping display controls",
                    hide_serial(serial),
                )
            return None

        state = DisplayState(hass, login, device, supported=values, probed=True)
        state.client = client
        states[serial] = state
        return state


def _device_info(client) -> dict[str, Any]:
    """Return the device registry information for display entities."""
    return {"identifiers": {(DOMAIN, client.unique_id)}}


class AlexaDisplayPowerSwitch(SwitchEntity):
    """Turn the Echo display on or off."""

    _attr_should_poll = False
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
        return self._state.available(SETTING_DISPLAY_POWER)

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

    _attr_should_poll = False
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
        return self._state.available(SETTING_ADAPTIVE_BRIGHTNESS)

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

    _attr_should_poll = False
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
        return self._state.available(SETTING_BRIGHTNESS)

    async def async_added_to_hass(self) -> None:
        """Subscribe to display state updates."""
        self.async_on_remove(self._state.async_add_listener(self.async_write_ha_state))
        await self._state.async_start()

    async def async_set_native_value(self, value: float) -> None:
        """Set the display brightness."""
        if not await self._state.async_set(SETTING_BRIGHTNESS, int(value)):
            raise HomeAssistantError("Unable to set the Echo display brightness")
