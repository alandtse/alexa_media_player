"""
Echo display controls.

SPDX-License-Identifier: Apache-2.0

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

from alexapy import AlexaAPI, AlexaLogin, AlexapyLoginError, hide_serial
from homeassistant.components.number import NumberEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.event import async_call_later, async_track_time_interval

from .const import DATA_ALEXAMEDIA, DOMAIN
from .helpers import report_relogin_required

_LOGGER = logging.getLogger(__name__)

DISPLAY_SCAN_INTERVAL = timedelta(minutes=15)
DISPLAY_REFRESH_TIMEOUT = 30
# AlexaPy retries a throttled request once after 10-63 seconds (10-13s for a
# rate-limit body, up to 30-63s for "Too many requests"). Keep the outer bound
# above that window so the library's own retry can finish.
DISPLAY_PROBE_TIMEOUT = 70
DISPLAY_PROBE_ATTEMPTS = 2
DISPLAY_PROBE_RETRY_DELAY = 1
DISPLAY_PROBE_RELOAD_DELAY = 15 * 60
DISPLAY_FAILURE_LIMIT = 3
DISPLAY_THROTTLE_WATCH_INTERVAL = 0.05
DISPLAY_PROBE_CONCURRENCY = 3

SETTING_DISPLAY_POWER = "displayPower"
SETTING_BRIGHTNESS = "brightness"
SETTING_ADAPTIVE_BRIGHTNESS = "adaptiveBrightness"

DISPLAY_SETTINGS = (
    SETTING_DISPLAY_POWER,
    SETTING_BRIGHTNESS,
    SETTING_ADAPTIVE_BRIGHTNESS,
)


def can_probe_display(device: dict[str, Any]) -> bool:
    """Return whether the device has the identity needed to probe settings."""
    serial = device.get("serialNumber")
    account_id = device.get("deviceAccountId")
    return (
        isinstance(serial, str)
        and bool(serial)
        and isinstance(account_id, str)
        and bool(account_id)
    )


def _normalize_setting_value(setting: str, value: Any) -> Any | None:
    """Return a validated setting value, or None when the payload is malformed."""
    if setting == SETTING_BRIGHTNESS:
        if isinstance(value, bool):
            return None
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            return None
        if not 0 <= number <= 100:
            return None
        return int(number) if number.is_integer() else number
    if setting in (SETTING_DISPLAY_POWER, SETTING_ADAPTIVE_BRIGHTNESS):
        return value if value in ("ON", "OFF") else None
    return None


async def async_get_device_setting(
    login: AlexaLogin, device_account_id: str, setting: str
) -> tuple[int, Any]:
    """Read one setting through the status-aware alexapy API.

    The API returns ``(0, None)`` when the device has no account id, ``400``
    for an explicitly unsupported setting and the HTTP status for anything
    else, so callers can keep transient failures retryable.
    """
    if not device_account_id:
        return 0, None
    return await AlexaAPI.get_device_setting(login, device_account_id, setting)


async def async_set_device_setting(
    login: AlexaLogin, device_account_id: str, setting: str, value: Any
) -> bool:
    """Write one device setting and return whether Amazon accepted it."""
    if not device_account_id:
        return False
    return await AlexaAPI.set_device_setting(login, device_account_id, setting, value)


async def _capture_request_flag(login: AlexaLogin, awaitable) -> tuple[Any, bool]:
    """Capture the shared throttle flag in the request task at completion."""
    try:
        result = await awaitable
    except Exception as err:  # noqa: BLE001
        return err, getattr(login, "_rate_retry_inflight", False) is True
    return result, getattr(login, "_rate_retry_inflight", False) is True


async def _await_with_throttle_watch(login: AlexaLogin, awaitable) -> tuple[Any, bool]:
    """Await one request and report whether throttling overlapped it.

    AlexaPy clears ``_rate_retry_inflight`` in a ``finally`` block before the
    request returns, so a request that was throttled and retried internally can
    look unthrottled when checked only before and after the call. Sample the
    flag while the request is still running instead.

    Exceptions are returned instead of raised so the caller can keep the
    throttle observation together with the failed result.
    """
    request = asyncio.ensure_future(_capture_request_flag(login, awaitable))
    throttled = False
    try:
        while not request.done():
            if getattr(login, "_rate_retry_inflight", False) is True:
                throttled = True
            await asyncio.wait({request}, timeout=DISPLAY_THROTTLE_WATCH_INTERVAL)
    except BaseException:
        request.cancel()
        await asyncio.gather(request, return_exceptions=True)
        raise
    result, response_throttled = request.result()
    # AlexaPy exposes one shared throttle flag, so a 400 that overlaps any
    # concurrent retry is treated as temporary. This can delay a genuine
    # unsupported setting, but it must never be cached as unsupported. Per-
    # response attribution would require an AlexaPy API change.
    throttled = (
        throttled
        or response_throttled
        or getattr(login, "_rate_retry_inflight", False) is True
    )
    return result, throttled


def _display_relogin_reported(hass: HomeAssistant) -> set:
    """Return the accounts already reported for display reauthentication."""
    data = getattr(hass, "data", None)
    if not isinstance(data, dict):
        return set()
    return data.setdefault(DATA_ALEXAMEDIA, {}).setdefault(
        "display_relogin_reported", set()
    )


def _report_display_relogin(hass: HomeAssistant, login: AlexaLogin) -> None:
    """Report a display authentication failure once per account episode."""
    email = getattr(login, "email", None)
    if not email:
        return
    reported = _display_relogin_reported(hass)
    if email in reported:
        return
    if report_relogin_required(hass, login, email, require_status=False):
        reported.add(email)


def _clear_display_relogin(hass: HomeAssistant, login: AlexaLogin) -> None:
    """Allow a future failure to report once authentication recovers."""
    email = getattr(login, "email", None)
    if email:
        _display_relogin_reported(hass).discard(email)


def _auth_recovered(login: AlexaLogin) -> bool:
    """Return whether AlexaPy reports a successful account login."""
    status = getattr(login, "status", None)
    return isinstance(status, dict) and status.get("login_successful") is True


async def async_probe_display_settings(
    hass: HomeAssistant, login: AlexaLogin, device: dict[str, Any]
) -> tuple[dict[str, Any], bool]:
    """Return the settings the device reports and whether a probe failed.

    A 400 is an explicit unsupported response unless AlexaPy reports a
    concurrent throttle. A transport failure is reported separately so a
    temporary network problem is not cached as "device does not support this".
    """
    serial = device.get("serialNumber", "")
    device_account_id = device.get("deviceAccountId", "")
    if not device_account_id:
        return {}, False

    async def _probe(setting: str) -> tuple[Any, bool]:
        last_error: Exception | None = None
        throttled = False
        for attempt in range(DISPLAY_PROBE_ATTEMPTS):
            result, throttled = await _await_with_throttle_watch(
                login, async_get_device_setting(login, device_account_id, setting)
            )
            if not isinstance(result, Exception):
                status = result[0]
                if status == 400 and throttled and attempt + 1 < DISPLAY_PROBE_ATTEMPTS:
                    # A 400 that overlapped another request's backoff is
                    # ambiguous. Wait for the shared backoff to clear, then ask
                    # again instead of discarding the settings that succeeded.
                    loop = asyncio.get_running_loop()
                    deadline = loop.time() + DISPLAY_PROBE_TIMEOUT
                    while (
                        getattr(login, "_rate_retry_inflight", False) is True
                        and loop.time() < deadline
                    ):
                        await asyncio.sleep(DISPLAY_THROTTLE_WATCH_INTERVAL)
                    await asyncio.sleep(DISPLAY_PROBE_RETRY_DELAY)
                    continue
                if status not in (200, 400) and attempt + 1 < DISPLAY_PROBE_ATTEMPTS:
                    # 429, 5xx and other temporary statuses are retried within
                    # the outer probe deadline.
                    await asyncio.sleep(DISPLAY_PROBE_RETRY_DELAY)
                    continue
                return result, throttled
            if isinstance(result, AlexapyLoginError) and not _auth_recovered(login):
                _report_display_relogin(hass, login)
            last_error = result
            if attempt + 1 < DISPLAY_PROBE_ATTEMPTS:
                await asyncio.sleep(DISPLAY_PROBE_RETRY_DELAY)
        return last_error, throttled

    try:
        results = await asyncio.wait_for(
            asyncio.gather(*(_probe(setting) for setting in DISPLAY_SETTINGS)),
            timeout=DISPLAY_PROBE_TIMEOUT,
        )
    except asyncio.TimeoutError:
        _LOGGER.debug("%s: Display probe timed out", hide_serial(serial))
        return {}, True
    if any(
        isinstance(result, AlexapyLoginError) for result, _ in results
    ) and not _auth_recovered(login):
        _report_display_relogin(hass, login)
    elif _auth_recovered(login):
        _clear_display_relogin(hass, login)

    supported: dict[str, Any] = {}
    failed = False
    for setting, (result, throttled) in zip(DISPLAY_SETTINGS, results, strict=True):
        if isinstance(result, Exception):
            failed = True
            _LOGGER.debug(
                "%s: Unable to probe display setting %s: %s",
                hide_serial(serial),
                setting,
                result,
            )
            continue
        status, setting_value = result
        if status == 400 and throttled:
            failed = True
            _LOGGER.debug(
                "%s: Throttled while probing display setting %s",
                hide_serial(serial),
                setting,
            )
            continue
        if status == 400:
            continue
        if status == 200 and setting_value is not None:
            normalized = _normalize_setting_value(setting, setting_value)
            if normalized is not None:
                supported[setting] = normalized
                continue
        failed = True
        _LOGGER.debug(
            "%s: Temporary or malformed HTTP %s probing display setting %s",
            hide_serial(serial),
            status,
            setting,
        )
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
        self._stopped = False
        self._refresh_tasks: set[asyncio.Task] = set()

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
        if self._stopped or self._unsub is not None:
            return
        self._unsub = async_track_time_interval(
            self.hass, self._async_interval, DISPLAY_SCAN_INTERVAL
        )
        if not self._probed:
            await self.async_refresh()

    @callback
    def async_stop(self) -> None:
        """Stop polling the display settings."""
        self._stopped = True
        try:
            current = asyncio.current_task()
        except RuntimeError:
            current = None
        for task in tuple(self._refresh_tasks):
            if not task.done() and task is not current:
                task.cancel()
        if self._unsub:
            self._unsub()
            self._unsub = None

    async def _async_interval(self, now) -> None:
        """Refresh the display settings periodically."""
        await self._tracked_refresh()

    async def _tracked_refresh(self) -> None:
        """Run a refresh that unload can cancel."""
        task = asyncio.current_task()
        self._refresh_tasks.add(task)
        try:
            await self.async_refresh()
        finally:
            self._refresh_tasks.discard(task)

    async def async_refresh(self) -> None:
        """Refresh all supported display settings for this Echo."""
        if self._stopped or not self._supported:
            return
        async with self._refresh_lock:
            if self._stopped:
                return
            settings = tuple(sorted(self._supported))
            values = await asyncio.gather(
                *(self._read_setting(setting) for setting in settings),
                return_exceptions=True,
            )
            if self._stopped:
                # Unload or removal retired this state while the reads were in
                # flight; do not report relogin or update entities afterwards.
                return
            results = [
                value if isinstance(value, tuple) else (value, False)
                for value in values
            ]
            if any(
                isinstance(result, AlexapyLoginError) for result, _ in results
            ) and not _auth_recovered(self.login):
                _report_display_relogin(self.hass, self.login)
            elif _auth_recovered(self.login):
                _clear_display_relogin(self.hass, self.login)
            for setting, (result, throttled) in zip(settings, results, strict=True):
                if isinstance(result, Exception):
                    self._failures[setting] = 0
                    _LOGGER.debug(
                        "%s: Unable to read display setting %s: %s",
                        hide_serial(self.serial),
                        setting,
                        result,
                    )
                    continue
                status, setting_value = result
                if status == 400 and throttled:
                    self._failures[setting] = 0
                    _LOGGER.debug(
                        "%s: Throttled reading display setting %s; keeping %s",
                        hide_serial(self.serial),
                        setting,
                        self._values.get(setting),
                    )
                    continue
                if status == 400:
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
                if status == 200 and setting_value is not None:
                    normalized = _normalize_setting_value(setting, setting_value)
                    if normalized is not None:
                        self._failures[setting] = 0
                        self._values[setting] = normalized
                        continue
                self._failures[setting] = 0
                _LOGGER.debug(
                    "%s: Temporary or malformed HTTP %s reading display setting "
                    "%s; keeping %s",
                    hide_serial(self.serial),
                    status,
                    setting,
                    self._values.get(setting),
                )
            if not self._supported:
                self.async_stop()
            self._async_notify()

    async def _read_setting(self, setting: str) -> tuple[Any, bool]:
        """Read one setting and capture whether a throttle retry overlapped it."""
        return await _await_with_throttle_watch(
            self.login,
            async_get_device_setting(self.login, self.device_account_id, setting),
        )

    async def async_set(self, setting: str, value: Any) -> bool:
        """Set one supported display setting and update the cached value."""
        if self._stopped:
            return False
        async with self._refresh_lock:
            if self._stopped or setting not in self._supported:
                return False
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
                if not self._stopped:
                    self._values[setting] = value
                    self._async_notify()
                return True

        # Do not call async_refresh while holding the lock: it is not re-entrant.
        try:
            await asyncio.wait_for(
                self._tracked_refresh(), timeout=DISPLAY_REFRESH_TIMEOUT
            )
        except asyncio.TimeoutError:
            _LOGGER.warning(
                "%s: Timed out refreshing display after failed %s write",
                hide_serial(self.serial),
                setting,
            )
        return False


def _display_entry_state(
    hass: HomeAssistant, account_dict: dict[str, Any]
) -> dict | None:
    """Return entry-scoped display recovery state that survives reloads."""
    entry = account_dict.get("config_entry")
    entry_id = getattr(entry, "entry_id", None)
    if entry_id is None:
        return None
    data = getattr(hass, "data", None)
    if not isinstance(data, dict):
        return None
    states = data.setdefault(DATA_ALEXAMEDIA, {}).setdefault("display_entry_states", {})
    return states.setdefault(entry_id, {})


def _display_pending(hass: HomeAssistant, account_dict: dict[str, Any]) -> set:
    """Return the serials whose display probe still needs recovery."""
    state = _display_entry_state(hass, account_dict)
    if state is not None:
        pending = state.setdefault("pending", set())
    else:
        pending = account_dict.setdefault("display_probe_pending", set())
    # Drop serials for devices that no longer exist so a stale entry cannot
    # keep the reload budget consumed forever. Only prune against a real
    # inventory; partial test or setup dicts have no device map.
    devices = account_dict.get("devices", {})
    media_players = devices.get("media_player") if isinstance(devices, dict) else None
    if isinstance(media_players, dict):
        known = {
            device.get("serialNumber")
            for device in media_players.values()
            if isinstance(device, dict) and can_probe_display(device)
        }
        pruned = pending - known
        pending.intersection_update(known)
        if pruned and not pending:
            # Every unresolved device disappeared. The previous attempt did not
            # run against the current inventory, so release its budget.
            entry = account_dict.get("config_entry")
            key = getattr(entry, "entry_id", None)
            if key is not None:
                _display_reload_budget(hass, account_dict).pop(key, None)
    return pending


def _display_reload_budget(hass: HomeAssistant, account_dict: dict[str, Any]) -> dict:
    """Return the automatic display reload budget for this Home Assistant run."""
    data = getattr(hass, "data", None)
    if not isinstance(data, dict):
        return account_dict.setdefault("_display_reload_budget", {})
    return data.setdefault(DATA_ALEXAMEDIA, {}).setdefault("display_reload_budget", {})


def _cancel_display_reload(account_dict: dict[str, Any]) -> None:
    """Cancel a pending display reload timer, if any."""
    unsub = account_dict.pop("display_reload_unsub", None)
    if unsub:
        unsub()


def _cancel_display_reload_if_idle(
    hass: HomeAssistant, account_dict: dict[str, Any]
) -> None:
    """Cancel the timer once no display probe still needs recovery."""
    if _display_pending(hass, account_dict):
        return
    _cancel_display_reload(account_dict)
    _clear_display_reload_budget(hass, account_dict)


def _clear_display_reload_budget(
    hass: HomeAssistant, account_dict: dict[str, Any]
) -> None:
    """Allow one future automatic retry once every device has recovered."""
    if _display_pending(hass, account_dict):
        return
    entry = account_dict.get("config_entry")
    key = getattr(entry, "entry_id", None)
    if key is None:
        return
    _display_reload_budget(hass, account_dict).pop(key, None)


@callback
def _schedule_display_reload(hass: HomeAssistant, account_dict: dict[str, Any]) -> None:
    """Reload the entry later so a failed display probe is retried."""
    if account_dict.get("display_reload_unsub") is not None:
        return
    if not _display_pending(hass, account_dict):
        return
    entry = account_dict.get("config_entry")
    if entry is None:
        return
    key = getattr(entry, "entry_id", None)
    if key is None:
        return
    budget = _display_reload_budget(hass, account_dict)
    if budget.get(key, 0) >= 1:
        _LOGGER.debug(
            "%s: Automatic display reload already attempted; waiting for a "
            "manual reload",
            hide_serial(str(key)),
        )
        return
    budget[key] = budget.get(key, 0) + 1

    @callback
    def _reload(_now) -> None:
        account_dict["display_reload_unsub"] = None
        reload_entry = hass.config_entries.async_get_entry(entry.entry_id)
        if reload_entry is None:
            return
        if getattr(reload_entry, "disabled_by", None) is not None:
            # Home Assistant will not set up a disabled entry, so do not spend
            # the only automatic retry on it.
            _display_reload_budget(hass, account_dict).pop(key, None)
            return
        hass.config_entries.async_schedule_reload(entry.entry_id)

    account_dict["display_reload_unsub"] = async_call_later(
        hass, DISPLAY_PROBE_RELOAD_DELAY, _reload
    )


async def _async_ensure_display_state(
    hass: HomeAssistant,
    account_dict: dict[str, Any],
    login: AlexaLogin,
    device: dict[str, Any],
    client,
) -> DisplayState | None:
    """Probe one device and record the outcome for its serial."""
    states = account_dict.setdefault("display_states", {})
    unsupported = account_dict.setdefault("display_unsupported", set())
    failed_serials = account_dict.setdefault("display_probe_failed", set())
    pending = _display_pending(hass, account_dict)
    serial = device["serialNumber"]

    semaphore = account_dict.get("display_probe_semaphore")
    if semaphore is None:
        semaphore = asyncio.Semaphore(DISPLAY_PROBE_CONCURRENCY)
        account_dict["display_probe_semaphore"] = semaphore
    async with semaphore:
        values, failed = await async_probe_display_settings(hass, login, device)
    if failed:
        # Do not commit a partial capability result: the missing setting
        # would never get an entity, and polling only reads supported
        # settings. Reload the entry later to retry the whole probe.
        failed_serials.add(serial)
        pending.add(serial)
        _schedule_display_reload(hass, account_dict)
        _LOGGER.debug(
            "%s: Display settings probe incomplete; retrying on the next setup",
            hide_serial(serial),
        )
        return None
    failed_serials.discard(serial)
    pending.discard(serial)
    _clear_display_reload_budget(hass, account_dict)
    _cancel_display_reload_if_idle(hass, account_dict)
    if not values:
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


async def async_get_display_state(
    hass: HomeAssistant,
    account_dict: dict[str, Any],
    login: AlexaLogin,
    device: dict[str, Any],
    client,
) -> DisplayState | None:
    """Return (creating and probing if needed) the shared display state.

    Platforms set up concurrently, so every caller for the same serial awaits
    one in-flight probe. A failed probe is remembered for the current setup: a
    sibling platform must not retry it, succeed, and cancel the reload that
    repairs the platform which is still missing its entities. The next setup
    attempt clears that memo, even though the account dict survives retries.
    """
    serial = device.get("serialNumber")
    if not serial:
        return None

    states = account_dict.setdefault("display_states", {})
    state = states.get(serial)
    if state is not None:
        # A setup retry can supply a new login/client while reusing the
        # probed state from the previous attempt.
        pending = _display_pending(hass, account_dict)
        pending.discard(serial)
        _cancel_display_reload_if_idle(hass, account_dict)
        state.login = login
        state.client = client
        return state

    if serial in account_dict.setdefault("display_unsupported", set()):
        pending = _display_pending(hass, account_dict)
        pending.discard(serial)
        _cancel_display_reload_if_idle(hass, account_dict)
        return None

    if serial in account_dict.setdefault("display_probe_failed", set()):
        return None

    probes = account_dict.setdefault("display_probes", {})
    probe = probes.get(serial)
    if probe is None:
        probe = asyncio.create_task(
            _async_ensure_display_state(hass, account_dict, login, device, client)
        )
        probes[serial] = probe

        @callback
        def _forget(done, serial=serial, probe=probe) -> None:
            if probes.get(serial) is probe:
                probes.pop(serial, None)

        probe.add_done_callback(_forget)
    return await asyncio.shield(probe)


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
