"""
Alexa Devices Sensors.

SPDX-License-Identifier: Apache-2.0

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""

import json
import logging
from typing import Any, Dict, List, Optional, Text, TypedDict, Union

from alexapy import AlexaAPI, AlexaLogin, hide_serial
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


def has_capability(
    appliance: Dict[Text, Any], interface_name: Text, property_name: Text
) -> bool:
    """Determine if an appliance from the Alexa network details offers a particular interface with enough support that is worth adding to Home Assistant.

    Args:
        appliance(Dict[Text, Any]): An appliance from a call to AlexaAPI.get_network_details
        interface_name(Text): One of the interfaces documented by the Alexa Smart Home Skills API
        property_name(Text): The property that matches the interface name.

    """
    for cap in appliance["capabilities"]:
        props = cap.get("properties")
        if (
            cap["interfaceName"] == interface_name
            and props
            and (props["retrievable"] or props["proactivelyReported"])
        ):
            for prop in props["supported"]:
                if prop["name"] == property_name:
                    return True
    return False


def is_hue_v1(appliance: Dict[Text, Any]) -> bool:
    """Determine if an appliance is managed via the Philips Hue v1 Hub.

    This check catches old Philips Hue bulbs and hubs, but critically, it also catches things pretending to be older
    Philips Hue bulbs and hubs. This includes things exposed by HA to Alexa using the emulated_hue integration.
    """
    return appliance.get("manufacturerName") == "Royal Philips Electronics"


def is_local(appliance: Dict[Text, Any]) -> bool:
    """Test whether locally connected.

    connectedVia is a flag that determines which Echo devices holds the connection. Its blank for
    skill derived devices and includes an Echo name for zigbee and local devices. This is used to limit
    the scope of what devices will be discovered. This is mainly present to prevent loops with the official Alexa
    integration. There is probably a better way to prevent that, but this works.
    """
    return appliance["connectedVia"]


def is_alexa_guard(appliance: Dict[Text, Any]) -> bool:
    """Is the given appliance the guard alarm system of an echo."""
    return appliance["modelName"] == "REDROCK_GUARD_PANEL" and has_capability(
        appliance, "Alexa.SecurityPanelController", "armState"
    )


def is_temperature_sensor(appliance: Dict[Text, Any]) -> bool:
    """Is the given appliance the temperature sensor of an Echo."""
    return (
        is_local(appliance)
        and appliance["manufacturerName"] == "Amazon"
        and has_capability(appliance, "Alexa.TemperatureSensor", "temperature")
    )


def is_light(appliance: Dict[Text, Any]) -> bool:
    """Is the given appliance a light controlled locally by an Echo."""
    return (
        is_local(appliance)
        and "LIGHT" in appliance["applianceTypes"]
        and has_capability(appliance, "Alexa.PowerController", "powerState")
    )


def get_friendliest_name(appliance: Dict[Text, Any]) -> Text:
    """Find the best friendly name. Alexa seems to store manual renames in aliases. Prefer that one."""
    aliases = appliance.get("aliases", [])
    for alias in aliases:
        friendly = alias.get("friendlyName")
        if friendly:
            return friendly
    return appliance["friendlyName"]


def get_device_serial(appliance: Dict[Text, Any]) -> Optional[Text]:
    """Find the device serial id if it is present."""
    alexa_device_id_list = appliance.get("alexaDeviceIdentifierList", [])
    for alexa_device_id in alexa_device_id_list:
        if isinstance(alexa_device_id, dict):
            return alexa_device_id.get("dmsDeviceSerialNumber")
    return None


class AlexaEntity(TypedDict):
    """Class for Alexaentity."""

    id: Text
    appliance_id: Text
    name: Text
    is_hue_v1: bool


class AlexaLightEntity(AlexaEntity):
    """Class for AlexaLightEntity."""

    brightness: bool
    color: bool
    color_temperature: bool


class AlexaTemperatureEntity(AlexaEntity):
    """Class for AlexaTemperatureEntity."""

    device_serial: Text


class AlexaEntities(TypedDict):
    """Class for holding entities."""

    light: List[AlexaLightEntity]
    guard: List[AlexaEntity]
    temperature: List[AlexaTemperatureEntity]


def parse_alexa_entities(network_details: Optional[Dict[Text, Any]]) -> AlexaEntities:
    """Turn the network details into a list of useful entities with the important details extracted."""
    lights = []
    guards = []
    temperature_sensors = []
    location_details = network_details["locationDetails"]["locationDetails"]
    for location in location_details.values():
        amazon_bridge_details = location["amazonBridgeDetails"]["amazonBridgeDetails"]
        for bridge in amazon_bridge_details.values():
            appliance_details = bridge["applianceDetails"]["applianceDetails"]
            for appliance in appliance_details.values():
                processed_appliance = {
                    "id": appliance["entityId"],
                    "appliance_id": appliance["applianceId"],
                    "name": get_friendliest_name(appliance),
                    "is_hue_v1": is_hue_v1(appliance),
                }
                if is_alexa_guard(appliance):
                    guards.append(processed_appliance)
                elif is_temperature_sensor(appliance):
                    serial = get_device_serial(appliance)
                    processed_appliance["device_serial"] = (
                        serial if serial else appliance["entityId"]
                    )
                    temperature_sensors.append(processed_appliance)
                elif is_light(appliance):
                    processed_appliance["brightness"] = has_capability(
                        appliance, "Alexa.BrightnessController", "brightness"
                    )
                    processed_appliance["color"] = has_capability(
                        appliance, "Alexa.ColorController", "color"
                    )
                    processed_appliance["color_temperature"] = has_capability(
                        appliance,
                        "Alexa.ColorTemperatureController",
                        "colorTemperatureInKelvin",
                    )
                    lights.append(processed_appliance)

    return {"light": lights, "guard": guards, "temperature": temperature_sensors}


class AlexaCapabilityState(TypedDict):
    """Class for AlexaCapabilityState."""

    name: Text
    namespace: Text
    value: Union[int, Text, TypedDict]


AlexaEntityData = Dict[Text, List[AlexaCapabilityState]]


async def get_entity_data(
    login_obj: AlexaLogin, entity_ids: List[Text]
) -> AlexaEntityData:
    """Get and process the entity data into a more usable format."""
    raw = await AlexaAPI.get_entity_state(login_obj, entity_ids=entity_ids)
    entities = {}
    device_states = raw.get("deviceStates")
    if device_states:
        for device_state in device_states:
            entity_id = device_state["entity"]["entityId"]
            entities[entity_id] = []
            for cap_state in device_state["capabilityStates"]:
                entities[entity_id].append(json.loads(cap_state))
    return entities


def parse_temperature_from_coordinator(
    coordinator: DataUpdateCoordinator, entity_id: Text
) -> Optional[Text]:
    """Get the temperature of an entity from the coordinator data."""
    value = parse_value_from_coordinator(
        coordinator, entity_id, "Alexa.TemperatureSensor", "temperature"
    )
    return value.get("value") if value and "value" in value else None


def parse_brightness_from_coordinator(
    coordinator: DataUpdateCoordinator, entity_id: Text
) -> int:
    """Get the brightness in the range 0-100."""
    return parse_value_from_coordinator(
        coordinator, entity_id, "Alexa.BrightnessController", "brightness"
    )


def parse_power_from_coordinator(
    coordinator: DataUpdateCoordinator, entity_id: Text
) -> Text:
    """Get the power state of the entity."""
    return parse_value_from_coordinator(
        coordinator, entity_id, "Alexa.PowerController", "powerState"
    )


def parse_guard_state_from_coordinator(
    coordinator: DataUpdateCoordinator, entity_id: Text
):
    """Get the guard state from the coordinator data."""
    return parse_value_from_coordinator(
        coordinator, entity_id, "Alexa.SecurityPanelController", "armState"
    )


def parse_value_from_coordinator(
    coordinator: DataUpdateCoordinator, entity_id: Text, namespace: Text, name: Text
) -> Any:
    """Parse out values from coordinator for Alexa Entities."""
    if coordinator.data and entity_id in coordinator.data:
        for cap_state in coordinator.data[entity_id]:
            if (
                cap_state.get("namespace") == namespace
                and cap_state.get("name") == name
            ):
                return cap_state.get("value")
    else:
        _LOGGER.debug("Coordinator has no data for %s", hide_serial(entity_id))
    return None
