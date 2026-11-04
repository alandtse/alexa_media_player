"""Regression coverage for text-discovered AQM PM10 metrics."""

from copy import deepcopy
from unittest.mock import MagicMock

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
import pytest

from custom_components.alexa_media.alexa_entity import parse_alexa_entities
from custom_components.alexa_media.sensor import create_air_quality_sensors
from custom_components.alexa_media.switch import LEDIndicatorSwitch

UNIT = "Alexa.Unit.Density.MicroGramsPerCubicMeter"
LEGACY = {
    "CarbonMonoxide": "carbon_monoxide",
    "Humidity": "humidity",
    "IndoorAirQuality": "indoor_air_quality",
    "ParticulateMatter": "particulate_matter",
    "VolatileOrganicCompounds": "volatile_organic_compounds",
}


def range_cap(instance, value):
    """Build sanitized range discovery metadata."""
    return {
        "interfaceName": "Alexa.RangeController",
        "instance": instance,
        "properties": {
            "supported": [{"name": "rangeValue"}],
            "retrievable": True,
            "readOnly": True,
        },
        "resources": {"friendlyNames": [{"value": value}]},
        "configuration": {"unitOfMeasure": UNIT},
    }


@pytest.fixture
def appliance():
    """Keep all existing metrics alongside the captured PM10 text resource."""
    return {
        "entityId": "aqm-entity",
        "applianceId": "aqm-appliance",
        "friendlyName": "Office AQM",
        "modelName": "AQM",
        "friendlyDescription": "Amazon Indoor Air Quality Monitor",
        "applianceTypes": ["AIR_QUALITY_MONITOR"],
        "manufacturerName": "Amazon",
        "alexaDeviceIdentifierList": [{"dmsDeviceSerialNumber": "aqm-serial"}],
        "capabilities": [
            *[
                range_cap(str(i), {"assetId": f"Alexa.AirQuality.{metric}"})
                for i, metric in enumerate(LEGACY, 1)
            ],
            range_cap("7", {"text": "Particulate matter PM10"}),
            range_cap("9", {"text": "Unrelated range"}),
        ],
    }


@pytest.mark.parametrize("instance", ["7", 7, "27"])
async def test_pm10_discovery_and_state(appliance, instance):
    """PM10 uses its discovered instance and shares the unchanged AQM device."""
    appliance["capabilities"][-2]["instance"] = instance
    appliance["capabilities"][-2]["configuration"] = {}
    parsed = parse_alexa_entities([appliance])
    details = parsed["aiaqm"][0]
    assert len(details["sensors"]) == 6
    assert len(parsed["temperature"]) == 1
    coordinator = MagicMock()
    coordinator.data = {
        "aqm-entity": [
            {
                "namespace": "Alexa.RangeController",
                "name": "rangeValue",
                "instance": "9",
                "value": 999,
            },
            {
                "namespace": "Alexa.RangeController",
                "name": "rangeValue",
                "instance": instance,
                "value": 12.5,
            },
        ]
    }
    account = {"coordinator": coordinator, "entities": {"sensor": {}}}
    sensors = await create_air_quality_sensors(account, [details])
    pm10 = next(s for s in sensors if s.device_class == SensorDeviceClass.PM10)
    assert pm10.native_value == 12.5
    assert pm10.native_unit_of_measurement == "\u00b5g/m\u00b3"
    assert pm10.state_class == SensorStateClass.MEASUREMENT
    assert pm10.name == "PM10"
    assert pm10.unique_id == "aqm-entity_particulate_matter_p_m10"
    for sensor in sensors:
        assert sensor.device_info["identifiers"] == {("alexa_media", "aqm-serial")}
    for metric, suffix in LEGACY.items():
        sensor = next(
            s for s in sensors if s._sensor_type == f"Alexa.AirQuality.{metric}"
        )
        assert sensor.unique_id == f"aqm-entity_{suffix}"
    pm10.async_write_ha_state = MagicMock()
    coordinator.data["aqm-entity"][-1]["value"] = 0
    pm10._handle_coordinator_update()
    assert pm10.native_value == 0
    coordinator.data["aqm-entity"].pop()
    pm10._handle_coordinator_update()
    assert pm10.native_value is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("retrievable", False),
        ("readOnly", False),
        ("retrievable", None),
        ("readOnly", None),
        ("supported", [{"name": "other"}]),
    ],
)
def test_pm10_requires_readable_sensor(appliance, field, value):
    """Do not turn writable controls or unreadable ranges into PM10 sensors."""
    appliance["capabilities"][-2]["properties"][field] = value
    assert len(parse_alexa_entities([appliance])["aiaqm"][0]["sensors"]) == 5


def test_unrelated_text_and_absent_pm10_preserve_legacy(appliance):
    """Instance 7 alone does not identify PM10; older devices stay unchanged."""
    appliance["capabilities"][-2]["resources"] = {
        "friendlyNames": [{"value": {"text": "PM2.5"}}]
    }
    before = deepcopy(parse_alexa_entities([appliance]))
    appliance["capabilities"].pop(-2)
    assert parse_alexa_entities([appliance]) == before
    assert len(before["aiaqm"][0]["sensors"]) == 5


async def test_pm10_and_led_share_device_and_keep_independent_states(appliance):
    """Discover both features together and isolate range and toggle updates."""
    appliance["capabilities"].append(
        {
            "interfaceName": "Alexa.ToggleController",
            "instance": "11",
            "properties": {
                "supported": [{"name": "toggleState"}],
                "retrievable": True,
                "readOnly": False,
            },
            "resources": {"friendlyNames": [{"value": {"text": "LED"}}]},
        }
    )
    details = parse_alexa_entities([appliance])["aiaqm"][0]
    assert details["led_indicator_instance"] == "11"
    assert len(details["sensors"]) == 6
    coordinator = MagicMock()
    pm10_state = {
        "namespace": "Alexa.RangeController",
        "name": "rangeValue",
        "instance": "7",
        "value": 12.5,
    }
    led_state = {
        "namespace": "Alexa.ToggleController",
        "name": "toggleState",
        "instance": "11",
        "value": "ON",
    }
    coordinator.data = {"aqm-entity": [pm10_state, led_state]}
    sensors = await create_air_quality_sensors(
        {"coordinator": coordinator, "entities": {"sensor": {}}}, [details]
    )
    pm10 = next(s for s in sensors if s.device_class == SensorDeviceClass.PM10)
    led = LEDIndicatorSwitch(coordinator, MagicMock(), details)
    assert led.device_info["identifiers"] == pm10.device_info["identifiers"]
    assert led.is_on is True
    assert pm10.native_value == 12.5
    pm10.async_write_ha_state = MagicMock()
    led_state["value"] = "OFF"
    pm10._handle_coordinator_update()
    assert led.is_on is False
    assert pm10.native_value == 12.5
    pm10_state["value"] = 0
    pm10._handle_coordinator_update()
    assert pm10.native_value == 0
    assert led.is_on is False
    coordinator.data["aqm-entity"] = [pm10_state]
    assert led.is_on is None
    assert pm10.native_value == 0
