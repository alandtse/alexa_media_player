"""Tests for the entity categories of the Echo switches and select."""

from unittest.mock import MagicMock

from homeassistant.helpers.entity import EntityCategory
import pytest

from custom_components.alexa_media.select import AmazonKidsChildSelect
from custom_components.alexa_media.switch import (
    AmazonKidsSwitch,
    DNDSwitch,
    RepeatSwitch,
    ShuffleSwitch,
)


@pytest.fixture
def client():
    """Create a mock Echo media player client."""
    client = MagicMock()
    client.device_serial_number = "serial"
    client.unique_id = "uid"
    client._login.email = "test@example.com"
    return client


@pytest.mark.parametrize("switch_class", [DNDSwitch, ShuffleSwitch, RepeatSwitch])
def test_media_switches_have_no_entity_category(client, switch_class):
    """Do Not Disturb, Shuffle and Repeat are primary controls."""
    assert switch_class(client).entity_category is None


def test_amazon_kids_switch_is_config(client):
    """The Amazon Kids switch is a configuration entity."""
    switch = AmazonKidsSwitch(MagicMock(), client._login, client, "echo")
    assert switch.entity_category is EntityCategory.CONFIG


def test_amazon_kids_select_is_config(client):
    """The Amazon Kids child select is a configuration entity."""
    select = AmazonKidsChildSelect(MagicMock(), client._login, client, "echo")
    assert select.entity_category is EntityCategory.CONFIG
