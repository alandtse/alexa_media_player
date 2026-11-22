"""Tests for the alarm and notification volume number."""

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.exceptions import HomeAssistantError
import pytest

from custom_components.alexa_media.const import DATA_ALEXAMEDIA
from custom_components.alexa_media.number import (
    AlexaNotificationVolume,
    async_setup_platform,
)

EMAIL = "test@example.com"  # noqa: S105
SERIAL = "G090XXXXXXXXXXXX"


@pytest.fixture
def mock_client():
    """Create a mock media player client."""
    client = MagicMock()
    client.available = True
    client.device_serial_number = SERIAL
    client.unique_id = SERIAL
    client.name = "Kitchen Echo"
    client._login = MagicMock(email=EMAIL)
    return client


@pytest.fixture
def mock_account_dict(mock_client):
    """Create a mock account dictionary with one Echo that reports a volume."""
    return {
        "devices": {
            "media_player": {
                SERIAL: {
                    "deviceType": "A3S5BH2HU6VAYF",
                    "notification_volume": 40,
                    "notification_software_version": "123456",
                },
                "OTHER": {"deviceType": "A3S5BH2HU6VAYF"},
            },
            "number": {SERIAL: {"notification_volume": True}},
        },
        "entities": {
            "media_player": {SERIAL: mock_client, "OTHER": MagicMock()},
            "number": {},
        },
    }


@pytest.fixture
def mock_hass(mock_account_dict):
    """Create a mock hass object."""
    hass = MagicMock()
    hass.data = {DATA_ALEXAMEDIA: {"accounts": {EMAIL: mock_account_dict}}}
    return hass


@pytest.fixture
def number(mock_hass, mock_client):
    """Create a number attached to the mock hass."""
    entity = AlexaNotificationVolume(mock_client)
    entity.hass = mock_hass
    entity.async_write_ha_state = MagicMock()
    return entity


@pytest.mark.asyncio
async def test_setup_creates_number_for_echo_with_volume(mock_hass, mock_account_dict):
    """Only the Echo that reported a volume gets a number."""
    with patch(
        "custom_components.alexa_media.number.add_devices",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_add_devices:
        assert await async_setup_platform(mock_hass, {"email": EMAIL}, MagicMock())
        await async_setup_platform(mock_hass, {"email": EMAIL}, MagicMock())

    numbers = mock_account_dict["entities"]["number"]
    assert list(numbers) == [SERIAL]
    assert numbers[SERIAL].unique_id == f"{SERIAL}_notification_volume"
    assert mock_add_devices.call_args_list[0].args[1] == [numbers[SERIAL]]
    assert mock_add_devices.call_args_list[1].args[1] == []


@pytest.mark.asyncio
async def test_setup_retries_numbers_after_registration_failure(
    mock_hass, mock_account_dict, mock_client
):
    """Retry both numbers after a failed add and skip them after a successful add."""
    mock_account_dict["login_obj"] = mock_client._login
    device = mock_account_dict["devices"]["media_player"][SERIAL]
    config = {"email": EMAIL}
    add_callback = MagicMock(side_effect=[RuntimeError("add failed"), None, None])
    numbers = mock_account_dict["entities"]["number"]
    display_state = MagicMock(client=mock_client)
    display_state.supports.return_value = True

    with (
        patch(
            "custom_components.alexa_media.number.can_probe_display",
            side_effect=lambda candidate: candidate is device,
        ),
        patch(
            "custom_components.alexa_media.number.async_get_display_state",
            new_callable=AsyncMock,
            return_value=display_state,
        ),
    ):
        assert not await async_setup_platform(mock_hass, config, add_callback)
        assert not numbers

        assert await async_setup_platform(mock_hass, config, add_callback)
        assert set(numbers) == {SERIAL, f"{SERIAL}_display_brightness"}
        assert add_callback.call_args_list[-2].args[0] == [numbers[SERIAL]]
        assert add_callback.call_args_list[-1].args[0] == [
            numbers[f"{SERIAL}_display_brightness"]
        ]

        add_callback.reset_mock()
        assert await async_setup_platform(mock_hass, config, add_callback)
        add_callback.assert_not_called()


def test_value_is_read_from_coordinator_data(number, mock_account_dict):
    """The value follows the latest poll."""
    assert number.native_value == 40
    mock_account_dict["devices"]["media_player"][SERIAL]["notification_volume"] = 70
    assert number.native_value == 70


def test_availability_follows_the_device(number, mock_client, mock_account_dict):
    """The number is unavailable while the Echo is, and current when it returns."""
    assert number.available
    mock_client.available = False
    assert not number.available
    mock_account_dict["devices"]["media_player"][SERIAL]["notification_volume"] = 15
    mock_client.available = True
    assert number.available
    assert number.native_value == 15


def test_unavailable_without_volume(number, mock_account_dict):
    """The number is unavailable when the volume isn't known."""
    del mock_account_dict["devices"]["media_player"][SERIAL]["notification_volume"]
    assert not number.available


@pytest.mark.asyncio
async def test_set_value_calls_api(number, mock_client, mock_account_dict):
    """Setting the value sends the device's details and updates the state."""
    with patch(
        "custom_components.alexa_media.number.AlexaAPI.set_notification_volume",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_set:
        await number.async_set_native_value(25.0)

    mock_set.assert_awaited_once_with(
        mock_client._login, SERIAL, "A3S5BH2HU6VAYF", "123456", 25
    )
    assert number.native_value == 25
    number.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_set_value_failure_raises(number):
    """A failed set raises and keeps the old value."""
    with (
        patch(
            "custom_components.alexa_media.number.AlexaAPI.set_notification_volume",
            new_callable=AsyncMock,
            return_value=False,
        ),
        pytest.raises(HomeAssistantError),
    ):
        await number.async_set_native_value(25.0)

    assert number.native_value == 40
    number.async_write_ha_state.assert_not_called()


@pytest.mark.asyncio
async def test_setup_survives_device_added_during_probe(
    mock_hass, mock_account_dict, mock_client
):
    """A discovery insert during the probe does not break the snapshot loop."""
    mock_account_dict["login_obj"] = mock_client._login
    device = mock_account_dict["devices"]["media_player"][SERIAL]
    display_state = MagicMock(client=mock_client)
    display_state.supports.return_value = True

    async def add_during_probe(*_args, **_kwargs):
        mock_account_dict["devices"]["media_player"]["NEW"] = {
            "serialNumber": "NEW",
            "deviceAccountId": "new-id",
        }
        return display_state

    with (
        patch(
            "custom_components.alexa_media.number.can_probe_display",
            side_effect=lambda candidate: candidate is device,
        ),
        patch(
            "custom_components.alexa_media.number.async_get_display_state",
            side_effect=add_during_probe,
        ),
    ):
        assert await async_setup_platform(mock_hass, {"email": EMAIL}, MagicMock())

    assert f"{SERIAL}_display_brightness" in mock_account_dict["entities"]["number"]
