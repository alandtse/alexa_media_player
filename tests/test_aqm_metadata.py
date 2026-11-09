"""Regression coverage for unitless AQM indices and stable entity identity."""

from inspect import signature
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.components.sensor.recorder import (
    _normalize_states,
    _wanted_statistics,
)
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import device_registry as dr, entity_registry as er
import pytest

from custom_components.alexa_media.sensor import AirQualitySensor

VOC = "Alexa.AirQuality.VolatileOrganicCompounds"
KEY = "air_quality_volatile_organic_compounds"
ROOT = Path(__file__).parents[1] / "custom_components" / "alexa_media"


def make_sensor(metric, unit=None, value=42):
    """Build a sensor using the real coordinator parsing path."""
    coordinator = MagicMock()
    coordinator.data = {
        "aqm-entity": [
            {
                "namespace": "Alexa.RangeController",
                "name": "rangeValue",
                "instance": "5",
                "value": value,
            }
        ]
    }
    sensor = AirQualitySensor(
        coordinator,
        "aqm-entity",
        "Office AQM",
        ("alexa_media", "serial"),
        metric,
        "5",
        unit,
    )
    sensor.platform = SimpleNamespace(
        platform_name="alexa_media",
        domain="sensor",
        platform_translations={},
        default_language_platform_translations={},
    )
    if hasattr(sensor, "platform_data"):
        sensor.platform_data = sensor.platform
    return sensor


@pytest.mark.parametrize("unit", [None, ""])
@pytest.mark.parametrize("value", [0, 42.5, 100, None])
def test_voc_unitless_measurement(unit, value, caplog):
    """Empty Amazon units stay unitless, numeric and eligible for statistics."""
    sensor = make_sensor(VOC, unit, value)
    assert sensor.device_class is None
    assert sensor.native_unit_of_measurement is None
    assert sensor.state_class == SensorStateClass.MEASUREMENT
    assert sensor.native_value == value
    assert sensor.state == value
    assert "not a valid unit" not in caplog.text
    assert sensor.icon == "mdi:air-filter"
    assert sensor.translation_key == KEY
    assert sensor.unique_id == "aqm-entity_volatile_organic_compounds"
    assert sensor.extra_state_attributes is None
    state = State("sensor.office_voc", "42.5", sensor.capability_attributes)
    wanted = _wanted_statistics([state])[state.entity_id]
    # HA versions use either a set or a typed statistics configuration.
    if isinstance(wanted, set):
        assert {"mean", "min", "max"} <= wanted
    else:
        assert {"mean", "min", "max"} <= wanted.types


@pytest.mark.parametrize(
    "metric,suffix,device_class,icon,unit",
    [
        (
            "IndoorAirQuality",
            "indoor_air_quality",
            SensorDeviceClass.AQI,
            "mdi:gauge",
            None,
        ),
        (
            "ParticulateMatter",
            "particulate_matter",
            SensorDeviceClass.PM25,
            "mdi:blur",
            "Alexa.Unit.Density.MicroGramsPerCubicMeter",
        ),
    ],
)
def test_other_aqm_metadata(metric, suffix, device_class, icon, unit):
    """IAQ retains its identity and classes; PM2.5 retains its icon and unit."""
    sensor = make_sensor(f"Alexa.AirQuality.{metric}", unit)
    assert sensor.unique_id == f"aqm-entity_{suffix}"
    assert sensor.device_class == device_class
    assert sensor.icon == icon
    assert sensor.state_class == SensorStateClass.MEASUREMENT
    assert sensor.device_info["identifiers"] == {("alexa_media", "serial")}


def test_voc_english_translations():
    """Keep the existing translation key and update English fallback copies."""
    for path in [ROOT / "strings.json", ROOT / "translations" / "en.json"]:
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["entity"]["sensor"][KEY] == {
            "name": "Volatile organic compounds index"
        }


async def test_existing_registry_identity(tmp_path):
    """Metadata refresh keeps a registered entity ID and user customizations."""
    hass = HomeAssistant(str(tmp_path))
    hass.config_entries = MagicMock(async_wait_initialized=AsyncMock())
    try:
        if hasattr(dr, "async_setup"):
            dr.async_setup(hass)
        await dr.async_load(hass)
        registry = er.async_get(hass)
        await registry.async_load()
        sensor = make_sensor(VOC)
        entry = registry.async_get_or_create(
            "sensor",
            "alexa_media",
            sensor.unique_id,
            suggested_object_id="office_volatile_organic_compounds",
            original_name="Volatile organic compounds",
            original_device_class="aqi",
        )
        registry.async_update_entity(entry.entity_id, name="My VOC", icon="mdi:leaf")
        refreshed = registry.async_get_or_create(
            "sensor",
            "alexa_media",
            sensor.unique_id,
            original_name="Volatile organic compounds index",
            original_device_class=sensor.device_class,
        )
        assert refreshed.entity_id == entry.entity_id
        assert refreshed.name == "My VOC"
        assert refreshed.icon == "mdi:leaf"
        assert refreshed.original_device_class is None
        assert refreshed.original_name == "Volatile organic compounds index"
        assert len(registry.entities) == 1
    finally:
        await hass.async_stop(force=True)


def test_voc_statistics_history():
    """Existing unitless AQI statistics accept new unclassified VOC readings."""
    entity_id = "sensor.office_voc"
    states = [
        (
            42.0,
            State(
                entity_id, "42", {"device_class": "aqi", "state_class": "measurement"}
            ),
        ),
        (43.0, State(entity_id, "43", {"state_class": "measurement"})),
    ]
    metadata = {entity_id: (1, {"unit_of_measurement": None, "unit_class": None})}
    kwargs = {}
    # HA added per-entity equivalent units after the minimum supported version.
    if "custom_units_for_entity" in signature(_normalize_states).parameters:
        kwargs["custom_units_for_entity"] = None
    result = _normalize_states(
        SimpleNamespace(data={}), metadata, states, entity_id, **kwargs
    )
    assert result[-1] == states
    assert result[-2] is None
