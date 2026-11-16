"""Tests for Echo display controls."""

import asyncio
from unittest.mock import ANY, AsyncMock, MagicMock, patch

from alexapy import hide_serial
from alexapy.errors import AlexapyLoginError, AlexapyTooManyRequestsError
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
import pytest

from custom_components.alexa_media.const import DATA_ALEXAMEDIA
from custom_components.alexa_media.display import (
    DISPLAY_FAILURE_LIMIT,
    DISPLAY_SETTINGS,
    SETTING_ADAPTIVE_BRIGHTNESS,
    SETTING_BRIGHTNESS,
    SETTING_DISPLAY_POWER,
    AlexaAdaptiveBrightnessSwitch,
    AlexaDisplayBrightness,
    AlexaDisplayPowerSwitch,
    DisplayState,
    _decode_setting,
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


def test_decode_setting():
    """Device settings are stored as JSON strings."""
    assert _decode_setting('"ON"') == "ON"
    assert _decode_setting("100") == 100
    assert _decode_setting("plain") == "plain"
    assert _decode_setting("{not json") == "{not json"
    assert _decode_setting(123) == 123


class _FakeResponse:
    """Minimal aiohttp response for the direct settings request."""

    def __init__(
        self,
        status: int,
        value=None,
        *,
        missing_value: bool = False,
        json_error: Exception | None = None,
    ) -> None:
        self.status = status
        self.reason = "test"
        self._value = value
        self._missing_value = missing_value
        self._json_error = json_error
        self.released = False

    async def json(self, content_type=None):
        if self._json_error is not None:
            raise self._json_error
        if self._missing_value:
            return {"no-value": True}
        return {"value": self._value}

    def release(self) -> None:
        self.released = True


def _login(*responses):
    login = MagicMock()
    login.url = "amazon.com"
    login.close_requested = False
    login.status = {"login_successful": True}
    login._headers = {}
    login._ssl = None
    login.session = MagicMock()
    login.session.closed = False
    login.session.get = AsyncMock(side_effect=list(responses))
    login.test_loggedin = AsyncMock(return_value=True)
    return login


@pytest.mark.asyncio
async def test_get_device_setting_error_paths():
    """Only a 400 is unsupported; other statuses stay distinguishable."""
    assert await async_get_device_setting(MagicMock(), "", SETTING_DISPLAY_POWER) == (
        0,
        None,
    )

    login = _login(_FakeResponse(400))
    assert await async_get_device_setting(
        login, "account-id", SETTING_DISPLAY_POWER
    ) == (400, None)

    login = _login(_FakeResponse(503))
    assert await async_get_device_setting(
        login, "account-id", SETTING_DISPLAY_POWER
    ) == (503, None)

    login = _login(_FakeResponse(200, json_error=ValueError("bad json")))
    assert await async_get_device_setting(
        login, "account-id", SETTING_DISPLAY_POWER
    ) == (200, None)

    login = _login(_FakeResponse(200, missing_value=True))
    assert await async_get_device_setting(
        login, "account-id", SETTING_DISPLAY_POWER
    ) == (200, None)

    login = _login(_FakeResponse(200, '{"nested": 1}'))
    assert await async_get_device_setting(
        login, "account-id", SETTING_DISPLAY_POWER
    ) == (200, None)

    login = _login(_FakeResponse(200, "[1, 2]"))
    assert await async_get_device_setting(
        login, "account-id", SETTING_DISPLAY_POWER
    ) == (200, None)


@pytest.mark.asyncio
async def test_get_device_setting_retries_unauthorized_once():
    """A 401 is retried once, matching alexapy's request behaviour."""
    login = _login(_FakeResponse(401), _FakeResponse(200, '"ON"'))

    assert await async_get_device_setting(
        login, "account-id", SETTING_DISPLAY_POWER
    ) == (200, "ON")
    assert login.session.get.await_count == 2


@pytest.mark.asyncio
async def test_get_device_setting_raises_for_login_or_throttle():
    """Closed sessions and 429 stay retryable for the caller."""
    login = _login()
    login.session.closed = True
    with pytest.raises(AlexapyLoginError):
        await async_get_device_setting(login, "account-id", SETTING_DISPLAY_POWER)

    login = _login()
    login.close_requested = True
    with pytest.raises(AlexapyLoginError):
        await async_get_device_setting(login, "account-id", SETTING_DISPLAY_POWER)

    login = _login()
    login.status = {"login_successful": False}
    with pytest.raises(AlexapyLoginError):
        await async_get_device_setting(login, "account-id", SETTING_DISPLAY_POWER)

    login = _login(_FakeResponse(429))
    with pytest.raises(AlexapyTooManyRequestsError):
        await async_get_device_setting(login, "account-id", SETTING_DISPLAY_POWER)


@pytest.mark.asyncio
async def test_set_device_setting_without_account_id():
    """A device without an account id is never written to."""
    with patch(
        "custom_components.alexa_media.display.AlexaAPI._static_request",
        new_callable=AsyncMock,
    ) as request:
        assert not await async_set_device_setting(
            MagicMock(), "", SETTING_BRIGHTNESS, 50
        )
    request.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_device_setting():
    """Reading a setting returns the HTTP status and decoded value."""
    response = _FakeResponse(200, '"ON"')
    login = _login(response)

    status, value = await async_get_device_setting(
        login, "account-id", SETTING_DISPLAY_POWER
    )

    assert (status, value) == (200, "ON")
    login.session.get.assert_awaited_once()
    assert login.session.get.await_args.args[0] == (
        "https://alexa.amazon.com/api/v1/devices/account-id/settings/displayPower"
    )
    assert response.released


@pytest.mark.asyncio
async def test_set_device_setting_uses_json_value():
    """Writing a setting wraps the value the way the Alexa app does."""
    with patch(
        "custom_components.alexa_media.display.AlexaAPI._static_request",
        new_callable=AsyncMock,
        return_value=MagicMock(),
    ) as mock_request:
        assert await async_set_device_setting(
            MagicMock(), "account-id", SETTING_BRIGHTNESS, 65
        )

    assert mock_request.call_args.kwargs["data"] == {"value": "65"}


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
        supported, failed = await async_probe_display_settings(MagicMock(), _device())

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
        supported, failed = await async_probe_display_settings(MagicMock(), _device())

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
        supported, failed = await async_probe_display_settings(MagicMock(), _device())

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
        supported, failed = await async_probe_display_settings(MagicMock(), _device())

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
            MagicMock(), {"serialNumber": SERIAL}
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
    account_dict = {"config_entry": MagicMock(entry_id="entry")}
    hass = MagicMock()

    with patch("custom_components.alexa_media.display.async_call_later") as later:
        _schedule_display_reload(hass, account_dict)
        _schedule_display_reload(hass, account_dict)

    later.assert_called_once()
    assert account_dict["display_reload_unsub"] is later.return_value


def test_display_reload_callback_reloads_entry():
    """The scheduled callback reloads the current entry."""
    account_dict = {"config_entry": MagicMock(entry_id="entry")}
    hass = MagicMock()
    hass.config_entries.async_get_entry.return_value = MagicMock()

    with patch("custom_components.alexa_media.display.async_call_later") as later:
        _schedule_display_reload(hass, account_dict)
        callback = later.call_args.args[2]
        callback(None)

    hass.async_create_task.assert_called_once()
    assert account_dict["display_reload_unsub"] is None


def test_display_reload_callback_skips_removed_entry():
    """A removed entry is not reloaded by a stale timer."""
    account_dict = {"config_entry": MagicMock(entry_id="entry")}
    hass = MagicMock()
    hass.config_entries.async_get_entry.return_value = None

    with patch("custom_components.alexa_media.display.async_call_later") as later:
        _schedule_display_reload(hass, account_dict)
        callback = later.call_args.args[2]
        callback(None)

    hass.async_create_task.assert_not_called()


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
    state.async_refresh = AsyncMock(side_effect=asyncio.TimeoutError)

    with patch(
        "custom_components.alexa_media.display.async_set_device_setting",
        new_callable=AsyncMock,
        return_value=False,
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

    with (
        patch(
            "custom_components.alexa_media.display.async_probe_display_settings",
            new_callable=AsyncMock,
            return_value=(
                {
                    SETTING_DISPLAY_POWER: "ON",
                    SETTING_ADAPTIVE_BRIGHTNESS: "OFF",
                },
                False,
            ),
        ) as probe,
        patch(
            "custom_components.alexa_media.switch.add_devices",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_add_devices,
    ):
        await async_setup_platform(hass, {"email": EMAIL}, MagicMock())

    probe.assert_awaited_once()
    switches = account_dict["entities"]["switch"][SERIAL]
    assert {"display_power", "adaptive_brightness"} <= set(switches)
    # The display switches are added unfiltered, after the filtered batch.
    display_batch = mock_add_devices.call_args_list[-1].args[1]
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
async def test_get_display_state_rechecks_unsupported_after_lock():
    """A concurrent probe that marked the device unsupported wins."""
    account_dict = {"display_states": {}, "display_locks": {}}
    lock = asyncio.Lock()
    await lock.acquire()
    account_dict["display_locks"][SERIAL] = lock

    task = asyncio.create_task(
        async_get_display_state(
            MagicMock(), account_dict, MagicMock(), _device(), MagicMock()
        )
    )
    await asyncio.sleep(0)
    account_dict.setdefault("display_unsupported", set()).add(SERIAL)
    lock.release()

    assert await task is None
    assert SERIAL not in account_dict["display_states"]


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
