"""Tests for Echo display controls."""

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
import pytest

from custom_components.alexa_media.const import DATA_ALEXAMEDIA
from custom_components.alexa_media.display import (
    SETTING_ADAPTIVE_BRIGHTNESS,
    SETTING_BRIGHTNESS,
    SETTING_DISPLAY_POWER,
    AlexaAdaptiveBrightnessSwitch,
    AlexaDisplayBrightness,
    AlexaDisplayPowerSwitch,
    DisplayState,
    _decode_setting,
    async_get_device_setting,
    async_get_display_state,
    async_set_device_setting,
    supports_display,
)

EMAIL = "test@example.com"  # noqa: S105
SERIAL = "G090XXXXXXXXXXXX"
SHOW_TYPE = "A1XWJRHALS1REP"  # Echo Show 5 (Gen2)
DOT_TYPE = "A3S5BH2HU6VAYF"  # Echo Dot (Gen2)


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


def test_supports_display_models():
    """Known display models are detected, plain speakers are not."""
    assert supports_display(_device())
    assert supports_display(_device("A2H4LV5GIZ1JFT"))  # Echo Dot Clock (Gen4)
    assert not supports_display(_device(DOT_TYPE))


def test_decode_setting():
    """Device settings are stored as JSON strings."""
    assert _decode_setting('"ON"') == "ON"
    assert _decode_setting("100") == 100
    assert _decode_setting("plain") == "plain"


@pytest.mark.asyncio
async def test_get_device_setting():
    """Reading a setting decodes the API response."""
    response = MagicMock()
    response.json = AsyncMock(return_value={"value": '"ON"'})

    with patch(
        "custom_components.alexa_media.display.AlexaAPI._static_request",
        new_callable=AsyncMock,
        return_value=response,
    ) as mock_request:
        value = await async_get_device_setting(
            MagicMock(), "account-id", SETTING_DISPLAY_POWER
        )

    assert value == "ON"
    mock_request.assert_awaited_once()
    assert mock_request.call_args.args[2] == (
        "/api/v1/devices/account-id/settings/displayPower"
    )


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
async def test_display_state_refresh_and_notify():
    """Refreshing loads all settings and notifies listeners."""
    state = _state()
    listener = MagicMock()
    state.async_add_listener(listener)

    async def _get(_login, _account_id, setting):
        return {
            SETTING_DISPLAY_POWER: "ON",
            SETTING_BRIGHTNESS: 42,
            SETTING_ADAPTIVE_BRIGHTNESS: "OFF",
        }[setting]

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


def test_adaptive_brightness_entity():
    """The adaptive brightness switch reflects the cached state."""
    state = _state()
    state._values[SETTING_ADAPTIVE_BRIGHTNESS] = "OFF"
    switch = AlexaAdaptiveBrightnessSwitch(state)

    assert not switch.is_on
    assert switch.available


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

    with patch(
        "custom_components.alexa_media.switch.add_devices",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_add_devices:
        await async_setup_platform(hass, {"email": EMAIL}, MagicMock())

    switches = account_dict["entities"]["switch"][SERIAL]
    assert {"display_power", "adaptive_brightness"} <= set(switches)
    # The display switches are added unfiltered, after the filtered batch.
    display_batch = mock_add_devices.call_args_list[-1].args[1]
    assert {type(switch) for switch in display_batch} == {
        AlexaDisplayPowerSwitch,
        AlexaAdaptiveBrightnessSwitch,
    }


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

    with patch(
        "custom_components.alexa_media.number.add_devices",
        new_callable=AsyncMock,
        return_value=True,
    ):
        await async_setup_platform(hass, {"email": EMAIL}, MagicMock())

    assert f"{SERIAL}_display_brightness" in account_dict["entities"]["number"]


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

    first = await async_get_display_state(
        MagicMock(), account_dict, login, device, client
    )
    second = await async_get_display_state(
        MagicMock(), account_dict, login, device, client
    )

    assert first is second
