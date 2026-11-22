"""Tests for Echo display controls."""

import asyncio
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, MagicMock, patch

from alexapy import AlexaAPI, AlexapyLoginError, hide_serial
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
import pytest

from custom_components.alexa_media.const import DATA_ALEXAMEDIA
from custom_components.alexa_media.display import (
    DISPLAY_FAILURE_LIMIT,
    DISPLAY_PROBE_CONCURRENCY,
    DISPLAY_SETTINGS,
    SETTING_ADAPTIVE_BRIGHTNESS,
    SETTING_BRIGHTNESS,
    SETTING_DISPLAY_POWER,
    AlexaAdaptiveBrightnessSwitch,
    AlexaDisplayBrightness,
    AlexaDisplayPowerSwitch,
    DisplayState,
    _await_with_throttle_watch,
    _cancel_display_reload_if_idle,
    _clear_display_reload_budget,
    _display_pending,
    _normalize_setting_value,
    _report_display_relogin,
    _schedule_display_reload,
    async_get_device_setting,
    async_get_display_state,
    async_probe_display_settings,
    async_set_device_setting,
    can_probe_display,
)

EMAIL = "test@example.com"  # noqa: S105
SERIAL = "G090XXXXXXXXXXXX"
SHOW_TYPE = "A1XWJRHALS1REP"  # Echo Show 5 (Gen2)
SHOW_8_GEN2 = "A15996VY63BQ2D"  # Echo Show 8 (Gen2)
SHOW_15_GEN1 = "A1EIANJ7PNB0Q7"  # Echo Show 15 (Gen1)
SHOW_15_GEN2 = "AQ24620N8QD5Q"  # Echo Show 15 (Gen2)
DOT_CLOCK_TYPE = "A2H4LV5GIZ1JFT"  # Echo Dot Clock (Gen4)
DOT_TYPE = "A3S5BH2HU6VAYF"  # Echo Dot (Gen2)
UNKNOWN_TYPE = "A0UNKNOWNMODEL"  # Any model not in MODEL_IDS


def _device(device_type: str = SHOW_TYPE) -> dict:
    return {
        "serialNumber": SERIAL,
        "deviceType": device_type,
        "deviceAccountId": "account-id",
    }


def _state() -> DisplayState:
    state = DisplayState(MagicMock(), MagicMock(), _device())
    state.client = MagicMock(unique_id=SERIAL)
    return state


def test_can_probe_display_requires_identity():
    """Every media player with an id and serial is a probe candidate."""
    assert can_probe_display(_device())
    assert can_probe_display(_device(DOT_TYPE))
    assert can_probe_display(_device(UNKNOWN_TYPE))
    assert not can_probe_display({"deviceType": UNKNOWN_TYPE})
    assert not can_probe_display({"serialNumber": SERIAL})
    assert not can_probe_display({})


@pytest.mark.asyncio
async def test_get_device_setting_without_account_id():
    """A device without an account id is never queried."""
    with patch.object(AlexaAPI, "get_device_setting", AsyncMock()) as get:
        assert await async_get_device_setting(
            MagicMock(), "", SETTING_DISPLAY_POWER
        ) == (0, None)
    get.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_device_setting_delegates_to_alexapy():
    """The display layer uses the status-aware alexapy API."""
    login = MagicMock()
    with patch.object(
        AlexaAPI, "get_device_setting", AsyncMock(return_value=(200, "ON"))
    ) as get:
        assert await async_get_device_setting(
            login, "account-id", SETTING_DISPLAY_POWER
        ) == (200, "ON")
    get.assert_awaited_once_with(login, "account-id", SETTING_DISPLAY_POWER)


@pytest.mark.asyncio
async def test_set_device_setting_without_account_id():
    """A device without an account id is never written to."""
    with patch.object(AlexaAPI, "set_device_setting", AsyncMock()) as set_setting:
        assert not await async_set_device_setting(
            MagicMock(), "", SETTING_BRIGHTNESS, 50
        )
    set_setting.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_device_setting_delegates_to_alexapy():
    """The display layer writes through the alexapy API."""
    login = MagicMock()
    with patch.object(
        AlexaAPI, "set_device_setting", AsyncMock(return_value=True)
    ) as set_setting:
        assert await async_set_device_setting(
            login, "account-id", SETTING_BRIGHTNESS, 65
        )
    set_setting.assert_awaited_once_with(login, "account-id", SETTING_BRIGHTNESS, 65)


@pytest.mark.asyncio
async def test_probe_display_settings_keeps_supported_values():
    """Probing keeps every setting that returns a value."""

    async def _get(_login, _account_id, setting):
        return (
            200,
            {
                SETTING_DISPLAY_POWER: "ON",
                SETTING_BRIGHTNESS: 42,
                SETTING_ADAPTIVE_BRIGHTNESS: "OFF",
            }[setting],
        )

    with patch(
        "custom_components.alexa_media.display.async_get_device_setting",
        side_effect=_get,
    ):
        supported, failed = await async_probe_display_settings(
            MagicMock(), MagicMock(), _device()
        )

    assert supported == {
        SETTING_DISPLAY_POWER: "ON",
        SETTING_BRIGHTNESS: 42,
        SETTING_ADAPTIVE_BRIGHTNESS: "OFF",
    }
    assert not failed


@pytest.mark.asyncio
async def test_probe_display_settings_skips_unsupported_and_errors():
    """Unsupported settings are omitted and transport errors are flagged."""

    async def _get(_login, _account_id, setting):
        if setting == SETTING_DISPLAY_POWER:
            return 200, "ON"
        if setting == SETTING_BRIGHTNESS:
            raise RuntimeError("network down")
        return 400, None

    with patch(
        "custom_components.alexa_media.display.async_get_device_setting",
        side_effect=_get,
    ):
        supported, failed = await async_probe_display_settings(
            MagicMock(), MagicMock(), _device()
        )

    assert supported == {SETTING_DISPLAY_POWER: "ON"}
    assert failed


@pytest.mark.asyncio
async def test_probe_display_settings_flags_temporary_http_failure():
    """A 5xx is not treated as an unsupported setting."""

    async def _get(_login, _account_id, setting):
        if setting == SETTING_BRIGHTNESS:
            return 503, None
        return 200, "ON"

    with patch(
        "custom_components.alexa_media.display.async_get_device_setting",
        side_effect=_get,
    ):
        supported, failed = await async_probe_display_settings(
            MagicMock(), MagicMock(), _device()
        )

    assert supported == {
        SETTING_DISPLAY_POWER: "ON",
        SETTING_ADAPTIVE_BRIGHTNESS: "ON",
    }
    assert failed


@pytest.mark.asyncio
async def test_probe_display_settings_retries_transport_errors():
    """A failed probe attempt is retried before reporting a failure."""
    attempts = dict.fromkeys(DISPLAY_SETTINGS, 0)

    async def _get(_login, _account_id, setting):
        attempts[setting] += 1
        if setting == SETTING_DISPLAY_POWER and attempts[setting] == 1:
            raise RuntimeError("network down")
        return (
            200,
            {
                SETTING_DISPLAY_POWER: "ON",
                SETTING_BRIGHTNESS: 42,
                SETTING_ADAPTIVE_BRIGHTNESS: "OFF",
            }[setting],
        )

    with (
        patch(
            "custom_components.alexa_media.display.async_get_device_setting",
            side_effect=_get,
        ),
        patch("custom_components.alexa_media.display.DISPLAY_PROBE_RETRY_DELAY", 0),
    ):
        supported, failed = await async_probe_display_settings(
            MagicMock(), MagicMock(), _device()
        )

    assert not failed
    assert supported == {
        SETTING_DISPLAY_POWER: "ON",
        SETTING_BRIGHTNESS: 42,
        SETTING_ADAPTIVE_BRIGHTNESS: "OFF",
    }
    assert attempts[SETTING_DISPLAY_POWER] == 2


@pytest.mark.asyncio
async def test_probe_display_settings_without_account_id():
    """A device without an account id is never probed."""
    with patch(
        "custom_components.alexa_media.display.async_get_device_setting",
        new_callable=AsyncMock,
    ) as getter:
        supported, failed = await async_probe_display_settings(
            MagicMock(), MagicMock(), {"serialNumber": SERIAL}
        )

    assert supported == {}
    assert not failed
    getter.assert_not_awaited()


@pytest.mark.asyncio
async def test_display_state_refresh_and_notify():
    """Refreshing loads all settings and notifies listeners."""
    state = _state()
    listener = MagicMock()
    state.async_add_listener(listener)

    async def _get(_login, _account_id, setting):
        return (
            200,
            {
                SETTING_DISPLAY_POWER: "ON",
                SETTING_BRIGHTNESS: 42,
                SETTING_ADAPTIVE_BRIGHTNESS: "OFF",
            }[setting],
        )

    with patch(
        "custom_components.alexa_media.display.async_get_device_setting",
        side_effect=_get,
    ):
        await state.async_refresh()

    assert state.value(SETTING_DISPLAY_POWER) == "ON"
    assert state.value(SETTING_BRIGHTNESS) == 42
    assert state.value(SETTING_ADAPTIVE_BRIGHTNESS) == "OFF"
    listener.assert_called_once()


@pytest.mark.asyncio
async def test_display_state_refresh_only_polls_supported_settings():
    """A partially supported device only refreshes its supported settings."""
    state = DisplayState(
        MagicMock(),
        MagicMock(),
        _device(),
        supported={SETTING_BRIGHTNESS: 42},
        probed=True,
    )
    state.client = MagicMock(unique_id=SERIAL)
    calls = []

    async def _get(_login, _account_id, setting):
        calls.append(setting)
        return 200, 50

    with patch(
        "custom_components.alexa_media.display.async_get_device_setting",
        side_effect=_get,
    ):
        await state.async_refresh()

    assert calls == [SETTING_BRIGHTNESS]
    assert state.value(SETTING_BRIGHTNESS) == 50
    assert not state.supports(SETTING_DISPLAY_POWER)


@pytest.mark.asyncio
async def test_display_refresh_preserves_values_on_transient_failures():
    """Transient failures keep cached values and entity availability (#3707)."""
    state = DisplayState(
        MagicMock(),
        MagicMock(),
        _device(),
        supported={
            SETTING_DISPLAY_POWER: "ON",
            SETTING_BRIGHTNESS: 40,
            SETTING_ADAPTIVE_BRIGHTNESS: "OFF",
        },
        probed=True,
    )
    state.client = MagicMock(unique_id=SERIAL)
    power = AlexaDisplayPowerSwitch(state)
    adaptive = AlexaAdaptiveBrightnessSwitch(state)
    brightness = AlexaDisplayBrightness(state)

    assert power.available
    assert adaptive.available
    assert brightness.available
    assert brightness.native_value == 40

    async def _transient(_login, _account_id, setting):
        if setting == SETTING_DISPLAY_POWER:
            return 503, None
        if setting == SETTING_BRIGHTNESS:
            raise RuntimeError("network down")
        return 200, None

    with patch(
        "custom_components.alexa_media.display.async_get_device_setting",
        side_effect=_transient,
    ):
        await state.async_refresh()

    assert state.value(SETTING_DISPLAY_POWER) == "ON"
    assert state.value(SETTING_BRIGHTNESS) == 40
    assert state.value(SETTING_ADAPTIVE_BRIGHTNESS) == "OFF"
    assert power.available
    assert adaptive.available
    assert brightness.available
    assert brightness.native_value == 40

    async def _recovered(_login, _account_id, setting):
        return (
            200,
            {
                SETTING_DISPLAY_POWER: "OFF",
                SETTING_BRIGHTNESS: 75,
                SETTING_ADAPTIVE_BRIGHTNESS: "ON",
            }[setting],
        )

    with patch(
        "custom_components.alexa_media.display.async_get_device_setting",
        side_effect=_recovered,
    ):
        await state.async_refresh()

    assert state.value(SETTING_DISPLAY_POWER) == "OFF"
    assert state.value(SETTING_BRIGHTNESS) == 75
    assert state.value(SETTING_ADAPTIVE_BRIGHTNESS) == "ON"
    assert not power.is_on
    assert adaptive.is_on
    assert brightness.native_value == 75
    assert power.available
    assert adaptive.available
    assert brightness.available


@pytest.mark.asyncio
async def test_display_state_drops_setting_after_failures():
    """A setting that keeps failing is marked unsupported and stops polling."""
    state = _state()

    with patch(
        "custom_components.alexa_media.display.async_get_device_setting",
        new_callable=AsyncMock,
        return_value=(400, None),
    ):
        for _ in range(DISPLAY_FAILURE_LIMIT):
            await state.async_refresh()

    assert not state.supports(SETTING_BRIGHTNESS)
    assert not state.available(SETTING_BRIGHTNESS)


@pytest.mark.asyncio
async def test_display_state_400_streak_resets_on_temporary_failure():
    """A 5xx between 400 responses breaks the consecutive-failure streak."""
    state = DisplayState(
        MagicMock(),
        MagicMock(),
        _device(),
        supported={SETTING_BRIGHTNESS: 10},
        probed=True,
    )
    state.client = MagicMock(unique_id=SERIAL)

    with patch(
        "custom_components.alexa_media.display.async_get_device_setting",
        new_callable=AsyncMock,
        side_effect=[(400, None), (503, None), (400, None), (503, None), (400, None)],
    ):
        for _ in range(5):
            await state.async_refresh()

    assert state.supports(SETTING_BRIGHTNESS)


def test_schedule_display_reload_once():
    """Only one reload is scheduled per account until it runs."""
    account_dict = {
        "config_entry": MagicMock(entry_id="entry"),
        "display_probe_pending": {"serial"},
    }
    hass = MagicMock()

    with patch("custom_components.alexa_media.display.async_call_later") as later:
        _schedule_display_reload(hass, account_dict)
        _schedule_display_reload(hass, account_dict)

    later.assert_called_once()
    assert account_dict["display_reload_unsub"] is later.return_value


def test_display_reload_callback_reloads_entry():
    """The scheduled callback reloads the current entry."""
    account_dict = {
        "config_entry": MagicMock(entry_id="entry"),
        "display_probe_pending": {"serial"},
    }
    hass = MagicMock()
    hass.config_entries.async_get_entry.return_value = MagicMock()

    with patch("custom_components.alexa_media.display.async_call_later") as later:
        _schedule_display_reload(hass, account_dict)
        callback = later.call_args.args[2]
        callback(None)

    hass.config_entries.async_schedule_reload.assert_called_once_with("entry")
    assert account_dict["display_reload_unsub"] is None


def test_display_reload_callback_skips_removed_entry():
    """A removed entry is not reloaded by a stale timer."""
    account_dict = {
        "config_entry": MagicMock(entry_id="entry"),
        "display_probe_pending": {"serial"},
    }
    hass = MagicMock()
    hass.config_entries.async_get_entry.return_value = None

    with patch("custom_components.alexa_media.display.async_call_later") as later:
        _schedule_display_reload(hass, account_dict)
        callback = later.call_args.args[2]
        callback(None)

    hass.config_entries.async_schedule_reload.assert_not_called()


@pytest.mark.asyncio
async def test_transient_probe_failure_schedules_reload():
    """A failed probe schedules the entry reload to retry later."""
    account_dict = {
        "display_states": {},
        "config_entry": MagicMock(entry_id="entry"),
    }

    with (
        patch(
            "custom_components.alexa_media.display.async_probe_display_settings",
            new_callable=AsyncMock,
            return_value=({}, True),
        ),
        patch(
            "custom_components.alexa_media.display._schedule_display_reload"
        ) as schedule,
    ):
        state = await async_get_display_state(
            MagicMock(), account_dict, MagicMock(), _device(), MagicMock()
        )

    assert state is None
    schedule.assert_called_once()
    assert account_dict["display_unsupported"] == set()


@pytest.mark.asyncio
async def test_display_state_set_ignores_unsupported_setting():
    """Writing a setting the device never exposed is rejected locally."""
    state = DisplayState(
        MagicMock(),
        MagicMock(),
        _device(),
        supported={SETTING_DISPLAY_POWER: "ON"},
        probed=True,
    )
    state.client = MagicMock(unique_id=SERIAL)

    with patch(
        "custom_components.alexa_media.display.async_set_device_setting",
        new_callable=AsyncMock,
    ) as setter:
        assert not await state.async_set(SETTING_BRIGHTNESS, 50)

    setter.assert_not_awaited()


@pytest.mark.asyncio
async def test_display_state_refresh_logs_read_exception():
    """A failed read is logged while the other settings still refresh."""
    state = DisplayState(
        MagicMock(),
        MagicMock(),
        _device(),
        supported={SETTING_DISPLAY_POWER: "ON", SETTING_BRIGHTNESS: 10},
        probed=True,
    )
    state.client = MagicMock(unique_id=SERIAL)

    async def _get(_login, _account_id, setting):
        if setting == SETTING_DISPLAY_POWER:
            raise RuntimeError("network down")
        return 200, 55

    with (
        patch(
            "custom_components.alexa_media.display.async_get_device_setting",
            side_effect=_get,
        ),
        patch("custom_components.alexa_media.display._LOGGER.debug") as debug,
    ):
        await state.async_refresh()

    assert state.value(SETTING_BRIGHTNESS) == 55
    assert state.value(SETTING_DISPLAY_POWER) == "ON"
    debug.assert_any_call(
        "%s: Unable to read display setting %s: %s",
        hide_serial(SERIAL),
        SETTING_DISPLAY_POWER,
        ANY,
    )


@pytest.mark.asyncio
async def test_display_state_set_times_out_on_refresh():
    """A stuck fallback refresh is bounded and reported."""
    state = _state()
    release = asyncio.Event()

    async def stuck_refresh():
        await release.wait()

    state.async_refresh = stuck_refresh

    with (
        patch(
            "custom_components.alexa_media.display.async_set_device_setting",
            new_callable=AsyncMock,
            return_value=False,
        ),
        patch("custom_components.alexa_media.display.DISPLAY_REFRESH_TIMEOUT", 0.01),
    ):
        assert not await state.async_set(SETTING_DISPLAY_POWER, "OFF")


@pytest.mark.asyncio
async def test_display_state_start_is_idempotent():
    """Starting twice keeps a single interval listener."""
    state = DisplayState(
        MagicMock(),
        MagicMock(),
        _device(),
        supported={SETTING_BRIGHTNESS: 10},
        probed=True,
    )
    state.client = MagicMock(unique_id=SERIAL)

    with patch(
        "custom_components.alexa_media.display.async_track_time_interval"
    ) as track:
        await state.async_start()
        await state.async_start()

    track.assert_called_once()


@pytest.mark.asyncio
async def test_display_state_refresh_without_supported_settings():
    """A state with no supported settings never calls the API."""
    state = DisplayState(
        MagicMock(),
        MagicMock(),
        _device(),
        supported={},
        probed=True,
    )
    state.client = MagicMock(unique_id=SERIAL)

    with patch(
        "custom_components.alexa_media.display.async_get_device_setting",
        new_callable=AsyncMock,
    ) as getter:
        await state.async_refresh()

    getter.assert_not_awaited()


@pytest.mark.asyncio
async def test_display_state_set_updates_cache():
    """Setting a value updates the local cache."""
    state = _state()

    with patch(
        "custom_components.alexa_media.display.async_set_device_setting",
        new_callable=AsyncMock,
        return_value=True,
    ):
        assert await state.async_set(SETTING_DISPLAY_POWER, "OFF")

    assert state.value(SETTING_DISPLAY_POWER) == "OFF"


@pytest.mark.asyncio
async def test_display_state_set_refreshes_on_failure():
    """A failed write falls back to a refresh."""
    state = _state()
    state.async_refresh = AsyncMock()

    with patch(
        "custom_components.alexa_media.display.async_set_device_setting",
        new_callable=AsyncMock,
        return_value=False,
    ):
        assert not await state.async_set(SETTING_DISPLAY_POWER, "OFF")

    state.async_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_display_state_set_refreshes_on_exception():
    """A transport exception is treated as a failed write and refreshed."""
    state = _state()
    state.async_refresh = AsyncMock()

    with patch(
        "custom_components.alexa_media.display.async_set_device_setting",
        new_callable=AsyncMock,
        side_effect=RuntimeError("network down"),
    ):
        assert not await state.async_set(SETTING_DISPLAY_POWER, "OFF")

    state.async_refresh.assert_awaited_once()


def test_display_power_entity():
    """The power switch reflects and changes the cached state."""
    state = _state()
    state._values[SETTING_DISPLAY_POWER] = "ON"
    switch = AlexaDisplayPowerSwitch(state)

    assert switch.is_on
    assert switch.available


@pytest.mark.asyncio
async def test_display_power_entity_set():
    """Turning the display off calls the shared state."""
    state = _state()
    state._values[SETTING_DISPLAY_POWER] = "ON"
    state.async_set = AsyncMock(return_value=True)
    switch = AlexaDisplayPowerSwitch(state)

    await switch.async_turn_off()
    state.async_set.assert_awaited_once_with(SETTING_DISPLAY_POWER, "OFF")


@pytest.mark.asyncio
async def test_display_power_entity_raises_on_failure():
    """A failed display write raises an error."""
    state = _state()
    state._values[SETTING_DISPLAY_POWER] = "ON"
    state.async_set = AsyncMock(return_value=False)
    switch = AlexaDisplayPowerSwitch(state)

    with pytest.raises(HomeAssistantError):
        await switch.async_turn_on()
    with pytest.raises(HomeAssistantError):
        await switch.async_turn_off()


def test_adaptive_brightness_entity():
    """The adaptive brightness switch reflects the cached state."""
    state = _state()
    state._values[SETTING_ADAPTIVE_BRIGHTNESS] = "OFF"
    switch = AlexaAdaptiveBrightnessSwitch(state)

    assert not switch.is_on
    assert switch.available


@pytest.mark.asyncio
async def test_adaptive_brightness_entity_raises_on_failure():
    """A failed adaptive brightness write raises an error."""
    state = _state()
    state._values[SETTING_ADAPTIVE_BRIGHTNESS] = "OFF"
    state.async_set = AsyncMock(return_value=False)
    switch = AlexaAdaptiveBrightnessSwitch(state)

    with pytest.raises(HomeAssistantError):
        await switch.async_turn_on()
    with pytest.raises(HomeAssistantError):
        await switch.async_turn_off()


@pytest.mark.asyncio
async def test_display_brightness_entity_raises_on_failure():
    """A failed brightness write raises an error."""
    state = _state()
    state._values[SETTING_BRIGHTNESS] = 55
    state.async_set = AsyncMock(return_value=False)
    number = AlexaDisplayBrightness(state)

    with pytest.raises(HomeAssistantError):
        await number.async_set_native_value(70)


def test_display_brightness_entity():
    """The brightness number reflects and changes the cached state."""
    state = _state()
    state._values[SETTING_BRIGHTNESS] = 55
    number = AlexaDisplayBrightness(state)

    assert number.native_value == 55
    assert number.available


@pytest.mark.asyncio
async def test_display_brightness_entity_set():
    """Setting brightness writes an integer."""
    state = _state()
    state._values[SETTING_BRIGHTNESS] = 55
    state.async_set = AsyncMock(return_value=True)
    number = AlexaDisplayBrightness(state)

    await number.async_set_native_value(70.0)
    state.async_set.assert_awaited_once_with(SETTING_BRIGHTNESS, 70)


@pytest.mark.asyncio
async def test_switch_setup_creates_display_entities():
    """The switch platform creates display switches for display models."""
    from custom_components.alexa_media.switch import async_setup_platform

    client = MagicMock()
    client.unique_id = SERIAL
    client._login = MagicMock(email=EMAIL)
    account_dict = {
        "devices": {
            "media_player": {
                SERIAL: {
                    "serialNumber": SERIAL,
                    "deviceType": SHOW_TYPE,
                    "deviceFamily": "ECHO_SHOW",
                    "deviceAccountId": "account-id",
                    "capabilities": ["MUSIC_SKILL"],
                }
            },
            "number": {},
            "smart_switch": [],
        },
        "entities": {
            "media_player": {SERIAL: client},
            "switch": {},
            "smart_switch": [],
            "amazon_kids_switch": [],
        },
        "options": {},
        "coordinator": MagicMock(),
        "login_obj": MagicMock(),
    }
    hass = MagicMock()
    hass.config.as_dict.return_value = {"components": set()}
    hass.data = {DATA_ALEXAMEDIA: {"accounts": {EMAIL: account_dict}}}

    add = MagicMock()
    with patch(
        "custom_components.alexa_media.display.async_probe_display_settings",
        new_callable=AsyncMock,
        return_value=(
            {
                SETTING_DISPLAY_POWER: "ON",
                SETTING_ADAPTIVE_BRIGHTNESS: "OFF",
            },
            False,
        ),
    ) as probe:
        await async_setup_platform(hass, {"email": EMAIL}, add)

    probe.assert_awaited_once()
    switches = account_dict["entities"]["switch"][SERIAL]
    assert {"display_power", "adaptive_brightness"} <= set(switches)
    # The display switches are added unfiltered, after the filtered batch.
    display_batch = add.call_args_list[-1].args[0]
    assert {type(switch) for switch in display_batch} == {
        AlexaDisplayPowerSwitch,
        AlexaAdaptiveBrightnessSwitch,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("device_type", [SHOW_8_GEN2, DOT_TYPE])
async def test_switch_setup_skips_unsupported_display(device_type):
    """Any media player that rejects every setting gets no display switches."""
    from custom_components.alexa_media.switch import async_setup_platform

    client = MagicMock()
    client.unique_id = SERIAL
    client._login = MagicMock(email=EMAIL)
    account_dict = {
        "devices": {
            "media_player": {
                SERIAL: {
                    "serialNumber": SERIAL,
                    "deviceType": device_type,
                    "deviceFamily": "ECHO",
                    "deviceAccountId": "account-id",
                    "capabilities": [],
                }
            },
            "number": {},
            "smart_switch": [],
        },
        "entities": {
            "media_player": {SERIAL: client},
            "switch": {},
            "smart_switch": [],
            "amazon_kids_switch": [],
        },
        "options": {},
        "coordinator": MagicMock(),
        "login_obj": MagicMock(),
    }
    hass = MagicMock()
    hass.config.as_dict.return_value = {"components": set()}
    hass.data = {DATA_ALEXAMEDIA: {"accounts": {EMAIL: account_dict}}}

    with (
        patch(
            "custom_components.alexa_media.display.async_probe_display_settings",
            new_callable=AsyncMock,
            return_value=({}, False),
        ) as probe,
        patch(
            "custom_components.alexa_media.switch.add_devices",
            new_callable=AsyncMock,
            return_value=True,
        ),
    ):
        await async_setup_platform(hass, {"email": EMAIL}, MagicMock())

    probe.assert_awaited_once()
    switches = account_dict["entities"]["switch"][SERIAL]
    assert "display_power" not in switches
    assert "adaptive_brightness" not in switches
    assert account_dict["display_unsupported"] == {SERIAL}
    assert SERIAL not in account_dict["display_states"]


@pytest.mark.asyncio
async def test_number_setup_creates_display_brightness():
    """The number platform creates brightness for display models."""
    from custom_components.alexa_media.number import async_setup_platform

    client = MagicMock()
    client.unique_id = SERIAL
    client._login = MagicMock(email=EMAIL)
    account_dict = {
        "devices": {
            "media_player": {
                SERIAL: {
                    "serialNumber": SERIAL,
                    "deviceType": SHOW_TYPE,
                    "deviceFamily": "ECHO_SHOW",
                    "deviceAccountId": "account-id",
                    "capabilities": [],
                }
            },
            "number": {},
        },
        "entities": {
            "media_player": {SERIAL: client},
            "number": {},
        },
        "login_obj": MagicMock(),
    }
    hass = MagicMock()
    hass.data = {DATA_ALEXAMEDIA: {"accounts": {EMAIL: account_dict}}}

    with (
        patch(
            "custom_components.alexa_media.display.async_probe_display_settings",
            new_callable=AsyncMock,
            return_value=({SETTING_BRIGHTNESS: 50}, False),
        ) as probe,
        patch(
            "custom_components.alexa_media.number.add_devices",
            new_callable=AsyncMock,
            return_value=True,
        ),
    ):
        await async_setup_platform(hass, {"email": EMAIL}, MagicMock())

    probe.assert_awaited_once()
    assert f"{SERIAL}_display_brightness" in account_dict["entities"]["number"]


@pytest.mark.asyncio
async def test_number_setup_skips_unsupported_display():
    """A model that rejects brightness gets no number entity."""
    from custom_components.alexa_media.number import async_setup_platform

    client = MagicMock()
    client.unique_id = SERIAL
    client._login = MagicMock(email=EMAIL)
    account_dict = {
        "devices": {
            "media_player": {
                SERIAL: {
                    "serialNumber": SERIAL,
                    "deviceType": SHOW_15_GEN1,
                    "deviceFamily": "ECHO_SHOW",
                    "deviceAccountId": "account-id",
                    "capabilities": [],
                }
            },
            "number": {},
        },
        "entities": {
            "media_player": {SERIAL: client},
            "number": {},
        },
        "login_obj": MagicMock(),
    }
    hass = MagicMock()
    hass.data = {DATA_ALEXAMEDIA: {"accounts": {EMAIL: account_dict}}}

    with (
        patch(
            "custom_components.alexa_media.display.async_probe_display_settings",
            new_callable=AsyncMock,
            return_value=({}, False),
        ) as probe,
        patch(
            "custom_components.alexa_media.number.add_devices",
            new_callable=AsyncMock,
            return_value=True,
        ),
    ):
        await async_setup_platform(hass, {"email": EMAIL}, MagicMock())

    probe.assert_awaited_once()
    assert f"{SERIAL}_display_brightness" not in account_dict["entities"]["number"]
    assert account_dict["display_unsupported"] == {SERIAL}


@pytest.mark.asyncio
async def test_number_setup_checks_display_before_storing_entities():
    """A missing display media player must not leave half-stored numbers."""
    from custom_components.alexa_media.number import async_setup_platform

    account_dict = {
        "devices": {
            "media_player": {
                SERIAL: {
                    "serialNumber": SERIAL,
                    "deviceType": SHOW_TYPE,
                    "deviceFamily": "ECHO_SHOW",
                    "deviceAccountId": "account-id",
                    "capabilities": [],
                }
            },
            "number": {SERIAL: {"notification_volume": True}},
        },
        "entities": {"media_player": {}, "number": {}},
        "login_obj": MagicMock(),
    }
    hass = MagicMock()
    hass.data = {DATA_ALEXAMEDIA: {"accounts": {EMAIL: account_dict}}}

    with pytest.raises(ConfigEntryNotReady):
        await async_setup_platform(hass, {"email": EMAIL}, MagicMock())

    assert account_dict["entities"]["number"] == {}


@pytest.mark.asyncio
async def test_display_state_is_shared_per_device():
    """Switch and number platforms reuse the same display state."""
    account_dict = {"display_states": {}}
    login = MagicMock()
    device = _device()
    client = MagicMock(unique_id=SERIAL)

    with patch(
        "custom_components.alexa_media.display.async_probe_display_settings",
        new_callable=AsyncMock,
        return_value=({SETTING_BRIGHTNESS: 50}, False),
    ) as probe:
        first = await async_get_display_state(
            MagicMock(), account_dict, login, device, client
        )
        new_login = MagicMock()
        new_client = MagicMock(unique_id=SERIAL)
        second = await async_get_display_state(
            MagicMock(), account_dict, new_login, device, new_client
        )

    assert first is second
    probe.assert_awaited_once()
    assert account_dict["display_states"][SERIAL] is first
    assert first.login is new_login
    assert first.client is new_client


@pytest.mark.asyncio
async def test_display_state_caches_unsupported_device():
    """A device without settings is probed once and then skipped."""
    account_dict = {"display_states": {}}

    with patch(
        "custom_components.alexa_media.display.async_probe_display_settings",
        new_callable=AsyncMock,
        return_value=({}, False),
    ) as probe:
        first = await async_get_display_state(
            MagicMock(), account_dict, MagicMock(), _device(), MagicMock()
        )
        second = await async_get_display_state(
            MagicMock(), account_dict, MagicMock(), _device(), MagicMock()
        )

    assert first is None
    assert second is None
    probe.assert_awaited_once()
    assert account_dict["display_unsupported"] == {SERIAL}
    assert SERIAL not in account_dict["display_states"]


@pytest.mark.asyncio
async def test_transient_probe_failure_is_not_cached_as_unsupported():
    """A partial probe is retried on the next setup instead of cached."""
    account_dict = {"display_states": {}}

    with patch(
        "custom_components.alexa_media.display.async_probe_display_settings",
        new_callable=AsyncMock,
        return_value=({SETTING_BRIGHTNESS: 50}, True),
    ):
        state = await async_get_display_state(
            MagicMock(), account_dict, MagicMock(), _device(), MagicMock()
        )

    assert state is None
    assert account_dict["display_unsupported"] == set()
    assert account_dict["display_states"] == {}


@pytest.mark.asyncio
async def test_get_display_state_without_serial():
    """A malformed device entry is skipped instead of raising."""
    account_dict = {"display_states": {}}

    with patch(
        "custom_components.alexa_media.display.async_probe_display_settings",
        new_callable=AsyncMock,
    ) as probe:
        state = await async_get_display_state(
            MagicMock(),
            account_dict,
            MagicMock(),
            {"deviceType": UNKNOWN_TYPE},
            MagicMock(),
        )

    assert state is None
    probe.assert_not_awaited()


@pytest.mark.asyncio
async def test_concurrent_platforms_share_one_display_probe():
    """Number and switch setup await the same in-flight probe."""
    account_dict = {"display_states": {}}
    started = asyncio.Event()
    release = asyncio.Event()

    async def _probe(*_args, **_kwargs):
        started.set()
        await release.wait()
        return {SETTING_BRIGHTNESS: 50}, False

    with patch(
        "custom_components.alexa_media.display.async_probe_display_settings",
        side_effect=_probe,
    ) as probe:
        first = asyncio.create_task(
            async_get_display_state(
                MagicMock(), account_dict, MagicMock(), _device(), MagicMock()
            )
        )
        await started.wait()
        second = asyncio.create_task(
            async_get_display_state(
                MagicMock(), account_dict, MagicMock(), _device(), MagicMock()
            )
        )
        await asyncio.sleep(0)
        release.set()
        first_state, second_state = await asyncio.gather(first, second)

    probe.assert_awaited_once()
    assert first_state is second_state
    assert first_state.supports(SETTING_BRIGHTNESS)


@pytest.mark.asyncio
async def test_shared_probe_survives_one_caller_cancel():
    """Cancelling one platform does not cancel the shared probe for the other."""
    account_dict = {"display_states": {}}
    started = asyncio.Event()
    release = asyncio.Event()

    async def _probe(*_args, **_kwargs):
        started.set()
        await release.wait()
        return {SETTING_BRIGHTNESS: 50}, False

    with patch(
        "custom_components.alexa_media.display.async_probe_display_settings",
        side_effect=_probe,
    ):
        first = asyncio.create_task(
            async_get_display_state(
                MagicMock(), account_dict, MagicMock(), _device(), MagicMock()
            )
        )
        await started.wait()
        second = asyncio.create_task(
            async_get_display_state(
                MagicMock(), account_dict, MagicMock(), _device(), MagicMock()
            )
        )
        await asyncio.sleep(0)
        first.cancel()
        release.set()

        with pytest.raises(asyncio.CancelledError):
            await first
        state = await second

    assert state.supports(SETTING_BRIGHTNESS)
    assert state.value(SETTING_BRIGHTNESS) == 50


@pytest.mark.asyncio
async def test_display_probe_concurrency_is_bounded():
    """Many devices are probed concurrently, but never above the bound."""
    account_dict = {"display_states": {}}
    current = 0
    peak = 0

    async def _probe(*_args, **_kwargs):
        nonlocal current, peak
        current += 1
        peak = max(peak, current)
        try:
            await asyncio.sleep(0.01)
        finally:
            current -= 1
        return {SETTING_BRIGHTNESS: 40}, False

    serials = [f"SERIAL{i}" for i in range(6)]
    devices = [
        {"serialNumber": serial, "deviceAccountId": f"id-{serial}"}
        for serial in serials
    ]
    clients = [MagicMock(unique_id=serial) for serial in serials]

    with patch(
        "custom_components.alexa_media.display.async_probe_display_settings",
        side_effect=_probe,
    ):
        states = await asyncio.gather(
            *(
                async_get_display_state(
                    MagicMock(), account_dict, MagicMock(), device, client
                )
                for device, client in zip(devices, clients, strict=True)
            )
        )

    assert all(state is not None for state in states)
    assert len(account_dict["display_states"]) == len(serials)
    assert peak <= DISPLAY_PROBE_CONCURRENCY


@pytest.mark.asyncio
async def test_failed_probe_is_not_retried_by_sibling_platform():
    """A sibling platform cannot replace a failure with a success."""
    account_dict = {
        "display_states": {},
        "config_entry": MagicMock(entry_id="entry"),
    }

    with patch(
        "custom_components.alexa_media.display.async_probe_display_settings",
        new_callable=AsyncMock,
        return_value=({}, True),
    ) as probe:
        first = await async_get_display_state(
            MagicMock(), account_dict, MagicMock(), _device(), MagicMock()
        )
        second = await async_get_display_state(
            MagicMock(), account_dict, MagicMock(), _device(), MagicMock()
        )

    assert first is None
    assert second is None
    probe.assert_awaited_once()
    assert account_dict["display_probe_failed"] == {SERIAL}
    assert account_dict["display_states"] == {}


@pytest.mark.asyncio
@pytest.mark.parametrize("device_type", [SHOW_8_GEN2, SHOW_15_GEN1, SHOW_15_GEN2])
async def test_reported_show_models_reject_every_setting(device_type):
    """Show models that return 400 for all settings get no display state."""
    account_dict = {"display_states": {}}
    device = _device(device_type)

    with patch(
        "custom_components.alexa_media.display.async_get_device_setting",
        new_callable=AsyncMock,
        return_value=(400, None),
    ) as getter:
        state = await async_get_display_state(
            MagicMock(), account_dict, MagicMock(), device, MagicMock()
        )

    assert state is None
    assert getter.await_count == 3
    assert account_dict["display_unsupported"] == {SERIAL}
    assert account_dict["display_states"] == {}


@pytest.mark.asyncio
async def test_dot_with_clock_probe_creates_supported_state():
    """A Dot with Clock exposes all three settings."""
    account_dict = {"display_states": {}}
    device = _device(DOT_CLOCK_TYPE)

    async def _get(_login, _account_id, setting):
        return (
            200,
            {
                SETTING_DISPLAY_POWER: "ON",
                SETTING_BRIGHTNESS: 30,
                SETTING_ADAPTIVE_BRIGHTNESS: "OFF",
            }[setting],
        )

    with patch(
        "custom_components.alexa_media.display.async_get_device_setting",
        side_effect=_get,
    ):
        state = await async_get_display_state(
            MagicMock(), account_dict, MagicMock(), device, MagicMock()
        )

    assert state is not None
    assert state.supports(SETTING_DISPLAY_POWER)
    assert state.supports(SETTING_BRIGHTNESS)
    assert state.supports(SETTING_ADAPTIVE_BRIGHTNESS)
    assert account_dict["display_states"][SERIAL] is state


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "entity_class,setting,initial,updated,attribute,expected",
    [
        (AlexaDisplayPowerSwitch, SETTING_DISPLAY_POWER, "OFF", "ON", "is_on", True),
        (
            AlexaAdaptiveBrightnessSwitch,
            SETTING_ADAPTIVE_BRIGHTNESS,
            "OFF",
            "ON",
            "is_on",
            True,
        ),
        (AlexaDisplayBrightness, SETTING_BRIGHTNESS, 10, 75, "native_value", 75),
    ],
)
async def test_display_entities_receive_shared_state_updates(
    entity_class, setting, initial, updated, attribute, expected
):
    """Shared polling and successful writes update every listener-driven entity."""
    state = _state()
    entity = entity_class(state)
    entity.async_write_ha_state = MagicMock()
    removers = []
    entity.async_on_remove = removers.append
    values = {setting: initial}

    async def _get(_login, _account_id, key):
        return 200, values.get(key)

    with (
        patch(
            "custom_components.alexa_media.display.async_track_time_interval"
        ) as track,
        patch(
            "custom_components.alexa_media.display.async_get_device_setting",
            side_effect=_get,
        ),
        patch(
            "custom_components.alexa_media.display.async_set_device_setting",
            new_callable=AsyncMock,
            return_value=True,
        ),
    ):
        await entity.async_added_to_hass()
        assert not entity.should_poll
        track.assert_called_once()
        entity.async_write_ha_state.assert_called_once()
        values[setting] = updated
        await track.call_args.args[1](None)
        assert getattr(entity, attribute) == expected
        assert entity.async_write_ha_state.call_count == 2
        assert await state.async_set(setting, initial)
        assert state.value(setting) == initial
        assert entity.async_write_ha_state.call_count == 3
        for remove in removers:
            remove()
        state._async_notify()
        assert entity.async_write_ha_state.call_count == 3
        state.async_stop()


@pytest.mark.parametrize(
    ("setting", "value", "expected"),
    [
        (SETTING_BRIGHTNESS, 0, 0),
        (SETTING_BRIGHTNESS, "0", 0),
        (SETTING_BRIGHTNESS, 50, 50),
        (SETTING_BRIGHTNESS, "50", 50),
        (SETTING_BRIGHTNESS, 50.5, 50.5),
        (SETTING_BRIGHTNESS, "unknown", None),
        (SETTING_BRIGHTNESS, -1, None),
        (SETTING_BRIGHTNESS, 101, None),
        (SETTING_BRIGHTNESS, True, None),
        (SETTING_DISPLAY_POWER, "ON", "ON"),
        (SETTING_DISPLAY_POWER, "OFF", "OFF"),
        (SETTING_DISPLAY_POWER, "on", None),
        (SETTING_ADAPTIVE_BRIGHTNESS, "ON", "ON"),
        (SETTING_ADAPTIVE_BRIGHTNESS, "unknown", None),
    ],
)
def test_normalize_setting_value(setting, value, expected):
    """Setting values are validated before they reach entity state."""
    assert _normalize_setting_value(setting, value) == expected


@pytest.mark.asyncio
async def test_probe_treats_throttled_400_as_temporary():
    """An isolated self-throttled 400 is temporary, not unsupported."""
    login = MagicMock()
    login._rate_retry_inflight = False

    async def _get_setting(_login, _account_id, setting):
        if setting != SETTING_BRIGHTNESS:
            return 200, "ON"
        login._rate_retry_inflight = True
        await asyncio.sleep(0.1)
        login._rate_retry_inflight = False
        return 400, None

    with (
        patch(
            "custom_components.alexa_media.display.async_get_device_setting",
            side_effect=_get_setting,
        ),
        patch(
            "custom_components.alexa_media.display.DISPLAY_THROTTLE_WATCH_INTERVAL",
            0.001,
        ),
    ):
        values, failed = await async_probe_display_settings(
            MagicMock(), login, _device()
        )

    assert values == {
        SETTING_DISPLAY_POWER: "ON",
        SETTING_ADAPTIVE_BRIGHTNESS: "ON",
    }
    assert failed is True


@pytest.mark.asyncio
async def test_probe_rejects_invalid_brightness():
    """An unparsable 200 is malformed, not a supported value."""
    with patch(
        "custom_components.alexa_media.display.async_get_device_setting",
        new_callable=AsyncMock,
        return_value=(200, "unknown"),
    ):
        values, failed = await async_probe_display_settings(
            MagicMock(), MagicMock(), _device()
        )

    assert values == {}
    assert failed is True


@pytest.mark.asyncio
async def test_display_state_keeps_setting_on_throttled_400():
    """A self-throttled 400 does not count toward the unsupported streak."""
    state = DisplayState(
        MagicMock(),
        MagicMock(),
        _device(),
        supported={SETTING_BRIGHTNESS: 40},
        probed=True,
    )
    state.login._rate_retry_inflight = False
    state.client = MagicMock(unique_id=SERIAL)

    async def _get_setting(_login, _account_id, _setting):
        state.login._rate_retry_inflight = True
        await asyncio.sleep(0.1)
        state.login._rate_retry_inflight = False
        return 400, None

    with (
        patch(
            "custom_components.alexa_media.display.async_get_device_setting",
            side_effect=_get_setting,
        ),
        patch(
            "custom_components.alexa_media.display.DISPLAY_THROTTLE_WATCH_INTERVAL",
            0.001,
        ),
    ):
        for _ in range(DISPLAY_FAILURE_LIMIT):
            await state.async_refresh()

    assert state.supports(SETTING_BRIGHTNESS)
    assert state.value(SETTING_BRIGHTNESS) == 40
    assert state._failures[SETTING_BRIGHTNESS] == 0


@pytest.mark.asyncio
async def test_display_state_keeps_last_value_on_invalid_200():
    """A malformed 200 keeps the last good value and the setting."""
    state = DisplayState(
        MagicMock(),
        MagicMock(),
        _device(),
        supported={SETTING_BRIGHTNESS: 40},
        probed=True,
    )
    state.client = MagicMock(unique_id=SERIAL)

    with patch(
        "custom_components.alexa_media.display.async_get_device_setting",
        new_callable=AsyncMock,
        return_value=(200, "unknown"),
    ):
        await state.async_refresh()

    assert state.supports(SETTING_BRIGHTNESS)
    assert state.value(SETTING_BRIGHTNESS) == 40


@pytest.mark.asyncio
async def test_display_refresh_reports_relogin_on_login_error():
    """A persistent 401 reports reauthentication once per refresh."""
    state = DisplayState(
        MagicMock(),
        MagicMock(),
        _device(),
        supported={SETTING_BRIGHTNESS: 40},
        probed=True,
    )
    state.client = MagicMock(unique_id=SERIAL)

    with (
        patch(
            "custom_components.alexa_media.display.async_get_device_setting",
            new_callable=AsyncMock,
            side_effect=AlexapyLoginError("login failed"),
        ),
        patch(
            "custom_components.alexa_media.display.report_relogin_required"
        ) as report,
    ):
        await state.async_refresh()

    report.assert_called_once_with(
        state.hass, state.login, state.login.email, require_status=False
    )


def test_display_reload_budget_survives_account_recreation():
    """A recurring probe failure cannot reload the entry every cycle."""
    hass = MagicMock()
    hass.data = {
        DATA_ALEXAMEDIA: {
            "display_entry_states": {"entry": {"pending": {"serial"}}},
        }
    }
    first = {
        "config_entry": MagicMock(entry_id="entry"),
    }
    second = {
        "config_entry": MagicMock(entry_id="entry"),
    }

    with patch("custom_components.alexa_media.display.async_call_later") as later:
        _schedule_display_reload(hass, first)
        _schedule_display_reload(hass, second)

    later.assert_called_once()


def test_schedule_display_reload_skips_without_pending_probe():
    """No reload is scheduled when no device still needs recovery."""
    hass = MagicMock()
    account_dict = {"config_entry": MagicMock(entry_id="entry")}

    with patch("custom_components.alexa_media.display.async_call_later") as later:
        _schedule_display_reload(hass, account_dict)

    later.assert_not_called()


@pytest.mark.asyncio
async def test_unsupported_probe_cancels_pending_reload():
    """A conclusive unsupported result cancels a no-longer-needed reload."""
    hass = MagicMock()
    unsub = MagicMock()
    account_dict = {
        "config_entry": MagicMock(entry_id="entry"),
        "display_probe_pending": {SERIAL},
        "display_reload_unsub": unsub,
    }

    with patch(
        "custom_components.alexa_media.display.async_probe_display_settings",
        new_callable=AsyncMock,
        return_value=({}, False),
    ):
        state = await async_get_display_state(
            hass, account_dict, MagicMock(), _device(), MagicMock()
        )

    assert state is None
    unsub.assert_called_once()
    assert account_dict["display_probe_pending"] == set()


def test_normalize_setting_value_rejects_unknown_setting():
    """Unknown settings never produce a cached value."""
    assert _normalize_setting_value("unknown", "ON") is None


def test_cancel_display_reload_keeps_timer_while_pending():
    """A device that still needs recovery keeps the timer alive."""
    unsub = MagicMock()
    account_dict = {
        "display_probe_pending": {"serial"},
        "display_reload_unsub": unsub,
    }

    _cancel_display_reload_if_idle(MagicMock(), account_dict)

    unsub.assert_not_called()
    assert account_dict["display_reload_unsub"] is unsub


def test_schedule_display_reload_requires_entry_id():
    """An entry without an id cannot schedule a reload."""
    hass = MagicMock()
    account_dict = {
        "config_entry": SimpleNamespace(),
        "display_probe_pending": {"serial"},
    }

    with patch("custom_components.alexa_media.display.async_call_later") as later:
        _schedule_display_reload(hass, account_dict)

    later.assert_not_called()


@pytest.mark.asyncio
async def test_probe_captures_concurrent_throttle_per_request():
    """A concurrent throttled 400 stays temporary, not unsupported."""
    login = MagicMock()
    login._rate_retry_inflight = False
    power_started = asyncio.Event()
    brightness_done = asyncio.Event()

    async def fake_get_setting(_login, _account_id, setting):
        if setting == SETTING_DISPLAY_POWER:
            login._rate_retry_inflight = True
            power_started.set()
            await brightness_done.wait()
            login._rate_retry_inflight = False
            return 200, "ON"
        if setting == SETTING_BRIGHTNESS:
            await power_started.wait()
            assert login._rate_retry_inflight is True
            # Keep the throttle window open long enough for the watcher to
            # sample it; a real retry holds this for 10-63 seconds.
            await asyncio.sleep(0.1)
            brightness_done.set()
            return 400, None
        return 200, "OFF"

    with (
        patch(
            "custom_components.alexa_media.display.async_get_device_setting",
            new_callable=AsyncMock,
            side_effect=fake_get_setting,
        ),
        patch(
            "custom_components.alexa_media.display.DISPLAY_THROTTLE_WATCH_INTERVAL",
            0.001,
        ),
    ):
        supported, failed = await async_probe_display_settings(
            MagicMock(), login, _device()
        )

    assert supported == {
        SETTING_DISPLAY_POWER: "ON",
        SETTING_ADAPTIVE_BRIGHTNESS: "OFF",
    }
    assert failed is True


@pytest.mark.asyncio
async def test_refresh_captures_concurrent_throttle_per_request():
    """A throttled 400 across refreshes keeps the cached brightness."""
    login = MagicMock()
    login._rate_retry_inflight = False

    state = DisplayState(
        MagicMock(),
        login,
        _device(),
        supported={
            SETTING_DISPLAY_POWER: "ON",
            SETTING_BRIGHTNESS: 40,
        },
        probed=True,
    )
    state.client = MagicMock(unique_id=SERIAL)

    for _ in range(DISPLAY_FAILURE_LIMIT):
        power_started = asyncio.Event()
        brightness_done = asyncio.Event()

        async def fake_get_setting(
            _login,
            _account_id,
            setting,
            power_started=power_started,
            brightness_done=brightness_done,
        ):
            if setting == SETTING_DISPLAY_POWER:
                login._rate_retry_inflight = True
                power_started.set()
                await brightness_done.wait()
                login._rate_retry_inflight = False
                return 200, "ON"
            if setting == SETTING_BRIGHTNESS:
                await power_started.wait()
                assert login._rate_retry_inflight is True
                # Keep the throttle window open long enough for the watcher.
                await asyncio.sleep(0.1)
                brightness_done.set()
                return 400, None

        with (
            patch(
                "custom_components.alexa_media.display.async_get_device_setting",
                new_callable=AsyncMock,
                side_effect=fake_get_setting,
            ),
            patch(
                "custom_components.alexa_media.display.DISPLAY_THROTTLE_WATCH_INTERVAL",
                0.001,
            ),
        ):
            await state.async_refresh()

        assert state._failures[SETTING_BRIGHTNESS] == 0

    assert state.supports(SETTING_BRIGHTNESS)
    assert state.value(SETTING_BRIGHTNESS) == 40
    assert state.value(SETTING_DISPLAY_POWER) == "ON"


@pytest.mark.asyncio
async def test_initial_probe_reports_relogin_once_and_resets_after_recovery():
    """A probe auth failure reports once and allows a later report."""
    hass = MagicMock()
    hass.data = {DATA_ALEXAMEDIA: {}}
    login = MagicMock(email=EMAIL)

    with (
        patch(
            "custom_components.alexa_media.display.async_get_device_setting",
            new_callable=AsyncMock,
            side_effect=AlexapyLoginError("login failed"),
        ),
        patch(
            "custom_components.alexa_media.display.report_relogin_required",
            return_value=True,
        ) as report,
    ):
        values, failed = await async_probe_display_settings(hass, login, _device())
        assert values == {}
        assert failed is True
        report.assert_called_once()

        await async_probe_display_settings(hass, login, _device())
        assert report.call_count == 1

        with patch(
            "custom_components.alexa_media.display.async_get_device_setting",
            new_callable=AsyncMock,
            return_value=(400, None),
        ):
            await async_probe_display_settings(hass, login, _device())

        await async_probe_display_settings(hass, login, _device())
        assert report.call_count == 2


@pytest.mark.asyncio
async def test_refresh_does_not_duplicate_probe_relogin_report():
    """The refresh path shares the probe's once-per-account report."""
    hass = MagicMock()
    hass.data = {DATA_ALEXAMEDIA: {}}
    login = MagicMock(email=EMAIL)

    with (
        patch(
            "custom_components.alexa_media.display.async_get_device_setting",
            new_callable=AsyncMock,
            side_effect=AlexapyLoginError("login failed"),
        ),
        patch(
            "custom_components.alexa_media.display.report_relogin_required",
            return_value=True,
        ) as report,
    ):
        await async_probe_display_settings(hass, login, _device())
        assert report.call_count == 1

        state = DisplayState(
            hass,
            login,
            _device(),
            supported={SETTING_BRIGHTNESS: 40},
            probed=True,
        )
        state.client = MagicMock(unique_id=SERIAL)
        await state.async_refresh()

        assert report.call_count == 1


def test_reload_budget_stays_consumed_until_all_devices_recover():
    """A successful device does not release the budget while another is pending."""
    hass = MagicMock()
    hass.data = {
        DATA_ALEXAMEDIA: {
            "display_entry_states": {"entry": {"pending": set()}},
            "display_reload_budget": {},
        }
    }
    entry_state = hass.data[DATA_ALEXAMEDIA]["display_entry_states"]["entry"]
    budget = hass.data[DATA_ALEXAMEDIA]["display_reload_budget"]
    first = {"config_entry": MagicMock(entry_id="entry")}
    second = {"config_entry": MagicMock(entry_id="entry")}

    with patch("custom_components.alexa_media.display.async_call_later") as later:
        entry_state["pending"].update({"A", "B"})
        _schedule_display_reload(hass, first)
        later.assert_called_once()
        assert budget["entry"] == 1

        entry_state["pending"].discard("B")
        _clear_display_reload_budget(hass, second)
        assert budget["entry"] == 1

        entry_state["pending"].discard("A")
        _clear_display_reload_budget(hass, second)
        assert "entry" not in budget


def test_report_display_relogin_ignores_missing_email():
    """A login without an email cannot be reported."""
    hass = MagicMock()
    hass.data = {DATA_ALEXAMEDIA: {}}
    login = MagicMock(email=None)

    with patch(
        "custom_components.alexa_media.display.report_relogin_required"
    ) as report:
        _report_display_relogin(hass, login)

    report.assert_not_called()


@pytest.mark.asyncio
async def test_throttle_watch_cancels_request_on_caller_cancel():
    """Cancelling a probe cancels the request it owns."""
    started = asyncio.Event()
    finished = asyncio.Event()

    async def _get():
        started.set()
        try:
            await asyncio.sleep(10)
        finally:
            finished.set()

    task = asyncio.create_task(_await_with_throttle_watch(MagicMock(), _get()))
    await started.wait()
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
    assert finished.is_set()


@pytest.mark.asyncio
async def test_probe_timeout_discards_partial_results():
    """The whole probe is bounded and a timeout keeps no partial capability."""

    async def _get(_login, _account_id, setting):
        if setting == SETTING_BRIGHTNESS:
            await asyncio.sleep(10)
        return 200, "ON"

    with (
        patch(
            "custom_components.alexa_media.display.async_get_device_setting",
            side_effect=_get,
        ),
        patch("custom_components.alexa_media.display.DISPLAY_PROBE_TIMEOUT", 0.05),
    ):
        values, failed = await async_probe_display_settings(
            MagicMock(), MagicMock(), _device()
        )

    assert values == {}
    assert failed is True


def test_stale_pending_serials_are_pruned():
    """Removed devices cannot keep the reload budget consumed forever."""
    hass = MagicMock()
    hass.data = {
        DATA_ALEXAMEDIA: {
            "display_entry_states": {"entry": {"pending": {"STALE"}}},
            "display_reload_budget": {"entry": 1},
        }
    }
    account_dict = {
        "config_entry": MagicMock(entry_id="entry"),
        "devices": {"media_player": {SERIAL: _device()}},
    }

    assert _display_pending(hass, account_dict) == set()

    _clear_display_reload_budget(hass, account_dict)
    assert "entry" not in hass.data[DATA_ALEXAMEDIA]["display_reload_budget"]


def test_stale_pending_pruning_keeps_live_devices():
    """Only removed serials are pruned; live recovery keeps the budget."""
    hass = MagicMock()
    hass.data = {
        DATA_ALEXAMEDIA: {
            "display_entry_states": {"entry": {"pending": {"STALE", SERIAL}}},
            "display_reload_budget": {"entry": 1},
        }
    }
    account_dict = {
        "config_entry": MagicMock(entry_id="entry"),
        "devices": {"media_player": {SERIAL: _device()}},
    }

    assert _display_pending(hass, account_dict) == {SERIAL}

    _clear_display_reload_budget(hass, account_dict)
    assert hass.data[DATA_ALEXAMEDIA]["display_reload_budget"]["entry"] == 1


@pytest.mark.asyncio
async def test_unload_stops_display_recovery():
    """Unload stops polling and cancels display probes and timers."""
    from custom_components.alexa_media import async_unload_entry

    display_state = MagicMock()
    probe = MagicMock()
    probe.done.return_value = False
    setup_task = MagicMock()
    setup_task.done.return_value = False
    unsub = MagicMock()
    account_dict = {
        "display_states": {SERIAL: display_state},
        "display_probes": {SERIAL: probe},
        "display_setup_tasks": {setup_task},
        "display_reload_unsub": unsub,
    }
    hass = MagicMock()
    hass.data = {DATA_ALEXAMEDIA: {"accounts": {EMAIL: account_dict}}}
    entry = MagicMock(data={"email": EMAIL})

    with (
        patch("custom_components.alexa_media.ALEXA_COMPONENTS", []),
        patch("custom_components.alexa_media.DEPENDENT_ALEXA_COMPONENTS", []),
        patch(
            "custom_components.alexa_media.close_connections",
            new_callable=AsyncMock,
        ),
    ):
        assert await async_unload_entry(hass, entry)

    display_state.async_stop.assert_called_once()
    probe.cancel.assert_called_once()
    setup_task.cancel.assert_called_once()
    unsub.assert_called_once()


@pytest.mark.asyncio
async def test_unload_missing_account_returns_true():
    """Unload tolerates a setup that never created the account record."""
    from custom_components.alexa_media import async_unload_entry

    hass = MagicMock()
    hass.data = {DATA_ALEXAMEDIA: {"accounts": {}}}
    entry = MagicMock(data={"email": EMAIL})

    assert await async_unload_entry(hass, entry)
