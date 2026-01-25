"""
Alexa Devices Entities.

SPDX-License-Identifier: Apache-2.0

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""

from __future__ import annotations

from datetime import datetime
import json
import logging
import re
from typing import Any, Optional, TypedDict

from alexapy import AlexaAPI, AlexaLogin
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .helpers import safe_get

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
    namespace = safe_get(appliance, ["driverIdentity", "namespace"], "")
    return namespace and namespace == "SKILL"


def is_known_ha_bridge(appliance: dict[str, Any] | None) -> bool:
    """Test whether a bridge appliance is a known HA bridge to avoid creating loops."""

    if appliance is None:
        return False

    if appliance.get("manufacturerName") in ("t0bst4r", "Matterbridge"):
        return True

    # Identify Matter bridge hubs regardless of manufacturerName
    if "HUB" in appliance.get("applianceTypes", []):
        driver_ns = safe_get(appliance, ["driverIdentity", "namespace"], "")
        driver_id = safe_get(appliance, ["driverIdentity", "identifier"], "")
        if driver_ns == "AAA" and driver_id == "SonarCloudService":
            interfaces = {
                cap.get("interfaceName") for cap in appliance.get("capabilities", [])
            }
            if (
                "Alexa.Matter.NodeOperationalCredentials.FabricManagement" in interfaces
                or "Alexa.Commissionable" in interfaces
            ):
                return True

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
    """Is the given appliance the Amazon Indoor Air Quality Monitor (AIAQM)."""
    return (
        appliance.get("friendlyDescription") == "Amazon Indoor Air Quality Monitor"
        and "AIR_QUALITY_MONITOR" in appliance.get("applianceTypes", [])
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


def get_device_serial(appliance: dict[str, Any]) -> str | None:
    """Find the device serial id if it is present."""
    alexa_device_id_list = appliance.get("alexaDeviceIdentifierList", [])
    for alexa_device_id in alexa_device_id_list:
        if isinstance(alexa_device_id, dict):
            return alexa_device_id.get("dmsDeviceSerialNumber")
    return None


def get_device_bridge(
    appliance: dict[str, Any], appliances: dict[str, dict[str, Any]]
) -> dict[str, Any] | None:
    """Find the bridge device for an appliance connected through e.g. a Matter bridge."""

    appliance_id = appliance.get("applianceId")
    if not isinstance(appliance_id, str) or "#" not in appliance_id:
        return None

    # HA Matter Hub bridged endpoints are identified by applianceId prefixes
    # of the form AAA_SonarCloudService_<bridgeId>#<childId>.
    bridge_id, _sep, _child = appliance_id.partition("#")

    if not bridge_id.startswith("AAA_SonarCloudService_"):
        return None

    bridge = appliances.get(bridge_id)
    return bridge if isinstance(bridge, dict) else None


AlexaEntityData = dict[str, list["AlexaCapabilityState"]]


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


class AlexaTemperatureEntity(TypedDict, total=False):
    device_serial: str
    is_aiaqm: bool


class AlexaAirQualityEntity(AlexaEntity):
    """Class for AlexaAirQualityEntity."""

    device_serial: str


class AlexaAIAQMEntity(AlexaEntity):
    """Entity-backed "device" representing an Amazon Indoor Air Quality Monitor."""

    device_serial: str
    sensors: list[dict[str, str]]


class AlexaBinaryEntity(AlexaEntity):
    """Class for AlexaBinaryEntity."""

    battery_level: bool


class AlexaEntities(TypedDict):
    """Class for Alexa Entities."""

    light: list[AlexaLightEntity]
    guard: list[AlexaEntity]
    temperature: list[AlexaTemperatureEntity]
    air_quality: list[AlexaAirQualityEntity]
    aiaqm: list[AlexaAIAQMEntity]
    binary_sensor: list[AlexaBinaryEntity]
    smart_switch: list[AlexaEntity]


class AlexaCapabilityState(TypedDict, total=False):
    """Class for AlexaCapabilityState."""

    name: str
    namespace: str
    value: int | float | str | dict[str, Any]
    instance: str
    timeOfSample: str
    uncertaintyInMilliseconds: int


def parse_alexa_entities(
    network_details: list[dict[str, Any]] | None,
    debug: bool = False,
) -> AlexaEntities:
    # pylint: disable=too-many-locals
    """Turn the network details into a list of useful entities with the important details extracted."""
    temperature_sensors: list[AlexaTemperatureEntity] = []
    air_quality_sensors: list[AlexaAirQualityEntity] = []
    aiaqm_entities: list[AlexaAIAQMEntity] = []
    contact_sensors: list[AlexaBinaryEntity] = []
    switches: list[AlexaEntity] = []
    guards: list[AlexaEntity] = []
    lights: list[AlexaLightEntity] = []

    function_name = "parse_alexa_entities()"

    if not network_details:
        return {
            "light": lights,
            "guard": guards,
            "temperature": temperature_sensors,
            "air_quality": air_quality_sensors,
            "aiaqm": aiaqm_entities,
            "binary_sensor": contact_sensors,
            "smart_switch": switches,
        }

    network_dict: dict[str, dict[str, Any]] = {}
    if debug:
        _LOGGER.debug("Processing network_details")

    # Build an applianceId → appliance map first so bridged devices
    # can resolve their bridge regardless of list ordering.
    for appliance in network_details:
        appliance_id = appliance.get("applianceId")
        if appliance_id:
            network_dict[appliance_id] = appliance

    for appliance in network_details:
        device_bridge = get_device_bridge(appliance, network_dict)

        bridge_label = (
            device_bridge.get("friendlyName") or device_bridge.get("manufacturerName")
            if device_bridge
            else None
        )

        appliance_id = str(appliance.get("applianceId", ""))

        # Only log a bridge check when:
        # - we found a bridge, OR
        # - ADV debug is enabled AND the appliance looks like a bridge candidate
        if bridge_label is not None or (debug and "#" in appliance_id):
            _LOGGER.debug(
                "%s: Checking device bridge: %s",
                appliance.get("friendlyName"),
                bridge_label or "<none>",
            )

        # ADV-only: only log resolution for cases where it might apply
        if debug and "#" in appliance_id:
            bridge_id = device_bridge.get("applianceId") if device_bridge else None
            _LOGGER.debug(
                "[%s] [ADV] Matter bridge resolution: appliance=%s → bridge=%s (connectedVia=%s, bridge=%s)",
                function_name,
                appliance_id,
                bridge_id,
                appliance.get("connectedVia"),
                bridge_label,
            )

        if is_known_ha_bridge(device_bridge):
            if debug:
                _LOGGER.debug(
                    '[%s] [ADV] Skipping bridged Matter device "%s" (%s) via known bridge: %s (%s)',
                    function_name,
                    appliance.get("friendlyName"),
                    appliance.get("applianceId"),
                    bridge_label,
                    device_bridge.get("applianceId") if device_bridge else None,
                )
            else:
                _LOGGER.debug(
                    'Skipping bridged Matter device "%s" via known bridge "%s"',
                    appliance.get("friendlyName"),
                    bridge_label or "<unknown>",
                )
            continue

        processed_appliance: AlexaEntity = {
            "id": appliance["entityId"],
            "appliance_id": appliance["applianceId"],
            "name": get_friendliest_name(appliance),
            "is_hue_v1": is_hue_v1(appliance),
        }

        if is_alexa_guard(appliance):
            _LOGGER.debug("Added Alexa Guard: %s", processed_appliance["name"])
            guards.append(processed_appliance)

        elif is_temperature_sensor(appliance):
            if debug:
                _LOGGER.debug(
                    "Added temperature sensor: %s", processed_appliance["name"]
                )
            serial = get_device_serial(appliance)
            temp_entity: AlexaTemperatureEntity = {
                **processed_appliance,
                "device_serial": serial if serial else appliance["entityId"],
            }
            temperature_sensors.append(temp_entity)

        elif is_air_quality_sensor(appliance):
            if debug:
                _LOGGER.debug("Added AIAQM sensor: %s", processed_appliance["name"])

            serial = get_device_serial(appliance)
            device_serial = serial if serial else appliance["entityId"]

            # Build a list of sub-sensors we can read via AlexaAPI.get_entity_state.
            # AIAQM metrics are exposed via Alexa.RangeController(rangeValue) with an
            # instance per metric. Some accounts/devices use numeric instances, so
            # we derive the sensor type from the friendlyName assetId/text.
            sensors: list[dict[str, str]] = []
            for cap in appliance.get("capabilities", []):
                if cap.get("interfaceName") != "Alexa.RangeController":
                    continue

                # Must support numeric rangeValue to be a sensor.
                supported = safe_get(cap, ["properties", "supported"], [])
                if not isinstance(supported, list) or not any(
                    isinstance(p, dict) and p.get("name") == "rangeValue"
                    for p in supported
                ):
                    continue

                instance = cap.get("instance")
                if instance is None or instance == "":
                    continue
                if not isinstance(instance, str):
                    if isinstance(instance, (int, float)):
                        instance = str(instance)
                    else:
                        continue

                unit = safe_get(cap, ["configuration", "unitOfMeasure"], "") or ""

                resources = (
                    cap.get("resources", {})
                    if isinstance(cap.get("resources"), dict)
                    else {}
                )
                friendly = (
                    resources.get("friendlyNames", [])
                    if isinstance(resources.get("friendlyNames"), list)
                    else []
                )

                sensor_type: str | None = None
                for entry in friendly:
                    if not isinstance(entry, dict):
                        continue
                    value_obj = entry.get("value")
                    asset_id = None
                    if isinstance(value_obj, dict):
                        asset_id = value_obj.get("assetId")
                    else:
                        asset_id = entry.get("assetId")

                    # Only treat Alexa.AirQuality assetIds as real AIAQM sensors.
                    # Text-only friendlyNames (e.g. @type "text") must be ignored to avoid
                    # creating extra sensors such as PM10.
                    if isinstance(asset_id, str) and asset_id.startswith(
                        "Alexa.AirQuality."
                    ):
                        sensor_type = asset_id
                        break

                if not sensor_type:
                    continue
                sensors.append(
                    {
                        "sensorType": str(sensor_type),
                        "instance": instance,
                        "unit": str(unit),
                    }
                )

            # Always register the AIAQM device (even if no sub-sensors are exposed).
            aiaqm_entity: AlexaAIAQMEntity = {
                **processed_appliance,
                "device_serial": device_serial,
                "sensors": sensors,
            }
            aiaqm_entities.append(aiaqm_entity)

            # Backwards compatibility: also expose as air_quality for existing paths.
            aq_entity: AlexaAirQualityEntity = {
                **processed_appliance,
                "device_serial": device_serial,
            }
            air_quality_sensors.append(aq_entity)

            # AIAQM also has temperature; ensure it gets created and grouped with AIAQM.
            temp_entity: AlexaTemperatureEntity = {
                **processed_appliance,
                "device_serial": device_serial,
                "is_aiaqm": True,
            }
            temperature_sensors.append(temp_entity)
        elif is_switch(appliance):
            if debug:
                _LOGGER.debug("Added switch: %s", processed_appliance["name"])
            switches.append(processed_appliance)

        elif is_light(appliance):
            if debug:
                _LOGGER.debug("Added light %s", processed_appliance["name"])
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
            light_entity: AlexaLightEntity = {
                **processed_appliance,
                "brightness": processed_appliance["brightness"],
                "color": processed_appliance["color"],
                "color_temperature": processed_appliance["color_temperature"],
            }
            lights.append(light_entity)

        elif is_contact_sensor(appliance):
            if debug:
                _LOGGER.debug("Added contact sensor: %s", processed_appliance["name"])
            processed_appliance["battery_level"] = has_capability(
                appliance, "Alexa.BatteryLevelSensor", "batteryLevel"
            )
            binary_entity: AlexaBinaryEntity = {
                **processed_appliance,
                "battery_level": processed_appliance["battery_level"],
            }
            contact_sensors.append(binary_entity)

        else:
            if debug:
                _LOGGER.debug("Unsupported entity: %s", processed_appliance["name"])

    return {
        "light": lights,
        "guard": guards,
        "temperature": temperature_sensors,
        "air_quality": air_quality_sensors,
        "aiaqm": aiaqm_entities,
        "binary_sensor": contact_sensors,
        "smart_switch": switches,
    }


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
                entity_id = safe_get(device_state, ["entity", "entityId"])
                if entity_id:
                    entities[entity_id] = []
                    cap_states = device_state.get("capabilityStates", [])
                    for cap_state in cap_states:
                        entities[entity_id].append(json.loads(cap_state))
    return entities


def parse_temperature_from_coordinator(
    coordinator: DataUpdateCoordinator,
    entity_id: str,
    debug: bool = False,
) -> dict[str, Any] | None:
    """Get the temperature of an entity from the coordinator data."""
    temperature = parse_value_from_coordinator(
        coordinator,
        entity_id,
        "Alexa.TemperatureSensor",
        "temperature",
        debug=debug,
    )
    if debug:
        _LOGGER.debug("parse_temperature_from_coordinator: %s", temperature)
    return temperature


def parse_air_quality_from_coordinator(
    coordinator: DataUpdateCoordinator,
    entity_id: str,
    instance_id: str,
    debug: bool = False,
) -> int | float | str | None:
    """Get the air quality of an entity from the coordinator data."""
    value = parse_value_from_coordinator(
        coordinator,
        entity_id,
        "Alexa.RangeController",
        "rangeValue",
        instance=instance_id,
        debug=debug,
    )
    return value


def parse_brightness_from_coordinator(
    coordinator: DataUpdateCoordinator, entity_id: str, since: datetime
) -> int | None:
    """Get the brightness in the range 0-100."""
    return parse_value_from_coordinator(
        coordinator,
        entity_id,
        "Alexa.BrightnessController",
        "brightness",
        since=since,
    )


def parse_color_temp_from_coordinator(
    coordinator: DataUpdateCoordinator, entity_id: str, since: datetime
) -> int | None:
    """Get the color temperature in kelvin."""
    return parse_value_from_coordinator(
        coordinator,
        entity_id,
        "Alexa.ColorTemperatureController",
        "colorTemperatureInKelvin",
        since=since,
    )


def parse_color_from_coordinator(
    coordinator: DataUpdateCoordinator, entity_id: str, since: datetime
) -> tuple[float, float, float] | None:
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
) -> str | None:
    """Get the power state of the entity."""
    return parse_value_from_coordinator(
        coordinator,
        entity_id,
        "Alexa.PowerController",
        "powerState",
        since=since,
    )


def parse_guard_state_from_coordinator(
    coordinator: DataUpdateCoordinator, entity_id: str
) -> str | None:
    """Get the guard state from the coordinator data."""
    return parse_value_from_coordinator(
        coordinator, entity_id, "Alexa.SecurityPanelController", "armState"
    )


def parse_detection_state_from_coordinator(
    coordinator: DataUpdateCoordinator, entity_id: str
) -> bool | None:
    """Get the detection state from the coordinator data."""
    return parse_value_from_coordinator(
        coordinator, entity_id, "Alexa.ContactSensor", "detectionState"
    )


def parse_value_from_coordinator(
    coordinator: DataUpdateCoordinator,
    entity_id: str,
    namespace: str,
    name: str,
    since: datetime | None = None,
    instance: str | None = None,
    *,
    debug: bool = False,
) -> Any:
    """Parse out values from coordinator for Alexa Entities."""
    if coordinator.data and entity_id in coordinator.data:
        for cap_state in coordinator.data[entity_id]:
            cap_instance = cap_state.get("instance")
            instance_match = instance is None or (
                cap_instance is not None and str(cap_instance) == str(instance)
            )
            if (
                cap_state.get("namespace") == namespace
                and cap_state.get("name") == name
                and instance_match
            ):
                if is_cap_state_still_acceptable(cap_state, since):
                    return cap_state.get("value")
                if debug:
                    _LOGGER.debug(
                        "Coordinator data for %s is too old to be returned.",
                        entity_id,
                    )
                return None
    else:
        if debug:
            _LOGGER.debug(
                "Coordinator has no data yet for %s, %s, %s, %s",
                entity_id,
                namespace,
                name,
                instance,
            )
    return None


def is_cap_state_still_acceptable(
    cap_state: dict[str, Any], since: datetime | None
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
