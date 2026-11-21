"""Guard against deprecated device registry APIs (Home Assistant 2026.8)."""

import ast
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

from homeassistant.helpers import device_registry as dr, frame
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.alexa_media.media_player import AlexaClient

COMPONENT = Path(__file__).parents[1] / "custom_components" / "alexa_media"


def make_client(friendly_name=None):
    """Return a client whose registered metadata is still stale."""
    client = AlexaClient(None, MagicMock(email="test@example.com"))
    client._device_type = "UNKNOWN"
    client._device_type_friendly_name = friendly_name
    client._device_family = "ECHO"
    client._device_serial_number = "SERIAL"
    client._device_name = "Living room"
    client._software_version = "13323246980"
    return client


def make_device(friendly_name="Echo Show 8 (3rd generation)"):
    """Return an inventory payload as returned by AlexaAPI."""
    return {
        "accountName": "Living room",
        "deviceFamily": "ECHO",
        "deviceType": "UNKNOWN",
        "deviceTypeFriendlyName": friendly_name,
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


def test_no_deprecated_device_registry_lookup():
    """Identifiers are unique per config entry; the old lookup is ambiguous."""
    offenders = []
    for path in COMPONENT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "async_get_device"
            ):
                offenders.append(f"{path.relative_to(COMPONENT)}:{node.lineno}")
    assert not offenders, offenders


async def test_refresh_does_not_report_deprecated_registry_usage(hass, caplog):
    """A refresh must not trigger the frame deprecation warning."""
    getattr(frame, "_REPORTED_INTEGRATIONS", set()).clear()
    caplog.set_level(logging.WARNING, logger="homeassistant.helpers.frame")

    client = make_client()
    config_entry = MockConfigEntry(domain="alexa_media")
    config_entry.add_to_hass(hass)
    registry = dr.async_get(hass)
    registered = registry.async_get_or_create(
        config_entry_id=config_entry.entry_id, **client.device_info
    )
    client.hass = hass
    # EntityPlatform assigns the device entry when the entity is added.
    client.device_entry = registered

    with patch.object(client, "schedule_update_ha_state"):
        await client.refresh(make_device(), skip_api=True)

    assert "async_get_device" not in caplog.text
    updated = registry.async_get(registered.id)
    assert (updated.model, updated.model_id, updated.hw_version) == (
        "Echo Show 8",
        "UNKNOWN",
        "3rd Gen",
    )
    assert client.device_entry is updated
    assert updated.identifiers == client.device_info["identifiers"]


async def test_refresh_before_registration_leaves_registry_to_hass(hass):
    """A refresh before the entity is registered must not write the registry."""
    client = make_client()
    client.hass = hass
    registry = dr.async_get(hass)

    with (
        patch.object(registry, "async_update_device") as update,
        patch.object(client, "schedule_update_ha_state"),
    ):
        await client.refresh(make_device(), skip_api=True)

    update.assert_not_called()
    assert client.device_entry is None
