"""Tests for entity naming and device metadata."""

from unittest.mock import MagicMock

from custom_components.alexa_media.binary_sensor import AlexaContact
from custom_components.alexa_media.light import AlexaLight
from custom_components.alexa_media.switch import SmartSwitch


def test_light_is_main_entity_of_its_device():
    """The light uses its device name and exposes the integration domain."""
    light = AlexaLight(
        MagicMock(),
        MagicMock(),
        {
            "id": "light-1",
            "name": "Desk Lamp",
            "brightness": True,
            "color": False,
            "color_temperature": False,
        },
    )

    assert light.name is None
    assert light.device_info["identifiers"] == {("alexa_media", "light-1")}
    assert light.device_info["name"] == "Desk Lamp"


def test_contact_is_main_entity_of_its_device():
    """The contact sensor uses its device name and keeps its metadata."""
    contact = AlexaContact(MagicMock(), {"id": "contact-1", "name": "Back Door"})

    assert contact.name is None
    assert contact.device_info["identifiers"] == {("alexa_media", "contact-1")}
    assert contact.device_info["name"] == "Back Door"


def test_smart_switch_is_main_entity_of_its_device():
    """The smart switch uses its device name and integration domain."""
    switch = SmartSwitch(
        MagicMock(),
        MagicMock(),
        {"id": "switch-1", "name": "Coffee Maker"},
    )

    assert switch.name is None
    assert switch.device_info["identifiers"] == {("alexa_media", "switch-1")}
    assert switch.device_info["name"] == "Coffee Maker"
