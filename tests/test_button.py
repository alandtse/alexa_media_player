"""Tests for the Echo restart button."""

from unittest.mock import AsyncMock, MagicMock, patch

from alexapy import AlexapyLoginError
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
import pytest

from custom_components.alexa_media.button import (
    AlexaRestartButton,
    async_setup_platform,
    async_unload_entry,
)
from custom_components.alexa_media.const import DATA_ALEXAMEDIA

EMAIL = "test@example.com"  # noqa: S105
SERIAL = "G090XXXXXXXXXXXX"
DEVICE_TYPE = "A3S5BH2HU6VAYF"


@pytest.fixture
def mock_client():
    """Create a mock media player client."""
    client = MagicMock()
    client.available = True
    client.unique_id = SERIAL
    client.name = "Kitchen Echo"
    client.device_serial_number = SERIAL
    client._login = MagicMock(email=EMAIL)
    return client


@pytest.fixture
def mock_account_dict(mock_client):
    """Create a mock account dictionary with one restart-capable Echo."""
    return {
        "devices": {
            "media_player": {
                SERIAL: {
                    "deviceType": DEVICE_TYPE,
                    "capabilities": ["ALEXA_DEVICE_REBOOT"],
                },
                "OTHER": {
                    "deviceType": DEVICE_TYPE,
                    "capabilities": ["MUSIC_SKILL"],
                },
            }
        },
        "entities": {
            "media_player": {SERIAL: mock_client, "OTHER": MagicMock()},
            "button": {},
        },
    }


@pytest.fixture
def mock_hass(mock_account_dict):
    """Create a mock hass object."""
    hass = MagicMock()
    hass.data = {DATA_ALEXAMEDIA: {"accounts": {EMAIL: mock_account_dict}}}
    return hass


@pytest.fixture
def button(mock_hass, mock_client, mock_account_dict):
    """Create a restart button attached to the mock account."""
    entity = AlexaRestartButton(
        mock_client, mock_account_dict["devices"]["media_player"][SERIAL]
    )
    entity.hass = mock_hass
    return entity


@pytest.mark.asyncio
async def test_setup_creates_button_for_capable_device(mock_hass, mock_account_dict):
    """Only the Echo advertising the reboot capability gets a button."""
    with patch(
        "custom_components.alexa_media.button.add_devices",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_add_devices:
        assert await async_setup_platform(mock_hass, {"email": EMAIL}, MagicMock())
        await async_setup_platform(mock_hass, {"email": EMAIL}, MagicMock())

    buttons = mock_account_dict["entities"]["button"]
    assert list(buttons) == [SERIAL]
    assert buttons[SERIAL].unique_id == f"{SERIAL}_restart"
    assert mock_add_devices.call_args_list[0].args[1] == [buttons[SERIAL]]
    assert mock_add_devices.call_args_list[1].args[1] == []


@pytest.mark.asyncio
async def test_setup_does_not_store_button_when_registration_fails(
    mock_hass, mock_account_dict
):
    """A failed registration must not hide the button from the next retry."""
    with patch(
        "custom_components.alexa_media.button.add_devices",
        new_callable=AsyncMock,
        return_value=False,
    ):
        assert not await async_setup_platform(mock_hass, {"email": EMAIL}, MagicMock())

    assert mock_account_dict["entities"]["button"] == {}


@pytest.mark.asyncio
async def test_setup_waits_for_media_player(mock_hass, mock_account_dict):
    """Do not create a button before its media player exists."""
    mock_account_dict["entities"]["media_player"].pop(SERIAL)

    with pytest.raises(ConfigEntryNotReady):
        await async_setup_platform(mock_hass, {"email": EMAIL}, MagicMock())


@pytest.mark.asyncio
async def test_press_calls_restart(button, mock_client):
    """Pressing the button restarts the Echo."""
    with patch(
        "custom_components.alexa_media.button.async_restart_device",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_restart:
        await button.async_press()

    mock_client.check_login_changes.assert_called_once()
    mock_restart.assert_awaited_once_with(mock_client._login, DEVICE_TYPE, SERIAL)


@pytest.mark.asyncio
async def test_press_raises_when_restart_fails(button):
    """A rejected restart is surfaced to Home Assistant."""
    with patch(
        "custom_components.alexa_media.button.async_restart_device",
        new_callable=AsyncMock,
        return_value=False,
    ):
        with pytest.raises(HomeAssistantError):
            await button.async_press()


@pytest.mark.asyncio
async def test_press_raises_when_login_fails(button):
    """A login error is surfaced and triggers the relogin flow."""
    with (
        patch(
            "custom_components.alexa_media.button.async_restart_device",
            new_callable=AsyncMock,
            side_effect=AlexapyLoginError("not logged in"),
        ),
        patch(
            "custom_components.alexa_media.button.report_relogin_required"
        ) as mock_report,
    ):
        with pytest.raises(HomeAssistantError):
            await button.async_press()

    mock_report.assert_called_once()


@pytest.mark.asyncio
async def test_added_to_hass_tracks_media_player_state(button, mock_client):
    """The button refreshes when the media player availability changes."""
    mock_client.entity_id = "media_player.kitchen"
    button.async_on_remove = MagicMock()

    with patch(
        "custom_components.alexa_media.button.async_track_state_change_event"
    ) as mock_track:
        await button.async_added_to_hass()

    mock_track.assert_called_once()
    assert mock_track.call_args.args[1] == ["media_player.kitchen"]


@pytest.mark.asyncio
async def test_unload_removes_buttons(mock_hass, mock_account_dict, button):
    """Unloading the platform removes the buttons."""
    button.async_remove = AsyncMock()
    mock_account_dict["entities"]["button"][SERIAL] = button
    entry = MagicMock()
    entry.data = {"email": EMAIL}

    assert await async_unload_entry(mock_hass, entry)
    button.async_remove.assert_awaited_once()
