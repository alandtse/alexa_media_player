"""
Alexa Devices Sensors.

SPDX-License-Identifier: Apache-2.0

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""

from datetime import datetime
import json
import logging
import re
from typing import Any, Optional, TypedDict, Union

from alexapy import AlexaAPI, AlexaLogin, hide_serial
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


def has_capability(
    appliance: dict[str, Any], interface_name: str, property_name: str
) -> bool:
    """Determine if an appliance from the Alexa network details offers a particular interface with enough support that is worth adding to Home Assistant.

    Args:
        appliance(dict[str, Any]): An appliance from a call to AlexaAPI.get_network_details
        interface_name(str): One of the interfaces documented by the Alexa Smart Home Skills API
        property_name(str): The property that matches the interface name.

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


def is_hue_v1(appliance: dict[str, Any]) -> bool:
    """Determine if an appliance is managed via the Philips Hue v1 Hub.

    This check catches old Philips Hue bulbs and hubs, but critically, it also catches things pretending to be older
    Philips Hue bulbs and hubs. This includes things exposed by HA to Alexa using the emulated_hue integration.
    """
    return appliance.get("manufacturerName") == "Royal Philips Electronics"


def is_skill(appliance: dict[str, Any]) -> bool:
    namespace = appliance.get("driverIdentity", {}).get("namespace", "")
    return namespace and namespace == "SKILL"


def is_known_ha_bridge(appliance: Optional[dict[str, Any]]) -> bool:
    """Test whether a bridge appliance is a known HA bridge to avoid creating loops."""

    if appliance is None:
        return False

    if appliance.get("manufacturerName") in ("t0bst4r", "Matterbridge"):
        return True

    # If we want to exclude all Matter devices (these can always be added
    # directly to HA instead of going through AMP), we could test for a
    # networkInterfaceIdentifier of type "MATTER" or capabilities on the
    # "Alexa.Matter.NodeOperationalCredentials.FabricManagement" interface.

    return False


def is_local(appliance: dict[str, Any]) -> bool:
    """Test whether locally connected.

    This is mainly present to prevent loops with the official Alexa integration.
    There is probably a better way to prevent that, but this works.
    """

    if appliance.get("connectedVia"):
        # connectedVia is a flag that determines which Echo devices holds the connection. Its blank for
        # skill derived devices and includes an Echo name for zigbee and local devices.
        return True

    # This catches the Echo/AVS devices. connectedVia isn't reliable in this case.
    # Only the first appears to get that set.
    if "ALEXA_VOICE_ENABLED" in appliance.get("applianceTypes", []):
        return not is_skill(appliance)

    # Ledvance/Sengled bulbs connected via bluetooth are hard to detect as locally connected
    # Amazon devices are not local but bypassing the local check allows for control by the integration
    # There is probably a better way, but this works for now.
    manufacturerNames = ["Ledvance", "Sengled", "Amazon"]
    if appliance.get("manufacturerName") in manufacturerNames:
        return not is_skill(appliance)

    # Zigbee devices are guaranteed to be local and have a particular pattern of id
    zigbee_pattern = re.compile(
        "AAA_SonarCloudService_([0-9A-F][0-9A-F]:){7}[0-9A-F][0-9A-F]", flags=re.I
    )
    return zigbee_pattern.fullmatch(appliance.get("applianceId", "")) is not None


def is_alexa_guard(appliance: dict[str, Any]) -> bool:
    """Is the given appliance the guard alarm system of an echo."""
    return appliance["modelName"] == "REDROCK_GUARD_PANEL" and has_capability(
        appliance, "Alexa.SecurityPanelController", "armState"
    )


def is_temperature_sensor(appliance: dict[str, Any]) -> bool:
    """Is the given appliance the temperature sensor of an Echo."""
    return (
        is_local(appliance)
        and has_capability(appliance, "Alexa.TemperatureSensor", "temperature")
        and appliance["friendlyDescription"] != "Amazon Indoor Air Quality Monitor"
    )


# Checks if air quality sensor
def is_air_quality_sensor(appliance: dict[str, Any]) -> bool:
    """Is the given appliance the Air Quality Sensor."""
    return (
        appliance["friendlyDescription"] == "Amazon Indoor Air Quality Monitor"
        and "AIR_QUALITY_MONITOR" in appliance.get("applianceTypes", [])
        and has_capability(appliance, "Alexa.TemperatureSensor", "temperature")
        and has_capability(appliance, "Alexa.RangeController", "rangeValue")
    )


def is_light(appliance: dict[str, Any]) -> bool:
    """Is the given appliance a light controlled locally by an Echo."""
    return (
        is_local(appliance)
        and (
            "LIGHT" in appliance.get("applianceTypes", [])
            or (
                "SMARTPLUG" in appliance.get("applianceTypes", [])
                and appliance.get("customerDefinedDeviceType") == "LIGHT"
            )
        )
        and has_capability(appliance, "Alexa.PowerController", "powerState")
    )


def is_contact_sensor(appliance: dict[str, Any]) -> bool:
    """Is the given appliance a contact sensor controlled locally by an Echo."""
    return (
        is_local(appliance)
        and "CONTACT_SENSOR" in appliance.get("applianceTypes", [])
        and has_capability(appliance, "Alexa.ContactSensor", "detectionState")
    )


def is_switch(appliance: dict[str, Any]) -> bool:
    """Is the given appliance a switch controlled locally by an Echo, which is not redeclared as a light."""
    return (
        is_local(appliance)
        and (
            "SMARTPLUG" in appliance.get("applianceTypes", [])
            or "SWITCH" in appliance.get("applianceTypes", [])
        )
        and appliance.get("customerDefinedDeviceType") != "LIGHT"
        and has_capability(appliance, "Alexa.PowerController", "powerState")
    )


def get_friendliest_name(appliance: dict[str, Any]) -> str:
    """Find the best friendly name. Alexa seems to store manual renames in aliases. Prefer that one."""
    aliases = appliance.get("aliases", [])
    for alias in aliases:
        friendly = alias.get("friendlyName")
        if friendly:
            return friendly
    return appliance["friendlyName"]


def get_device_serial(appliance: dict[str, Any]) -> Optional[str]:
    """Find the device serial id if it is present."""
    alexa_device_id_list = appliance.get("alexaDeviceIdentifierList", [])
    for alexa_device_id in alexa_device_id_list:
        if isinstance(alexa_device_id, dict):
            return alexa_device_id.get("dmsDeviceSerialNumber")
    return None


def get_device_bridge(
    appliance: dict[str, Any], appliances: dict[str, dict[str, Any]]
) -> Optional[dict[str, Any]]:
    """Find the bridge device for an appliance connected through e.g. a Matter bridge"""
    if not appliance.get("connectedVia"):
        # The appliance cannot be Matter if it does not connect to an Echo device
        return None

    # We expect the bridged devices to look like "AAA_SonarCloudService_UUID#DEVICENUM"
    bridged_device_pattern = re.compile(
        "(AAA_SonarCloudService_[a-f0-9\\-]+)#[0-9]+", flags=re.I
    )

    match = bridged_device_pattern.fullmatch(appliance.get("applianceId", ""))
    if match is None:
        return None

    # We expect the bridge to share the prefix without the device num
    return appliances[match.group(1)]


class AlexaEntity(TypedDict):
    """Class for Alexaentity."""

    id: str
    appliance_id: str
    name: str
    is_hue_v1: bool


class AlexaLightEntity(AlexaEntity):
    """Class for AlexaLightEntity."""

    brightness: bool
    color: bool
    color_temperature: bool


class AlexaTemperatureEntity(AlexaEntity):
    """Class for AlexaTemperatureEntity."""

    device_serial: str


class AlexaAirQualityEntity(AlexaEntity):
    """Class for AlexaAirQualityEntity."""

    device_serial: str


class AlexaBinaryEntity(AlexaEntity):
    """Class for AlexaBinaryEntity."""

    battery_level: bool


class AlexaEntities(TypedDict):
    """Class for holding entities."""

    light: list[AlexaLightEntity]
    guard: list[AlexaEntity]
    temperature: list[AlexaTemperatureEntity]
    air_quality: list[AlexaAirQualityEntity]
    binary_sensor: list[AlexaBinaryEntity]
    smart_switch: list[AlexaEntity]


def parse_alexa_entities(network_details: Optional[dict[str, Any]]) -> AlexaEntities:
    # pylint: disable=too-many-locals
    """Turn the network details into a list of useful entities with the important details extracted."""
    lights = []
    guards = []
    temperature_sensors = []
    air_quality_sensors = []
    contact_sensors = []
    switches = []

    if not network_details:
        return {
            "light": lights,
            "guard": guards,
            "temperature": temperature_sensors,
            "air_quality": air_quality_sensors,
            "binary_sensor": contact_sensors,
            "smart_switch": switches,
        }
    network_dict = {}
    for appliance in network_details:
        network_dict[appliance["applianceId"]] = appliance

    for appliance in network_details:
        device_bridge = get_device_bridge(appliance, network_dict)
        if is_known_ha_bridge(device_bridge):
            _LOGGER.debug("Found Home Assistant bridge, skipping %s", appliance)
            continue

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
        # Code for Amazon Smart Air Quality Monitor
        elif is_air_quality_sensor(appliance):
            serial = get_device_serial(appliance)
            processed_appliance["device_serial"] = (
                serial if serial else appliance["entityId"]
            )
            # create array of air quality sensors. We must store the instance id against
            # the assetId so we know which sensors are which.
            sensors = []
            if appliance["friendlyDescription"] == "Amazon Indoor Air Quality Monitor":
                for cap in appliance["capabilities"]:
                    instance = cap.get("instance")
                    if not instance:
                        continue

                    friendlyName = cap["resources"].get("friendlyNames")
                    for entry in friendlyName:
                        assetId = entry["value"].get("assetId")
                        if not assetId or not assetId.startswith("Alexa.AirQuality"):
                            continue

                        unit = cap["configuration"]["unitOfMeasure"]
                        sensor = {
                            "sensorType": assetId,
                            "instance": instance,
                            "unit": unit,
                        }
                        sensors.append(sensor)
                        _LOGGER.debug("AIAQM sensor detected %s", sensor)
            processed_appliance["sensors"] = sensors

            # Add as both temperature and air quality sensor
            temperature_sensors.append(processed_appliance)
            air_quality_sensors.append(processed_appliance)
        elif is_switch(appliance):
            switches.append(processed_appliance)
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
        elif is_contact_sensor(appliance):
            processed_appliance["battery_level"] = has_capability(
                appliance, "Alexa.BatteryLevelSensor", "batteryLevel"
            )
            contact_sensors.append(processed_appliance)
        else:
            _LOGGER.debug("Found unsupported device %s", appliance)

    return {
        "light": lights,
        "guard": guards,
        "temperature": temperature_sensors,
        "air_quality": air_quality_sensors,
        "binary_sensor": contact_sensors,
        "smart_switch": switches,
    }


class AlexaCapabilityState(TypedDict):
    """Class for AlexaCapabilityState."""

    name: str
    namespace: str
    value: Union[int, str, TypedDict]


AlexaEntityData = dict[str, list[AlexaCapabilityState]]


async def get_entity_data(
    login_obj: AlexaLogin, entity_ids: list[str]
) -> AlexaEntityData:
    """Get and process the entity data into a more usable format."""

    entities = {}
    if entity_ids:
        raw = await AlexaAPI.get_entity_state(login_obj, entity_ids=entity_ids)
        device_states = raw.get("deviceStates", []) if isinstance(raw, dict) else None
        if device_states:
            for device_state in device_states:
                entity_id = device_state.get("entity", {}).get("entityId")
                if entity_id:
                    entities[entity_id] = []
                    cap_states = device_state.get("capabilityStates", [])
                    for cap_state in cap_states:
                        entities[entity_id].append(json.loads(cap_state))
    return entities


def parse_temperature_from_coordinator(
    coordinator: DataUpdateCoordinator, entity_id: str
) -> Optional[str]:
    """Get the temperature of an entity from the coordinator data."""
    temperature = parse_value_from_coordinator(
        coordinator, entity_id, "Alexa.TemperatureSensor", "temperature"
    )
    _LOGGER.debug("parse_temperature_from_coordinator: %s", temperature)
    return temperature


def parse_air_quality_from_coordinator(
    coordinator: DataUpdateCoordinator, entity_id: str, instance_id: str
) -> Optional[str]:
    """Get the air quality of an entity from the coordinator data."""
    value = parse_value_from_coordinator(
        coordinator,
        entity_id,
        "Alexa.RangeController",
        "rangeValue",
        instance=instance_id,
    )
    return value


def parse_brightness_from_coordinator(
    coordinator: DataUpdateCoordinator, entity_id: str, since: datetime
) -> Optional[int]:
    """Get the brightness in the range 0-100."""
    return parse_value_from_coordinator(
        coordinator, entity_id, "Alexa.BrightnessController", "brightness", since
    )


def parse_color_temp_from_coordinator(
    coordinator: DataUpdateCoordinator, entity_id: str, since: datetime
) -> Optional[int]:
    """Get the color temperature in kelvin."""
    return parse_value_from_coordinator(
        coordinator,
        entity_id,
        "Alexa.ColorTemperatureController",
        "colorTemperatureInKelvin",
        since,
    )


def parse_color_from_coordinator(
    coordinator: DataUpdateCoordinator, entity_id: str, since: datetime
) -> Optional[tuple[float, float, float]]:
    """Get the color as a tuple of (hue, saturation, brightness)."""
    value = parse_value_from_coordinator(
        coordinator, entity_id, "Alexa.ColorController", "color", since
    )
    if value is not None:
        hue = value.get("hue", 0)
        saturation = value.get("saturation", 0)
        return hue, saturation, 1
    return None


def parse_power_from_coordinator(
    coordinator: DataUpdateCoordinator, entity_id: str, since: datetime
) -> Optional[str]:
    """Get the power state of the entity."""
    return parse_value_from_coordinator(
        coordinator, entity_id, "Alexa.PowerController", "powerState", since
    )


def parse_guard_state_from_coordinator(
    coordinator: DataUpdateCoordinator, entity_id: str
) -> Optional[str]:
    """Get the guard state from the coordinator data."""
    return parse_value_from_coordinator(
        coordinator, entity_id, "Alexa.SecurityPanelController", "armState"
    )


def parse_detection_state_from_coordinator(
    coordinator: DataUpdateCoordinator, entity_id: str
) -> Optional[bool]:
    """Get the detection state from the coordinator data."""
    return parse_value_from_coordinator(
        coordinator, entity_id, "Alexa.ContactSensor", "detectionState"
    )


def parse_value_from_coordinator(
    coordinator: DataUpdateCoordinator,
    entity_id: str,
    namespace: str,
    name: str,
    since: Optional[datetime] = None,
    instance: str = None,
) -> Any:
    """Parse out values from coordinator for Alexa Entities."""
    if coordinator.data and entity_id in coordinator.data:
        for cap_state in coordinator.data[entity_id]:
            if (
                cap_state.get("namespace") == namespace
                and cap_state.get("name") == name
                and (cap_state.get("instance") == instance or instance is None)
            ):
                if is_cap_state_still_acceptable(cap_state, since):
                    return cap_state.get("value")
                _LOGGER.debug(
                    "Coordinator data for %s is too old to be returned.",
                    hide_serial(entity_id),
                )
                return None
    else:
        _LOGGER.debug("Coordinator has no data for %s", hide_serial(entity_id))
    return None


def is_cap_state_still_acceptable(
    cap_state: dict[str, Any], since: Optional[datetime]
) -> bool:
    """Determine if a particular capability state is still usable given its age."""
    if since is not None:
        formatted_time_of_sample = cap_state.get("timeOfSample")
        if formatted_time_of_sample:
            try:
                time_of_sample = datetime.strptime(
                    formatted_time_of_sample, "%Y-%m-%dT%H:%M:%S%z"
                )
                return time_of_sample >= since
            except ValueError:
                pass
    return True
