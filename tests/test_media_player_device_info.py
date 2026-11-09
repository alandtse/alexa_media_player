"""Test Alexa device model and hardware metadata without network calls."""

from unittest.mock import MagicMock

import pytest

from custom_components.alexa_media.media_player import AlexaClient


def make_client(device_type="A3RMGO6LYLH7YN", friendly_name=None):
    """Return a client with device metadata populated."""
    client = AlexaClient(None, MagicMock(email="test@example.com"))
    client._device_type = device_type
    client._device_type_friendly_name = friendly_name
    client._device_family = "ECHO"
    client._device_serial_number = "SERIAL"
    client._device_name = "Living room"
    client._software_version = "13323246980"
    return client


@pytest.mark.parametrize(
    ("description", "model", "hardware"),
    [
        ("Echo (Gen4)", "Echo", "4th Gen"),
        ("Echo (4th Gen)", "Echo", "4th Gen"),
        ("Echo (4th generation)", "Echo", "4th Gen"),
        ("  Echo Show 8 (Gen2)  ", "Echo Show 8", "2nd Gen"),
        ("Echo Show 8", "Echo Show 8", None),
        ("Echo (Gen1)", "Echo", "1st Gen"),
        ("Echo (Gen3)", "Echo", "3rd Gen"),
        ("Echo (Gen11)", "Echo", "11th Gen"),
        ("Echo (Gen12)", "Echo", "12th Gen"),
        ("Echo (Gen13)", "Echo", "13th Gen"),
        ("Echo (Gen21)", "Echo", "21st Gen"),
        ("Unknown speaker 4", "Unknown speaker 4", None),
        ("Unknown (2024)", "Unknown (2024)", None),
        ("Unknown (GenX)", "Unknown (GenX)", None),
        ("Unknown Gen4 Edition", "Unknown Gen4 Edition", None),
        ("(Gen4)", "(Gen4)", None),
        ("Echo (Gen0)", "Echo (Gen0)", None),
    ],
)
def test_amazon_model_description(description, model, hardware):
    """Prefer Amazon's description without inferring generations from numbers."""
    info = make_client(friendly_name=description).device_info
    assert info["model"] == model
    assert info["hw_version"] == hardware
    assert info["model_id"] == "A3RMGO6LYLH7YN"


@pytest.mark.parametrize("friendly_name", [None, "", " \t ", 42])
@pytest.mark.parametrize(
    ("device_type", "model", "hardware"),
    [
        ("A3RMGO6LYLH7YN", "Echo", "4th Gen"),
        ("A15996VY63BQ2D", "Echo Show 8", "2nd Gen"),
        ("UNKNOWN", "ECHO UNKNOWN", None),
    ],
)
def test_model_fallbacks(friendly_name, device_type, model, hardware):
    """Missing or blank friendly names use the map, then family and type."""
    info = make_client(device_type, friendly_name).device_info
    assert info["model"] == model
    assert info["hw_version"] == hardware
    assert info["model_id"] == device_type


def test_device_info_preserves_identity_and_versions():
    """Keep generation separate from the model and preserve existing metadata."""
    assert make_client().device_info == {
        "identifiers": {("alexa_media", "SERIAL")},
        "name": "Living room",
        "manufacturer": "Amazon",
        "model": "Echo",
        "model_id": "A3RMGO6LYLH7YN",
        "hw_version": "4th Gen",
        "serial_number": "SERIAL",
        "sw_version": "13323246980",
    }


def test_unknown_type_with_amazon_name():
    """Amazon can describe devices absent from MODEL_IDS."""
    info = make_client("UNKNOWN", "New speaker").device_info
    assert info["model"] == "New speaker"
    assert info["hw_version"] is None


def test_second_account_keeps_registry_identifier():
    """Model metadata does not change the account-specific unique ID."""
    client = make_client()
    client._second_account_index = 1
    client._login.email = "test@example.com"
    assert client.device_info["identifiers"] == {("alexa_media", client.unique_id)}
    assert client.device_info["serial_number"] == "SERIAL"


@pytest.mark.parametrize("name", [None, "", "Living room"])
async def test_refresh_updates_friendly_name(name):
    """Read fresh inventory metadata, including removal, independently of name."""
    client = make_client()
    device = {
        "accountName": name,
        "deviceFamily": "ECHO",
        "deviceType": "UNKNOWN",
        "deviceTypeFriendlyName": "Echo Show 8 (3rd generation)",
        "serialNumber": "SERIAL",
        "appDeviceList": [],
        "deviceOwnerCustomerId": "CUSTOMER",
        "softwareVersion": "13323246980",
        "online": False,
        "capabilities": [],
        "clusterMembers": [],
        "parentClusters": [],
        "auth_info": {
            "authenticated": True,
            "canAccessPrimeMusicContent": False,
            "customerEmail": "test@example.com",
            "customerId": "CUSTOMER",
            "customerName": "Test",
        },
    }
    await client.refresh(device, skip_api=True)
    assert client.device_info["name"] == name
    assert client.device_info["model"] == "Echo Show 8"
    assert client.device_info["hw_version"] == "3rd Gen"
    device.pop("deviceTypeFriendlyName")
    await client.refresh(device, skip_api=True)
    assert client.device_info["model"] == "ECHO UNKNOWN"
    assert client.device_info["hw_version"] is None
