"""Tests for contact sensor battery levels."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.alexa_media.const import (
    CONF_EXTENDED_ENTITY_DISCOVERY,
    DATA_ALEXAMEDIA,
)
from custom_components.alexa_media.sensor import (
    AlexaBatterySensor,
    create_battery_sensors,
)

ENTITY_ID = "contact-1"
DEVICE_NAME = "Back Door"
EMAIL = "test@example.com"  # noqa: S105


def _coordinator(value=87):
    coordinator = MagicMock()
    coordinator.data = {
        ENTITY_ID: [
            {
                "namespace": "Alexa.BatteryLevelSensor",
                "name": "batteryLevel",
                "value": value,
            }
        ]
    }
    return coordinator


def _details():
    return {"id": ENTITY_ID, "name": DEVICE_NAME, "battery_level": True}


def test_battery_sensor_value():
    """The battery sensor reads the coordinator state."""
    sensor = AlexaBatterySensor(_coordinator(), _details())

    assert sensor.native_value == 87
    assert sensor.unique_id == f"{ENTITY_ID}_battery"
    assert sensor.device_info["identifiers"] == {("alexa_media", ENTITY_ID)}


def test_battery_sensor_updates():
    """Coordinator updates are reflected in the battery sensor."""
    coordinator = _coordinator(87)
    sensor = AlexaBatterySensor(coordinator, _details())
    sensor.async_write_ha_state = MagicMock()
    coordinator.data[ENTITY_ID][0]["value"] = 42

    sensor._handle_coordinator_update()

    assert sensor.native_value == 42


@pytest.mark.asyncio
async def test_sensor_setup_creates_battery_sensor():
    """The sensor platform wires discovered contact batteries in setup."""
    from custom_components.alexa_media.sensor import async_setup_platform

    account_dict = {
        "devices": {
            "media_player": {},
            "temperature": [],
            "aiaqm": [],
            "binary_sensor": [_details()],
        },
        "entities": {"sensor": {}, "media_player": {}},
        "options": {CONF_EXTENDED_ENTITY_DISCOVERY: True},
        "coordinator": _coordinator(),
        "login_obj": MagicMock(),
    }
    hass = MagicMock()
    hass.data = {DATA_ALEXAMEDIA: {"accounts": {EMAIL: account_dict}}}

    with patch(
        "custom_components.alexa_media.sensor.add_devices",
        new_callable=AsyncMock,
        return_value=True,
    ):
        await async_setup_platform(hass, {"email": EMAIL}, MagicMock())

    assert isinstance(
        account_dict["entities"]["sensor"][ENTITY_ID]["Battery"],
        AlexaBatterySensor,
    )


def test_create_battery_sensors_only_for_supported_devices():
    """Only contact sensors advertising a battery capability get a sensor."""
    coordinator = _coordinator()
    account_dict = {
        "coordinator": coordinator,
        "entities": {"sensor": {}},
    }
    entities = [
        _details(),
        {"id": "contact-2", "name": "Front Door", "battery_level": False},
    ]

    sensors = create_battery_sensors(account_dict, entities)

    assert len(sensors) == 1
    assert account_dict["entities"]["sensor"][ENTITY_ID]["Battery"] is sensors[0]
