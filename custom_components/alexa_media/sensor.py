"""
Alexa Devices Sensors.

SPDX-License-Identifier: Apache-2.0

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""

import datetime
import logging
from typing import Callable, Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature, __version__ as HA_VERSION
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady, NoEntitySpecifiedError
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
    CONF_EXTENDED_ENTITY_DISCOVERY,
    RECURRING_DAY,
    RECURRING_PATTERN,
    RECURRING_PATTERN_ISO_SET,
)
from .helpers import add_devices, alarm_just_dismissed

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
        account = discovery_info.get("config", {}).get(CONF_EMAIL)
    if account is None:
        raise ConfigEntryNotReady
    include_filter = config.get(CONF_INCLUDE_DEVICES, [])
    exclude_filter = config.get(CONF_EXCLUDE_DEVICES, [])
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
                    )
                elif n_type in ("Reminder") and "REMINDERS" in device["capabilities"]:
                    alexa_client = class_(
                        account_dict["entities"]["media_player"][key],
                        n_type_dict,
                        account,
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
    temperature_entities = account_dict.get("devices", {}).get("temperature", [])
    if temperature_entities and account_dict["options"].get(
        CONF_EXTENDED_ENTITY_DISCOVERY
    ):
        temperature_sensors = await create_temperature_sensors(
            account_dict, temperature_entities
        )

    # AIAQM Sensors
    air_quality_sensors = []
    air_quality_entities = account_dict.get("devices", {}).get("air_quality", [])
    if air_quality_entities and account_dict["options"].get(
        CONF_EXTENDED_ENTITY_DISCOVERY
    ):
        air_quality_sensors = await create_air_quality_sensors(
            account_dict, air_quality_entities
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
    for key, sensors in account_dict["entities"]["sensor"].items():
        for device in sensors[key].values():
            _LOGGER.debug("Removing %s", device)
            await device.async_remove()
    return True


async def create_temperature_sensors(account_dict, temperature_entities):
    """Create temperature sensors."""
    devices = []
    coordinator = account_dict["coordinator"]
    for temp in temperature_entities:
        _LOGGER.debug(
            "Creating entity %s for a temperature sensor with name %s (%s)",
            temp["id"],
            temp["name"],
            temp,
        )
        serial = temp["device_serial"]
        device_info = lookup_device_info(account_dict, serial)
        sensor = TemperatureSensor(coordinator, temp["id"], temp["name"], device_info)
        account_dict["entities"]["sensor"].setdefault(serial, {})
        account_dict["entities"]["sensor"][serial]["Temperature"] = sensor
        devices.append(sensor)
    return devices


async def create_air_quality_sensors(account_dict, air_quality_entities):
    devices = []
    coordinator = account_dict["coordinator"]

    for temp in air_quality_entities:
        _LOGGER.debug(
            "Creating entity %s for a air quality sensor with name %s",
            temp["id"],
            temp["name"],
        )
        # Each AIAQM has 5 different sensors.
        for subsensor in temp["sensors"]:
            sensor_type = subsensor["sensorType"]
            instance = subsensor["instance"]
            unit = subsensor["unit"]
            serial = temp["device_serial"]
            device_info = lookup_device_info(account_dict, serial)
            sensor = AirQualitySensor(
                coordinator,
                temp["id"],
                temp["name"],
                device_info,
                sensor_type,
                instance,
                unit,
            )
            _LOGGER.debug("Create air quality sensors %s", sensor)
            account_dict["entities"]["sensor"].setdefault(serial, {})
            account_dict["entities"]["sensor"][serial].setdefault(sensor_type, {})
            account_dict["entities"]["sensor"][serial][sensor_type][
                "Air_Quality"
            ] = sensor
            devices.append(sensor)
    return devices


def lookup_device_info(account_dict, device_serial):
    """Get the device to use for a given Echo based on a given device serial id.

    This may return nothing as there is no guarantee that a given temperature sensor is actually attached to an Echo.
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
    """A temperature sensor reported by an Echo."""

    def __init__(self, coordinator, entity_id, name, media_player_device_id):
        """Initialize temperature sensor."""
        super().__init__(coordinator)
        self.alexa_entity_id = entity_id
        # Need to append "+temperature" because the Alexa entityId is for a physical device
        # and a single physical device can have multiple HA entities
        self._attr_unique_id = entity_id + "_temperature"
        self._attr_name = name + " Temperature"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        value_and_scale: Optional[datetime.datetime] = (
            parse_temperature_from_coordinator(coordinator, entity_id)
        )
        self._attr_native_value = self._get_temperature_value(value_and_scale)
        self._attr_native_unit_of_measurement = self._get_temperature_scale(
            value_and_scale
        )
        _LOGGER.debug(
            "Coordinator init: %s: %s %s",
            self._attr_name,
            self._attr_native_value,
            self._attr_native_unit_of_measurement,
        )
        self._attr_device_info = (
            {
                "identifiers": {media_player_device_id},
                "via_device": media_player_device_id,
            }
            if media_player_device_id
            else None
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        value_and_scale = parse_temperature_from_coordinator(
            self.coordinator, self.alexa_entity_id
        )
        self._attr_native_value = self._get_temperature_value(value_and_scale)
        self._attr_native_unit_of_measurement = self._get_temperature_scale(
            value_and_scale
        )
        _LOGGER.debug(
            "Coordinator update: %s: %s %s",
            self._attr_name,
            self._attr_native_value,
            self._attr_native_unit_of_measurement,
        )
        super()._handle_coordinator_update()

    def _get_temperature_value(self, value):
        if value and "value" in value:
            _LOGGER.debug("TemperatureSensor value: %s", value.get("value"))
            return value.get("value")
        return None

    def _get_temperature_scale(self, value):
        if value and "scale" in value:
            _LOGGER.debug("TemperatureSensor scale: %s", value.get("scale"))
            if value.get("scale") == "CELSIUS":
                return UnitOfTemperature.CELSIUS
            if value.get("scale") == "FAHRENHEIT":
                return UnitOfTemperature.FAHRENHEIT
            if value.get("scale") == "KELVIN":
                return UnitOfTemperature.KELVIN
        return None


class AirQualitySensor(SensorEntity, CoordinatorEntity):
    """A air quality sensor reported by an Amazon indoor air quality monitor."""

    def __init__(
        self,
        coordinator,
        entity_id,
        name,
        media_player_device_id,
        sensor_name,
        instance,
        unit,
    ):
        super().__init__(coordinator)
        self.alexa_entity_id = entity_id
        self._sensor_name = sensor_name
        # tidy up name
        self._sensor_name = self._sensor_name.replace("Alexa.AirQuality.", "")
        self._sensor_name = "".join(
            " " + char if char.isupper() else char.strip() for char in self._sensor_name
        ).strip()
        self._attr_name = name + " " + self._sensor_name
        self._attr_device_class = ALEXA_AIR_QUALITY_DEVICE_CLASS.get(sensor_name)
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_value: Optional[datetime.datetime] = (
            parse_air_quality_from_coordinator(coordinator, entity_id, instance)
        )
        self._attr_native_unit_of_measurement: Optional[str] = (
            ALEXA_UNIT_CONVERSION.get(unit)
        )
        self._attr_unique_id = entity_id + " " + self._sensor_name
        self._attr_icon = ALEXA_ICON_CONVERSION.get(sensor_name, ALEXA_ICON_DEFAULT)
        self._attr_device_info = (
            {
                "identifiers": {media_player_device_id},
                "via_device": media_player_device_id,
            }
            if media_player_device_id
            else None
        )
        self._instance = instance

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = parse_air_quality_from_coordinator(
            self.coordinator, self.alexa_entity_id, self._instance
        )
        super()._handle_coordinator_update()


class AlexaMediaNotificationSensor(SensorEntity):
    """Representation of Alexa Media sensors."""

    _unrecorded_attributes = frozenset({"alarms_brief"})

    def __init__(
        self,
        client,
        n_dict,
        sensor_property: str,
        account,
        name="Next Notification",
        icon=None,
    ):
        """Initialize the Alexa sensor device."""
        # Class info
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_state_class = None
        self._attr_native_value: Optional[datetime.datetime] = None
        self._attr_name = f"{client.name} {name}"
        self._attr_unique_id = f"{client.unique_id}_{name}"
        self._attr_icon = icon
        self._attr_device_info = {
            "identifiers": {(ALEXA_DOMAIN, client.unique_id)},
            "via_device": (ALEXA_DOMAIN, client.unique_id),
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
        if self._all:
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
        else:
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
        if self._active:
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
        else:
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
        if (
            r_rule_data
        ):  # the new recurrence pattern; https://github.com/alandtse/alexa_media_player/issues/1608
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
            and alarm.isoweekday not in recurrence
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
        return not (self.hass.data[DATA_ALEXAMEDIA]["accounts"][self._account]["http2"])

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
            return {
                "id": entry.get("id"),
                "status": entry.get("status"),
                "type": entry.get("type"),
                self._sensor_property: when_val,
                "lastUpdatedDate": entry.get("lastUpdatedDate"),
            }

        if self._all:
            # Limit to a few entries so attributes stay small
            attr["alarms_brief"] = {
                "active": [_serialize_entry(v) for _, v in self._active[:12]],
                "all": [_serialize_entry(v) for _, v in self._all[:12]],
            }
        return attr


class AlarmSensor(AlexaMediaNotificationSensor):
    """Representation of a Alexa Alarm sensor."""

    def __init__(self, client, n_json, account):
        """Initialize the Alexa sensor."""
        # Class info
        self._type = "Alarm"
        super().__init__(
            client, n_json, "date_time", account, f"next {self._type}", "mdi:alarm"
        )


class TimerSensor(AlexaMediaNotificationSensor):
    """Representation of a Alexa Timer sensor."""

    def __init__(self, client, n_json, account):
        """Initialize the Alexa sensor."""
        # Class info
        self._type = "Timer"
        super().__init__(
            client,
            n_json,
            "remainingTime",
            account,
            f"next {self._type}",
            (
                "mdi:timer-outline"
                if (version.parse(HA_VERSION) >= version.parse("0.113.0"))
                else "mdi:timer"
            ),
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

    def __init__(self, client, n_json, account):
        """Initialize the Alexa sensor."""
        # Class info
        self._type = "Reminder"
        super().__init__(
            client, n_json, "alarmTime", account, f"next {self._type}", "mdi:reminder"
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
