"""
Alexa Devices Sensors.

SPDX-License-Identifier: Apache-2.0

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""

import datetime
import logging
from typing import Callable, ClassVar, Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature, __version__ as HA_VERSION
from homeassistant.core import callback
from homeassistant.exceptions import ConfigEntryNotReady, NoEntitySpecifiedError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt
from packaging import version

from . import (
    CONF_EMAIL,
    CONF_EXCLUDE_DEVICES,
    CONF_INCLUDE_DEVICES,
    DATA_ALEXAMEDIA,
    DOMAIN as ALEXA_DOMAIN,
    hide_email,
    hide_serial,
)
from .alexa_entity import (
    parse_air_quality_from_coordinator,
    parse_temperature_from_coordinator,
)
from .const import (
    ALEXA_AIR_QUALITY_DEVICE_CLASS,
    ALEXA_ICON_CONVERSION,
    ALEXA_ICON_DEFAULT,
    ALEXA_UNIT_CONVERSION,
    CONF_DEBUG,
    RECURRING_DAY,
    RECURRING_PATTERN,
    RECURRING_PATTERN_ISO_SET,
)
from .helpers import add_devices, alarm_just_dismissed, is_http2_enabled, safe_get

_LOGGER = logging.getLogger(__name__)

LOCAL_TIMEZONE = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo


async def async_setup_platform(hass, config, add_devices_callback, discovery_info=None):
    # pylint: disable=too-many-locals
    """Set up the Alexa sensor platform."""
    devices: list[AlexaMediaNotificationSensor] = []
    SENSOR_TYPES = {  # pylint: disable=invalid-name
        "Alarm": AlarmSensor,
        "Timer": TimerSensor,
        "Reminder": ReminderSensor,
    }
    account = None
    if config:
        account = config.get(CONF_EMAIL)
    if account is None and discovery_info:
        account = safe_get(discovery_info, ["config", CONF_EMAIL])
    if account is None:
        raise ConfigEntryNotReady
    include_filter = config.get(CONF_INCLUDE_DEVICES, [])
    exclude_filter = config.get(CONF_EXCLUDE_DEVICES, [])
    debug = bool(config.get(CONF_DEBUG, False))
    account_dict = hass.data[DATA_ALEXAMEDIA]["accounts"][account]
    _LOGGER.debug("%s: Loading sensors", hide_email(account))
    if "sensor" not in account_dict["entities"]:
        (hass.data[DATA_ALEXAMEDIA]["accounts"][account]["entities"]["sensor"]) = {}
    for key, device in account_dict["devices"]["media_player"].items():
        if key not in account_dict["entities"]["media_player"]:
            _LOGGER.debug(
                "%s: Media player %s not loaded yet; delaying load",
                hide_email(account),
                hide_serial(key),
            )
            raise ConfigEntryNotReady
        if key not in (account_dict["entities"]["sensor"]):
            (account_dict["entities"]["sensor"][key]) = {}
            for n_type, class_ in SENSOR_TYPES.items():
                notifications = account_dict.get("notifications") or {}
                key_notifications = notifications.get(key, {})
                n_type_dict = key_notifications.get(n_type, {})
                if (
                    n_type in ("Alarm", "Timer")
                    and "TIMERS_AND_ALARMS" in device["capabilities"]
                ):
                    alexa_client = class_(
                        account_dict["entities"]["media_player"][key],
                        n_type_dict,
                        account,
                        debug=debug,
                    )
                elif n_type in ("Reminder") and "REMINDERS" in device["capabilities"]:
                    alexa_client = class_(
                        account_dict["entities"]["media_player"][key],
                        n_type_dict,
                        account,
                        debug=debug,
                    )
                else:
                    continue
                _LOGGER.debug(
                    "%s: Found %s %s sensor (%s) with next: %s",
                    hide_email(account),
                    hide_serial(key),
                    n_type,
                    len(n_type_dict.keys()),
                    alexa_client.state,
                )
                devices.append(alexa_client)
                (account_dict["entities"]["sensor"][key][n_type]) = alexa_client
        else:
            for alexa_client in account_dict["entities"]["sensor"][key].values():
                _LOGGER.debug(
                    "%s: Skipping already added device: %s",
                    hide_email(account),
                    alexa_client,
                )

    temperature_sensors = []
    temperature_entities = safe_get(account_dict, ["devices", "temperature"], [])
    if temperature_entities:
        temperature_sensors = await create_temperature_sensors(
            account_dict, temperature_entities, debug=debug
        )

    # AQM Sensors
    air_quality_sensors = []
    aiaqm_entities = safe_get(account_dict, ["devices", "aiaqm"], [])
    if aiaqm_entities:
        air_quality_sensors = await create_air_quality_sensors(
            account_dict, aiaqm_entities, debug=debug
        )

    return await add_devices(
        hide_email(account),
        devices + temperature_sensors + air_quality_sensors,
        add_devices_callback,
        include_filter,
        exclude_filter,
    )


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Set up the Alexa sensor platform by config_entry."""
    return await async_setup_platform(
        hass, config_entry.data, async_add_devices, discovery_info=None
    )


async def async_unload_entry(hass, entry) -> bool:
    """Unload a config entry."""
    account = entry.data[CONF_EMAIL]
    account_dict = hass.data[DATA_ALEXAMEDIA]["accounts"][account]
    _LOGGER.debug("Attempting to unload sensors")

    for key, sensors in list(account_dict["entities"]["sensor"].items()):
        for sensor_key, device in list(sensors.items()):
            if isinstance(device, dict):
                # Air_Quality stores sensors in a nested dict
                for nested_key, nested_sensor in list(device.items()):
                    _LOGGER.debug("Removing %s", nested_sensor)
                    await nested_sensor.async_remove()
                    device.pop(nested_key, None)
                sensors.pop(sensor_key, None)
                continue

            _LOGGER.debug("Removing %s", device)
            await device.async_remove()
            sensors.pop(sensor_key, None)

        if not sensors:
            account_dict["entities"]["sensor"].pop(key, None)

    return True


async def create_temperature_sensors(
    account_dict,
    temperature_entities,
    debug: bool = False,
):
    """Create temperature sensors."""
    devices = []
    coordinator = account_dict["coordinator"]

    for temp in temperature_entities:
        if debug:
            _LOGGER.debug(
                "Creating entity %s for a temperature sensor with name %s (%s)",
                temp["id"],
                temp["name"],
                temp,
            )

        serial = temp["device_serial"]

        # Temperature can be from an Echo OR from an AIAQM endpoint.
        # If it's AIAQM, attach the sensor to the synthetic AIAQM HA device
        # so all AIAQM entities group under one HA device.
        is_aiaqm = bool(temp.get("is_aiaqm"))
        if is_aiaqm:
            device_ident = (ALEXA_DOMAIN, serial)
            aiaqm_device_serial = serial
        else:
            device_ident = lookup_device_info(account_dict, serial)
            aiaqm_device_serial = None

        sensor = TemperatureSensor(
            coordinator,
            temp["id"],
            temp["name"],
            device_ident,
            device_serial=aiaqm_device_serial,
            debug=debug,
        )

        account_dict["entities"]["sensor"].setdefault(serial, {})
        account_dict["entities"]["sensor"][serial]["Temperature"] = sensor
        devices.append(sensor)

    return devices


async def create_air_quality_sensors(
    account_dict, air_quality_entities, debug: bool = False
):
    devices = []
    coordinator = account_dict["coordinator"]

    for temp in air_quality_entities:
        _LOGGER.debug(
            "Creating sensors for %s id: %s",
            temp["name"],
            temp["id"],
        )
        subsensors = temp.get("sensors")
        if not isinstance(subsensors, list) or not subsensors:
            _LOGGER.debug(
                "Skipping AIAQM %s (%s): no parsed subsensors found",
                temp.get("name"),
                temp.get("id"),
            )
            continue

        last_index = len(subsensors) - 1
        seen_sensor_types: set[str] = set()

        # Each AIAQM has 5 different sensors.
        for idx, subsensor in enumerate(subsensors):
            prefix = "└─" if idx == last_index else "├─"
            sensor_type = subsensor.get("sensorType")
            instance = subsensor.get("instance")
            unit = subsensor.get("unit", "")

            if sensor_type in seen_sensor_types:
                _LOGGER.debug(
                    "%sSkipping duplicate AQM sensorType %s (instance=%s)",
                    prefix,
                    sensor_type,
                    instance,
                )
                continue
            if sensor_type:
                seen_sensor_types.add(sensor_type)

            if not sensor_type or instance is None:
                _LOGGER.debug(
                    "%sSkipping AIAQM subsensor missing sensorType/instance: %s",
                    prefix,
                    subsensor,
                )
                continue

            serial = temp.get("device_serial")
            if not serial:
                _LOGGER.debug(
                    "Skipping AIAQM subsensor %s: missing device_serial",
                    temp.get("name"),
                )
                continue
            device_ident = (ALEXA_DOMAIN, serial)
            _LOGGER.debug(
                " %s AQM sensor: %s",
                prefix,
                sensor_type.rsplit(".", 1)[-1],
            )
            sensor = AirQualitySensor(
                coordinator,
                temp["id"],
                temp["name"],
                device_ident,
                sensor_type,
                instance,
                unit,
                device_serial=serial,
                debug=debug,
            )
            account_dict["entities"]["sensor"].setdefault(serial, {})
            account_dict["entities"]["sensor"][serial].setdefault("Air_Quality", {})
            account_dict["entities"]["sensor"][serial]["Air_Quality"][
                sensor.unique_id
            ] = sensor
            devices.append(sensor)
    return devices


def lookup_device_info(account_dict, device_serial):
    """Get the device to use for a given Echo based on a given device serial id.

    This may return nothing as there is no guarantee that a given temperature sensor
    is actually attached to an Echo.
    """
    for key, mediaplayer in account_dict["entities"]["media_player"].items():
        if (
            key == device_serial
            and mediaplayer.device_info
            and "identifiers" in mediaplayer.device_info
        ):
            for ident in mediaplayer.device_info["identifiers"]:
                return ident
    return None


class TemperatureSensor(SensorEntity, CoordinatorEntity):
    """A temperature sensor reported by an Echo or an AIAQM endpoint."""

    _attr_has_entity_name = True
    _attr_translation_key = "temperature"

    def __init__(
        self,
        coordinator,
        entity_id,
        name,
        device_ident,
        *,
        device_serial: Optional[str] = None,
        debug: bool = False,
    ):
        """Initialize temperature sensor."""
        super().__init__(coordinator)
        self._debug = bool(debug)
        self.alexa_entity_id = entity_id
        self._device_name = name
        # Need to append "+temperature" because the Alexa entityId is for a physical device
        # and a single physical device can have multiple HA entities
        self._attr_unique_id = entity_id + "_temperature"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        value_and_scale: Optional[dict] = parse_temperature_from_coordinator(
            coordinator, entity_id, debug=self._debug
        )
        self._attr_native_value = self._get_temperature_value(value_and_scale)
        self._attr_native_unit_of_measurement = self._get_temperature_scale(
            value_and_scale
        )

        # Attach to an HA device by identifier:
        # - Echo: (DOMAIN, serial)
        # - AIAQM: (DOMAIN, <hardware serial>)
        if device_ident:
            # If we were given an AIAQM serial, expose richer device info in HA.
            if device_serial:
                self._attr_device_info = dr.DeviceInfo(
                    identifiers={device_ident},
                    serial_number=device_serial,
                    manufacturer="Amazon",
                    model="Indoor Air Quality Monitor",
                    name=name,
                )
            else:
                # Echo-attached temp: just bind to the existing HA device by identifier.
                self._attr_device_info = dr.DeviceInfo(
                    identifiers={device_ident},
                )
        else:
            self._attr_device_info = None

        _LOGGER.debug("Coordinator init: %s Temperature", self._device_name)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        value_and_scale = parse_temperature_from_coordinator(
            self.coordinator, self.alexa_entity_id, debug=self._debug
        )
        self._attr_native_value = self._get_temperature_value(value_and_scale)
        self._attr_native_unit_of_measurement = self._get_temperature_scale(
            value_and_scale
        )
        value_str = (
            self._attr_native_value if self._attr_native_value is not None else ""
        )
        unit_str = self._attr_native_unit_of_measurement or ""
        _LOGGER.debug(
            "Coordinator update: %s Temperature: %s%s",
            self._device_name,
            value_str,
            unit_str,
        )
        super()._handle_coordinator_update()

    def _get_temperature_value(self, value):
        if value and "value" in value:
            if getattr(self, "_debug", False):
                _LOGGER.debug("TemperatureSensor value: %s", value.get("value"))
            return value.get("value")
        return None

    def _get_temperature_scale(self, value):
        if value and "scale" in value:
            if getattr(self, "_debug", False):
                _LOGGER.debug("TemperatureSensor scale: %s", value.get("scale"))
            if value.get("scale") == "CELSIUS":
                return UnitOfTemperature.CELSIUS
            if value.get("scale") == "FAHRENHEIT":
                return UnitOfTemperature.FAHRENHEIT
            if value.get("scale") == "KELVIN":
                return UnitOfTemperature.KELVIN
        return None


# Mapping from Alexa AirQuality sensor types to translation keys
AIR_QUALITY_TRANSLATION_KEYS = {
    "Alexa.AirQuality.CarbonMonoxide": "air_quality_carbon_monoxide",
    "Alexa.AirQuality.Humidity": "air_quality_humidity",
    "Alexa.AirQuality.IndoorAirQuality": "air_quality_indoor_air_quality",
    "Alexa.AirQuality.ParticulateMatter": "air_quality_particulate_matter",
    "Alexa.AirQuality.VolatileOrganicCompounds": "air_quality_volatile_organic_compounds",
}


class AirQualitySensor(SensorEntity, CoordinatorEntity):
    """An air quality sensor reported by an Amazon indoor air quality monitor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        entity_id,
        name,
        device_ident,
        sensor_name,
        instance,
        unit,
        *,
        device_serial: Optional[str] = None,
        debug: bool = False,
    ):
        super().__init__(coordinator)
        self._debug = bool(debug)
        self.alexa_entity_id = entity_id
        self._device_name = name
        self._sensor_type = sensor_name
        # Set translation key based on sensor type
        self._attr_translation_key = AIR_QUALITY_TRANSLATION_KEYS.get(
            sensor_name, "air_quality"
        )
        # tidy up name for unique_id and logging
        self._sensor_name = sensor_name.replace("Alexa.AirQuality.", "")
        self._sensor_name = "".join(
            " " + char if char.isupper() else char.strip() for char in self._sensor_name
        ).strip()
        self._attr_device_class = ALEXA_AIR_QUALITY_DEVICE_CLASS.get(sensor_name)
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_value: Optional[int | float | str] = (
            parse_air_quality_from_coordinator(
                coordinator, entity_id, instance, debug=self._debug
            )
        )
        self._attr_native_unit_of_measurement: Optional[str] = (
            ALEXA_UNIT_CONVERSION.get(unit)
        )
        self._attr_unique_id = (
            entity_id + "_" + self._sensor_name.replace(" ", "_").lower()
        )
        self._attr_icon = ALEXA_ICON_CONVERSION.get(sensor_name, ALEXA_ICON_DEFAULT)

        # Attach to the synthetic AIAQM device so all AQM sensors group under one device.
        if device_ident:
            if device_serial:
                self._attr_device_info = dr.DeviceInfo(
                    identifiers={device_ident},
                    serial_number=device_serial,
                    manufacturer="Amazon",
                    model="Indoor Air Quality Monitor",
                    name=name,
                )
            else:
                self._attr_device_info = dr.DeviceInfo(
                    identifiers={device_ident},
                )
        else:
            self._attr_device_info = None

        self._instance = instance
        _LOGGER.debug("Coordinator init: %s %s", self._device_name, self._sensor_name)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = parse_air_quality_from_coordinator(
            self.coordinator, self.alexa_entity_id, self._instance, debug=self._debug
        )
        value_str = (
            self._attr_native_value if self._attr_native_value is not None else ""
        )
        unit_str = self._attr_native_unit_of_measurement or ""
        fmt = (
            "Coordinator update: %s %s: %s%s"
            if unit_str in ("", "%")
            else "Coordinator update: %s %s: %s %s"
        )
        _LOGGER.debug(
            fmt,
            self._device_name,
            self._sensor_name,
            value_str,
            unit_str,
        )
        super()._handle_coordinator_update()


class AlexaMediaNotificationSensor(SensorEntity):
    """Representation of Alexa Media sensors."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = None
    _unrecorded_attributes = frozenset({"brief", "sorted_active", "sorted_all"})

    # Guard for internal HA API - only override if base class has this property
    if hasattr(SensorEntity, "_unit_of_measurement_translation_key"):

        @property
        def _unit_of_measurement_translation_key(self) -> str | None:
            """Return None to prevent unit translation lookup before platform registration.

            This override is necessary because HA tries to resolve unit translation
            when translation_key is set, but platform_data is None before entity
            registration. Timestamp sensors have no units, so we can safely return None.
            """
            return None

    _LABEL_KEY_MAP: ClassVar[dict[str, str]] = {
        "Alarm": "alarmLabel",
        "Timer": "timerLabel",
        "Reminder": "reminderLabel",
    }

    def __init__(
        self,
        client,
        n_dict,
        sensor_property: str,
        account,
        name="Next Notification",
        icon=None,
        debug: bool = False,
    ):
        """Initialize the Alexa sensor device."""
        # Class info
        self._debug = bool(debug)
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_state_class = None
        self._attr_native_value: Optional[datetime.datetime] = None
        self._attr_unique_id = f"{client.unique_id}_{name}"
        self._attr_icon = icon
        self._attr_device_info = {
            "identifiers": {(ALEXA_DOMAIN, client.unique_id)},
        }
        self._attr_assumed_state = client.assumed_state
        self._attr_available = client.available
        self._client = client
        self._n_dict = n_dict
        self._sensor_property = sensor_property
        self._account = account
        self._type = "" if not self._type else self._type
        self._all = []
        self._active = []
        self._next: Optional[dict] = None
        self._prior_value = None
        self._timestamp: Optional[datetime.datetime] = None
        self._tracker: Optional[Callable] = None
        self._dismissed: Optional[datetime.datetime] = None
        self._status: Optional[str] = None
        self._amz_id: Optional[str] = None
        self._version: Optional[str] = None

    def _process_raw_notifications(self):
        # Build full list for this device/type
        self._all = (
            list(map(self._fix_alarm_date_time, self._n_dict.items()))
            if self._n_dict
            else []
        )
        self._all = list(map(self._update_recurring_alarm, self._all))
        self._all = sorted(self._all, key=lambda x: x[1][self._sensor_property])

        # DEBUG: log ALL notifications for this device/type
        if self._debug and self._all:
            try:
                summary_all = [
                    {
                        "id": v.get("id"),
                        "status": v.get("status"),
                        self._sensor_property: v.get(self._sensor_property),
                        "lastUpdatedDate": v.get("lastUpdatedDate"),
                        "type": v.get("type"),
                    }
                    for _, v in self._all
                ]
            except (KeyError, TypeError, AttributeError) as exc:
                summary_all = f"<error building summary_all: {exc}>"

            _LOGGER.debug(
                "%s: %s %s ALL notifications: %s",
                hide_email(self._account),
                hide_serial(self._client.device_serial_number),
                self._type,
                summary_all,
            )
        elif getattr(self, "_debug", False):
            _LOGGER.debug(
                "%s: %s %s has no notifications (_n_dict empty)",
                hide_email(self._account),
                hide_serial(self._client.device_serial_number),
                self._type,
            )

        # Previous "next" for change detection
        self._prior_value = self._next if self._active else None

        # Filter ACTIVE (ON / SNOOZED)
        self._active = (
            list(filter(lambda x: x[1]["status"] in ("ON", "SNOOZED"), self._all))
            if self._all
            else []
        )
        self._next = self._active[0][1] if self._active else None

        # DEBUG: log ACTIVE set and which one we picked as next
        if self._debug and self._active:
            try:
                summary_active = [
                    {
                        "id": v.get("id"),
                        "status": v.get("status"),
                        self._sensor_property: v.get(self._sensor_property),
                        "lastUpdatedDate": v.get("lastUpdatedDate"),
                        "type": v.get("type"),
                    }
                    for _, v in self._active
                ]
            except (KeyError, TypeError, AttributeError) as exc:
                summary_active = f"<error building summary_active: {exc}>"

            _LOGGER.debug(
                "%s: %s %s ACTIVE notifications: %s | picked next=%s",
                hide_email(self._account),
                hide_serial(self._client.device_serial_number),
                self._type,
                summary_active,
                self._next.get("id") if self._next else None,
            )
        elif getattr(self, "_debug", False):
            _LOGGER.debug(
                "%s: %s %s has no ACTIVE notifications (all=%s)",
                hide_email(self._account),
                hide_serial(self._client.device_serial_number),
                self._type,
                len(self._all),
            )

        # Track dismissal and schedule events (existing behavior)
        alarm = next(
            (alarm[1] for alarm in self._all if alarm[1].get("id") == self._amz_id),
            None,
        )
        if alarm_just_dismissed(alarm, self._status, self._version):
            self._dismissed = dt.now().isoformat()

        self._attr_native_value = self._process_state(self._next)
        self._status = self._next.get("status", "OFF") if self._next else "OFF"
        self._version = self._next.get("version", "0") if self._next else None
        self._amz_id = self._next.get("id") if self._next else None

        if self._attr_native_value is None or self._next != self._prior_value:
            # cancel any event triggers
            if self._tracker:
                _LOGGER.debug("%s: Cancelling old event", self)
                self._tracker()
            if self._attr_native_value is not None and self._status != "SNOOZED":
                _LOGGER.debug(
                    "%s: Scheduling event in %s",
                    self,
                    dt.as_utc(self._attr_native_value) - dt.utcnow(),
                )
                self._tracker = async_track_point_in_utc_time(
                    self.hass,
                    self._trigger_event,
                    dt.as_utc(self._attr_native_value),
                )

    def _trigger_event(self, time_date) -> None:
        _LOGGER.debug(
            "%s:Firing %s at %s",
            self,
            "alexa_media_notification_event",
            dt.as_local(time_date),
        )
        self.hass.bus.fire(
            "alexa_media_notification_event",
            event_data={
                "email": hide_email(self._account),
                "device": {"name": self.name, "entity_id": self.entity_id},
                "event": self._active[0],
            },
        )

    def _fix_alarm_date_time(self, value):
        if (
            self._sensor_property != "date_time"
            or not value
            or isinstance(value[1][self._sensor_property], datetime.datetime)
        ):
            return value
        naive_time = dt.parse_datetime(value[1][self._sensor_property])
        timezone = dt.get_time_zone(
            self._client._timezone  # pylint: disable=protected-access
        )
        if timezone and naive_time:
            value[1][self._sensor_property] = naive_time.replace(tzinfo=timezone)
        elif not naive_time:
            # this is typically an older alarm
            value[1][self._sensor_property] = datetime.datetime.fromtimestamp(
                value[1]["alarmTime"] / 1000, tz=LOCAL_TIMEZONE
            )
            _LOGGER.warning(
                "There is an old format alarm on %s set for %s. "
                " This alarm should be removed in the Alexa app and recreated. ",
                self._client.name,
                dt.as_local(value[1][self._sensor_property]),
            )
        else:
            _LOGGER.warning(
                "%s is returning erroneous data. "
                "Returned times may be wrong. "
                "Please confirm the timezone in the Alexa app is correct. "
                "Debugging info: \nRaw: %s \nNaive Time: %s "
                "\nTimezone: %s",
                self._client.name,
                value[1],
                naive_time,
                self._client._timezone,  # pylint: disable=protected-access
            )
        return value

    def _update_recurring_alarm(self, value):
        if getattr(self, "_debug", False):
            _LOGGER.debug("Sensor value %s", value)
        next_item = value[1]
        alarm = next_item[self._sensor_property]
        reminder = None
        recurrence = []
        if isinstance(next_item[self._sensor_property], (int, float)):
            reminder = True
            alarm = dt.as_local(
                self._round_time(
                    datetime.datetime.fromtimestamp(alarm / 1000, tz=LOCAL_TIMEZONE)
                )
            )
        alarm_on = next_item["status"] == "ON"
        r_rule_data = next_item.get("rRuleData")
        if r_rule_data:
            next_trigger_times = r_rule_data.get("nextTriggerTimes")
            weekdays = r_rule_data.get("byWeekDays")
            if next_trigger_times:
                alarm = next_trigger_times[0]
            elif weekdays:
                for day in weekdays:
                    recurrence.append(RECURRING_DAY[day])
        else:
            recurring_pattern = next_item.get("recurringPattern")
            recurrence = RECURRING_PATTERN_ISO_SET.get(recurring_pattern)
        while (
            alarm_on
            and recurrence
            and alarm.isoweekday() not in recurrence
            and alarm < dt.now()
        ):
            alarm += datetime.timedelta(days=1)
        if reminder:
            alarm = dt.as_timestamp(alarm) * 1000
        if alarm != next_item[self._sensor_property]:
            _LOGGER.debug(
                "%s with recurrence %s set to %s",
                next_item["type"],
                recurrence,
                alarm,
            )
        next_item[self._sensor_property] = alarm
        return value

    @staticmethod
    def _round_time(value: datetime.datetime) -> datetime.datetime:
        precision = datetime.timedelta(seconds=1).total_seconds()
        seconds = (value - value.min.replace(tzinfo=value.tzinfo)).seconds
        rounding = (seconds + precision / 2) // precision * precision
        return value + datetime.timedelta(0, rounding - seconds, -value.microsecond)

    async def async_added_to_hass(self):
        """Store register state change callback."""
        try:
            if not self.enabled:
                return
        except AttributeError:
            pass
        self._process_raw_notifications()
        # Register event handler on bus
        self._listener = async_dispatcher_connect(
            self.hass,
            f"{ALEXA_DOMAIN}_{hide_email(self._account)}"[0:32],
            self._handle_event,
        )
        await self.async_update()

    async def async_will_remove_from_hass(self):
        """Prepare to remove entity."""
        # Register event handler on bus
        self._listener()
        if self._tracker:
            self._tracker()

    def _handle_event(self, event):
        """Handle events.

        This will update PUSH_ACTIVITY, NOTIFICATION_UPDATE, or a global
        notifications refresh event to see if the sensor should be updated.
        """
        try:
            if not self.enabled:
                return
        except AttributeError:
            pass

        # Global refresh: any time we rebuild the notifications snapshot
        if "notifications_refreshed" in event:
            _LOGGER.debug("Force-refreshing notification sensor %s", self)
            self.schedule_update_ha_state(True)
            return

        if "notification_update" in event:
            if (
                event["notification_update"]["dopplerId"]["deviceSerialNumber"]
                == self._client.device_serial_number
            ):
                _LOGGER.debug("Updating sensor %s from notification_update", self)
                self.schedule_update_ha_state(True)

        if "push_activity" in event:
            if (
                event["push_activity"]["key"]["serialNumber"]
                == self._client.device_serial_number
            ):
                _LOGGER.debug("Updating sensor %s from push_activity", self)
                self.schedule_update_ha_state(True)

    @property
    def hidden(self):
        """Return whether the sensor should be hidden."""
        return self.state is None

    @property
    def should_poll(self):
        """Return the polling state."""
        return not is_http2_enabled(self.hass, self._account)

    def _process_state(self, value) -> Optional[datetime.datetime]:
        return dt.as_local(value[self._sensor_property]) if value else None

    async def async_update(self):
        """Update state."""
        try:
            if not self.enabled:
                return
        except AttributeError:
            pass
        account_dict = self.hass.data[DATA_ALEXAMEDIA]["accounts"][self._account]
        notifications = account_dict.get("notifications")
        if notifications is None:
            _LOGGER.debug(
                "%s: No notifications found in account_dict yet; skipping update",
                self,
            )
            self._timestamp = None
            self._n_dict = None
            self._process_raw_notifications()
            try:
                self.schedule_update_ha_state()
            except NoEntitySpecifiedError:
                pass
            return

        # Normal path: notifications dict present
        self._timestamp = notifications.get("process_timestamp")

        device_notifications = notifications.get(self._client.device_serial_number, {})
        self._n_dict = device_notifications.get(self._type, {})
        self._process_raw_notifications()
        try:
            self.schedule_update_ha_state()
        except NoEntitySpecifiedError:
            pass  # we ignore this due to a harmless startup race condition

    @property
    def recurrence(self):
        """Return the recurrence pattern of the sensor."""
        return (
            RECURRING_PATTERN.get(self._next.get("recurringPattern"))
            if self._next
            else None
        )

    @property
    def extra_state_attributes(self):
        """Return additional attributes."""
        attr = {
            "recurrence": self.recurrence,
            "process_timestamp": (
                dt.as_local(self._timestamp).isoformat() if self._timestamp else None
            ),
            "prior_value": self._process_state(self._prior_value),
            "total_active": len(self._active),
            "total_all": len(self._all),
            "status": self._status,
            "dismissed": self._dismissed,
        }

        # Optional lightweight debug/introspection view
        # Only include a small subset and rely on _unrecorded_attributes
        # so this doesn't end up in the recorder DB.
        def _serialize_entry(entry: dict) -> dict:
            """Serialize a single alarm/timer/reminder entry into a compact dict."""
            if not entry:
                return {}
            when = entry.get(self._sensor_property)
            if isinstance(when, datetime.datetime):
                when_val = dt.as_local(when).isoformat()
            else:
                when_val = when

            # Labels are type-specific in Alexa's payload; resolve to a single generic key.
            label_key = self._LABEL_KEY_MAP.get(self._type)
            label = entry.get(label_key) if label_key else None

            data = {
                "id": entry.get("id"),
                "label": label,
                "status": entry.get("status"),
                "type": entry.get("type"),
                "version": entry.get("version"),
                self._sensor_property: when_val,
                "lastUpdatedDate": entry.get("lastUpdatedDate"),
            }
            return data

        if self._all:
            # Limit to a few entries so attributes stay small
            attr["brief"] = {
                "active": [_serialize_entry(v) for _, v in self._active[:12]],
                "all": [_serialize_entry(v) for _, v in self._all[:12]],
            }
            # Legacy alias attributes (for backwards compatibility with
            # cards/automations that relied on the previous sorted_* attributes).
            #
            # Historical behavior exposed the full notification dicts
            legacy_all = [v for _, v in self._all]
            legacy_active = [v for _, v in self._active]

            # Generic legacy names
            attr["sorted_all"] = legacy_all
            attr["sorted_active"] = legacy_active

            # Some consumers expect a single string label for the "next" item.
            # These keys are used by card-alexa-alarms-timers.
            if legacy_active:
                first = legacy_active[0]
                label_key = self._LABEL_KEY_MAP.get(self._type)
                if label_key:
                    attr[self._type.lower()] = first.get(label_key)

                    if self._type == "Reminder":
                        # Secondary reminder label (when present)
                        attr["reminder_sub_label"] = first.get("reminderSubLabel")
        return attr


class AlarmSensor(AlexaMediaNotificationSensor):
    """Representation of a Alexa Alarm sensor."""

    _attr_translation_key = "next_alarm"

    def __init__(self, client, n_json, account, debug: bool = False):
        """Initialize the Alexa sensor."""
        # Class info
        self._type = "Alarm"
        super().__init__(
            client,
            n_json,
            "date_time",
            account,
            "Next alarm",
            "mdi:alarm",
            debug=debug,
        )


class TimerSensor(AlexaMediaNotificationSensor):
    """Representation of a Alexa Timer sensor."""

    _attr_translation_key = "next_timer"

    def __init__(self, client, n_json, account, debug: bool = False):
        """Initialize the Alexa sensor."""
        # Class info
        self._type = "Timer"
        super().__init__(
            client,
            n_json,
            "remainingTime",
            account,
            "Next timer",
            (
                "mdi:timer-outline"
                if (version.parse(HA_VERSION) >= version.parse("0.113.0"))
                else "mdi:timer"
            ),
            debug=debug,
        )

    def _process_state(self, value) -> Optional[datetime.datetime]:
        return (
            dt.as_local(
                super()._round_time(
                    self._timestamp
                    + datetime.timedelta(milliseconds=value[self._sensor_property])
                )
            )
            if value and self._timestamp
            else None
        )

    @property
    def paused(self) -> Optional[bool]:
        """Return the paused state of the sensor."""
        return self._next.get("status") == "PAUSED" if self._next else None

    @property
    def icon(self):
        """Return the icon of the sensor."""
        off_icon = (
            "mdi:timer-off-outline"
            if (version.parse(HA_VERSION) >= version.parse("0.113.0"))
            else "mdi:timer-off"
        )
        return self._attr_icon if not self.paused else off_icon

    @property
    def timer(self):
        """Return the timer of the sensor."""
        return self._next.get("timerLabel") if self._next else None

    @property
    def extra_state_attributes(self):
        """Return the scene state attributes."""
        attr = super().extra_state_attributes
        attr.update({"timer": self.timer})
        return attr


class ReminderSensor(AlexaMediaNotificationSensor):
    """Representation of a Alexa Reminder sensor."""

    _attr_translation_key = "next_reminder"

    def __init__(self, client, n_json, account, debug: bool = False):
        """Initialize the Alexa sensor."""
        self._type = "Reminder"
        super().__init__(
            client,
            n_json,
            "alarmTime",
            account,
            "Next reminder",
            "mdi:reminder",
            debug=debug,
        )

    def _process_state(self, value) -> Optional[datetime.datetime]:
        return (
            dt.as_local(
                super()._round_time(
                    datetime.datetime.fromtimestamp(
                        value[self._sensor_property] / 1000, tz=LOCAL_TIMEZONE
                    )
                )
            )
            if value
            else None
        )

    @property
    def reminder(self):
        """Return the reminder of the sensor."""
        return self._next.get("reminderLabel") if self._next else None

    @property
    def extra_state_attributes(self):
        """Return the scene state attributes."""
        attr = super().extra_state_attributes
        attr.update({"reminder": self.reminder})
        return attr
