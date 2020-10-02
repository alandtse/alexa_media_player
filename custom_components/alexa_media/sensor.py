#!/usr/bin/env python
# -*- coding: utf-8 -*-
#  SPDX-License-Identifier: Apache-2.0
"""
Alexa Devices Sensors.

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""
import datetime
import logging
from typing import List, Text  # noqa pylint: disable=unused-import

from homeassistant.const import (
    DEVICE_CLASS_TIMESTAMP,
    STATE_UNAVAILABLE,
    __version__ as HA_VERSION,
)
from homeassistant.exceptions import ConfigEntryNotReady, NoEntitySpecifiedError
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity
from homeassistant.util import dt
from packaging import version
import pytz

from . import (
    CONF_EMAIL,
    CONF_EXCLUDE_DEVICES,
    CONF_INCLUDE_DEVICES,
    DATA_ALEXAMEDIA,
    DOMAIN as ALEXA_DOMAIN,
    hide_email,
    hide_serial,
)
from .const import RECURRING_PATTERN, RECURRING_PATTERN_ISO_SET
from .helpers import add_devices, retry_async

_LOGGER = logging.getLogger(__name__)

LOCAL_TIMEZONE = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo


async def async_setup_platform(hass, config, add_devices_callback, discovery_info=None):
    """Set up the Alexa sensor platform."""
    devices: List[AlexaMediaNotificationSensor] = []
    SENSOR_TYPES = {
        "Alarm": AlarmSensor,
        "Timer": TimerSensor,
        "Reminder": ReminderSensor,
    }
    account = config[CONF_EMAIL]
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
            for (n_type, class_) in SENSOR_TYPES.items():
                n_type_dict = (
                    account_dict["notifications"][key][n_type]
                    if key in account_dict["notifications"]
                    and n_type in account_dict["notifications"][key]
                    else {}
                )
                if (
                    n_type in ("Alarm, Timer")
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
    return await add_devices(
        hide_email(account),
        devices,
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
    for key, sensors in account_dict["entities"]["sensor"].items():
        for device in sensors[key].values():
            await device.async_remove()
    return True


class AlexaMediaNotificationSensor(Entity):
    """Representation of Alexa Media sensors."""

    def __init__(
        self,
        client,
        n_dict,
        sensor_property: Text,
        account,
        name="Next Notification",
        icon=None,
    ):
        """Initialize the Alexa sensor device."""
        # Class info
        self._client = client
        self._n_dict = n_dict
        self._sensor_property = sensor_property
        self._account = account
        self._dev_id = client.unique_id
        self._name = name
        self._unit = None
        self._device_class = DEVICE_CLASS_TIMESTAMP
        self._icon = icon
        self._all = []
        self._active = []
        self._next = None
        self._prior_value = None
        self._timestamp: datetime.datetime = None
        self._process_raw_notifications()

    def _process_raw_notifications(self):
        self._all = (
            list(map(self._fix_alarm_date_time, self._n_dict.items()))
            if self._n_dict
            else []
        )
        self._all = list(map(self._update_recurring_alarm, self._all))
        self._all = sorted(self._all, key=lambda x: x[1][self._sensor_property])
        self._prior_value = self._next if self._active else None
        self._active = (
            list(filter(lambda x: x[1]["status"] == "ON", self._all))
            if self._all
            else []
        )
        self._next = self._active[0][1] if self._active else None

    def _fix_alarm_date_time(self, value):
        if (
            self._sensor_property != "date_time"
            or not value
            or isinstance(value[1][self._sensor_property], datetime.datetime)
        ):
            return value
        naive_time = dt.parse_datetime(value[1][self._sensor_property])
        timezone = pytz.timezone(self._client._timezone)
        if timezone and naive_time:
            value[1][self._sensor_property] = timezone.localize(naive_time)
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
                self._client._timezone,
            )
        return value

    def _update_recurring_alarm(self, value):
        _LOGGER.debug("Sensor value %s", value)
        alarm = value[1][self._sensor_property]
        reminder = None
        if isinstance(value[1][self._sensor_property], int):
            reminder = True
            alarm = dt.as_local(
                self._round_time(
                    datetime.datetime.fromtimestamp(alarm / 1000, tz=LOCAL_TIMEZONE)
                )
            )
        alarm_on = value[1]["status"] == "ON"
        recurring_pattern = value[1].get("recurringPattern")
        while (
            alarm_on
            and recurring_pattern
            and RECURRING_PATTERN_ISO_SET[recurring_pattern]
            and alarm.isoweekday not in RECURRING_PATTERN_ISO_SET[recurring_pattern]
            and alarm < dt.now()
        ):
            alarm += datetime.timedelta(days=1)
        if reminder:
            alarm = dt.as_timestamp(alarm) * 1000
        if alarm != value[1][self._sensor_property]:
            _LOGGER.debug(
                "%s with recurrence %s set to %s",
                value[1]["type"],
                RECURRING_PATTERN[recurring_pattern],
                alarm,
            )
            value[1][self._sensor_property] = alarm
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

    def _handle_event(self, event):
        """Handle events.

        This will update PUSH_NOTIFICATION_CHANGE events to see if the sensor
        should be updated.
        """
        try:
            if not self.enabled:
                return
        except AttributeError:
            pass
        if "notification_update" in event:
            if (
                event["notification_update"]["dopplerId"]["deviceSerialNumber"]
                == self._client.unique_id
            ):
                _LOGGER.debug("Updating sensor %s", self.name)
                self.async_schedule_update_ha_state(True)

    @property
    def available(self):
        """Return the availabilty of the sensor."""
        return self._client.available

    @property
    def assumed_state(self):
        """Return whether the state is an assumed_state."""
        return self._client.assumed_state

    @property
    def hidden(self):
        """Return whether the sensor should be hidden."""
        return self.state == STATE_UNAVAILABLE

    @property
    def unique_id(self):
        """Return the unique ID."""
        return f"{self._client.unique_id}_{self._name}"

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._client.name} {self._name}"

    @property
    def should_poll(self):
        """Return the polling state."""
        return not (
            self.hass.data[DATA_ALEXAMEDIA]["accounts"][self._account]["websocket"]
        )

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._process_state(self._next)

    def _process_state(self, value):
        return (
            value[self._sensor_property].replace(tzinfo=LOCAL_TIMEZONE).isoformat()
            if value
            else STATE_UNAVAILABLE
        )

    @property
    def unit_of_measurement(self):
        """Return the unit_of_measurement of the device."""
        return self._unit

    @property
    def device_class(self):
        """Return the device_class of the device."""
        return self._device_class

    async def async_update(self):
        """Update state."""
        try:
            if not self.enabled:
                return
        except AttributeError:
            pass
        account_dict = self.hass.data[DATA_ALEXAMEDIA]["accounts"][self._account]
        self._timestamp = account_dict["notifications"]["process_timestamp"]
        try:
            self._n_dict = account_dict["notifications"][self._dev_id][self._type]
        except KeyError:
            self._n_dict = None
        self._process_raw_notifications()
        try:
            self.async_schedule_update_ha_state()
        except NoEntitySpecifiedError:
            pass  # we ignore this due to a harmless startup race condition

    @property
    def device_info(self):
        """Return the device_info of the device."""
        return {
            "identifiers": {(ALEXA_DOMAIN, self._dev_id)},
            "via_device": (ALEXA_DOMAIN, self._dev_id),
        }

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return self._icon

    @property
    def recurrence(self):
        """Return the recurrence pattern of the sensor."""
        return (
            RECURRING_PATTERN[self._next.get("recurringPattern")]
            if self._next
            else None
        )

    @property
    def device_state_attributes(self):
        """Return additional attributes."""
        import json

        attr = {
            "recurrence": self.recurrence,
            "process_timestamp": 

                dt.as_local(
                        datetime.datetime.fromtimestamp(
                            self._timestamp.timestamp()
                        )
                ).isoformat(),            
            "prior_value": self._process_state(self._prior_value),
            "total_active": len(self._active),
            "total_all": len(self._all),
            "sorted_active": json.dumps(self._active, default=str),
            "sorted_all": json.dumps(self._all, default=str),
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
            "mdi:timer-outline"
            if (version.parse(HA_VERSION) >= version.parse("0.113.0"))
            else "mdi:timer",
        )

    @property
    def state(self) -> datetime.datetime:
        """Return the state of the sensor."""
        return self._process_state(self._next)

    def _process_state(self, value):
        return (
            dt.as_local(
                super()._round_time(
                    datetime.datetime.fromtimestamp(
                        self._timestamp.timestamp()
                        + value[self._sensor_property] / 1000
                    )
                )
            ).isoformat()
            if value and self._timestamp
            else STATE_UNAVAILABLE
        )

    @property
    def paused(self) -> bool:
        """Return the paused state of the sensor."""
        return self._next["status"] == "PAUSED" if self._next else None

    @property
    def icon(self):
        """Return the icon of the sensor."""
        off_icon = (
            "mdi:timer-off-outline"
            if (version.parse(HA_VERSION) >= version.parse("0.113.0"))
            else "mdi:timer-off"
        )
        return self._icon if not self.paused else off_icon


class ReminderSensor(AlexaMediaNotificationSensor):
    """Representation of a Alexa Reminder sensor."""

    def __init__(self, client, n_json, account):
        """Initialize the Alexa sensor."""
        # Class info
        self._type = "Reminder"
        super().__init__(
            client, n_json, "alarmTime", account, f"next {self._type}", "mdi:reminder"
        )

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._process_state(self._next)

    def _process_state(self, value):
        return (
            dt.as_local(
                super()._round_time(
                    datetime.datetime.fromtimestamp(
                        value[self._sensor_property] / 1000, tz=LOCAL_TIMEZONE
                    )
                )
            ).isoformat()
            if value
            else STATE_UNAVAILABLE
        )

    @property
    def reminder(self):
        """Return the reminder of the sensor."""
        return self._next["reminderLabel"] if self._next else None

    @property
    def device_state_attributes(self):
        """Return the scene state attributes."""
        attr = super().device_state_attributes
        attr.update({"reminder": self.reminder})
        return attr
