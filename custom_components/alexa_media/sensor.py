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

from homeassistant.const import DEVICE_CLASS_TIMESTAMP
from homeassistant.exceptions import NoEntitySpecifiedError
from homeassistant.helpers.entity import Entity
from homeassistant.util import dt

from . import (CONF_EMAIL, CONF_EXCLUDE_DEVICES, CONF_INCLUDE_DEVICES,
               DATA_ALEXAMEDIA)
from . import DOMAIN as ALEXA_DOMAIN
from . import (hide_email, hide_serial)
from .helpers import add_devices, retry_async

_LOGGER = logging.getLogger(__name__)

LOCAL_TIMEZONE = datetime.datetime.now(
    datetime.timezone.utc).astimezone().tzinfo

RECURRING_PATTERN = {
    None: "Never Repeat",
    "P1D": "Every day",
    "XXXX-WE": "Weekends",
    "XXXX-WD": "Weekdays",
    "XXXX-WXX-1": "Every Monday",
    "XXXX-WXX-2": "Every Tuesday",
    "XXXX-WXX-3": "Every Wednesday",
    "XXXX-WXX-4": "Every Thursday",
    "XXXX-WXX-5": "Every Friday",
    "XXXX-WXX-6": "Every Saturday",
    "XXXX-WXX-7": "Every Sunday"
}


@retry_async(limit=5, delay=5, catch_exceptions=False)
async def async_setup_platform(hass, config, add_devices_callback,
                               discovery_info=None):
    """Set up the Alexa sensor platform."""
    devices: List[AlexaMediaSensor] = []
    SENSOR_TYPES = {
        'Alarm': AlarmSensor,
        'Timer': TimerSensor,
        'Reminder': ReminderSensor
    }
    account = config[CONF_EMAIL]
    include_filter = config.get(CONF_INCLUDE_DEVICES, [])
    exclude_filter = config.get(CONF_EXCLUDE_DEVICES, [])
    account_dict = hass.data[DATA_ALEXAMEDIA]['accounts'][account]
    _LOGGER.debug("%s: Loading sensors",
                  hide_email(account))
    if 'sensor' not in account_dict['entities']:
        (hass.data[DATA_ALEXAMEDIA]
         ['accounts']
         [account]
         ['entities']
         ['sensor']) = {}
    for key, device in account_dict['devices']['media_player'].items():
        if key not in account_dict['entities']['media_player']:
            _LOGGER.debug("%s: Media player %s not loaded yet; delaying load",
                          hide_email(account),
                          hide_serial(key))
            return False
        if key not in (account_dict
                       ['entities']
                       ['sensor']):
            (account_dict
             ['entities']
             ['sensor'][key]) = {}
            for (n_type, class_) in SENSOR_TYPES.items():
                n_type_dict = (
                    account_dict['notifications'][key][n_type]
                    if key in account_dict['notifications'] and
                    n_type in account_dict['notifications'][key] else {})
                if (n_type in ('Alarm, Timer') and
                        'TIMERS_AND_ALARMS' in device['capabilities']):
                    alexa_client = class_(
                        account_dict['entities']['media_player'][key],
                        n_type_dict,
                        account)
                elif (n_type in ('Reminder') and
                        'REMINDERS' in device['capabilities']):
                    alexa_client = class_(
                        account_dict['entities']['media_player'][key],
                        n_type_dict,
                        account)
                else:
                    continue
                _LOGGER.debug("%s: Found %s %s sensor (%s) with next: %s",
                              hide_email(account),
                              hide_serial(key),
                              n_type,
                              len(n_type_dict.keys()),
                              alexa_client.state)
                devices.append(alexa_client)
                (account_dict
                    ['entities']
                    ['sensor']
                    [key]
                    [n_type]) = alexa_client
        else:
            for alexa_client in (account_dict['entities']
                                             ['sensor']
                                             [key].values()):
                _LOGGER.debug("%s: Skipping already added device: %s",
                              hide_email(account),
                              alexa_client)
    return await add_devices(hide_email(account),
                             devices, add_devices_callback,
                             include_filter, exclude_filter)


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Set up the Alexa sensor platform by config_entry."""
    return await async_setup_platform(
        hass,
        config_entry.data,
        async_add_devices,
        discovery_info=None)


async def async_unload_entry(hass, entry) -> bool:
    """Unload a config entry."""
    account = entry.data[CONF_EMAIL]
    account_dict = hass.data[DATA_ALEXAMEDIA]['accounts'][account]
    for key, sensors in (account_dict['entities']['sensor'].items()):
        for device in sensors[key].values():
            await device.async_remove()
    return True


class AlexaMediaSensor(Entity):
    """Representation of Alexa Media sensors."""

    def __init__(self,
                 client,
                 n_dict,
                 sensor_property: Text,
                 account,
                 name="Next Notification",
                 icon=None):
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
        self._all = (sorted(self._n_dict.items(),
                            key=lambda x: x[1][self._sensor_property])
                     if self._n_dict else [])
        self._sorted = list(filter(lambda x: x[1]['status'] == 'ON',
                            self._all)) if self._all else []
        self._next = self._sorted[0][1] if self._sorted else None

    async def async_added_to_hass(self):
        """Store register state change callback."""
        try:
            if not self.enabled:
                return
        except AttributeError:
            pass
        # Register event handler on bus
        self._listener = self.hass.bus.async_listen(
            f'{ALEXA_DOMAIN}_{hide_email(self._account)}'[0:32],
            self._handle_event)

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
        if 'notification_update' in event.data:
            if (event.data['notification_update']['dopplerId']
                    ['deviceSerialNumber'] == self._client.unique_id):
                _LOGGER.debug("Updating sensor %s", self.name)
                self.async_schedule_update_ha_state(True)

    @property
    def available(self):
        """Return the availabilty of the sensor."""
        return True

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
        return not (self.hass.data[DATA_ALEXAMEDIA]
                    ['accounts'][self._account]['websocket'])

    @property
    def state(self):
        """Return the state of the sensor."""
        return dt.parse_datetime(self._next[self._sensor_property]).replace(
            tzinfo=LOCAL_TIMEZONE) if self._next else 'None'

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
        account_dict = (self.hass.data[DATA_ALEXAMEDIA]['accounts']
                        [self._account])
        try:
            self._n_dict = (account_dict['notifications'][self._dev_id]
                            [self._type])
        except KeyError:
            self._n_dict = None
        self._all = (sorted(self._n_dict.items(),
                            key=lambda x: x[1][self._sensor_property])
                     if self._n_dict else [])
        self._sorted = list(filter(lambda x: x[1]['status'] == 'ON',
                            self._all)) if self._all else []
        self._next = self._sorted[0][1] if self._sorted else None
        try:
            self.async_schedule_update_ha_state()
        except NoEntitySpecifiedError:
            pass  # we ignore this due to a harmless startup race condition

    @property
    def device_info(self):
        """Return the device_info of the device."""
        return {
            'identifiers': {
                (ALEXA_DOMAIN, self._dev_id)
            },
            'via_device': (ALEXA_DOMAIN, self._dev_id),
        }

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return self._icon

    @property
    def recurrence(self):
        """Return the icon of the sensor."""
        return (RECURRING_PATTERN[self._next['recurringPattern']]
                if self._next else None)

    @property
    def device_state_attributes(self):
        """Return additional attributes."""
        import json
        attr = {
            'recurrence': self.recurrence,
            'total_active': len(self._sorted),
            'total_all': len(self._all),
            'sorted_active': json.dumps(self._sorted),
            'sorted_all': json.dumps(self._all),
        }
        return attr


class AlarmSensor(AlexaMediaSensor):
    """Representation of a Alexa Alarm sensor."""

    def __init__(self, client, n_json, account):
        """Initialize the Alexa sensor."""
        # Class info
        self._type = 'Alarm'
        super().__init__(
            client,
            n_json,
            'date_time',
            account,
            f"next {self._type}",
            'mdi:alarm')


class TimerSensor(AlexaMediaSensor):
    """Representation of a Alexa Timer sensor."""

    def __init__(self, client, n_json, account):
        """Initialize the Alexa sensor."""
        # Class info
        self._type = 'Timer'
        super().__init__(
            client,
            n_json,
            'remainingTime',
            account,
            f"next {self._type}",
            "mdi:timer")

    @property
    def state(self) -> datetime.datetime:
        """Return the state of the sensor."""
        return dt.as_local(dt.utc_from_timestamp(
            dt.utcnow().timestamp() +
            self._next[self._sensor_property]/1000)) if self._next else 'None'

    @property
    def paused(self) -> bool:
        """Return the paused state of the sensor."""
        return self._next['status'] == 'PAUSED' if self._next else None

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return self._icon if not self.paused else "mdi:timer-off"


class ReminderSensor(AlexaMediaSensor):
    """Representation of a Alexa Reminder sensor."""

    def __init__(self, client, n_json, account):
        """Initialize the Alexa sensor."""
        # Class info
        self._type = 'Reminder'
        super().__init__(
            client,
            n_json,
            'alarmTime',
            account,
            f"next {self._type}",
            'mdi:reminder')

    @property
    def state(self):
        """Return the state of the sensor."""
        return dt.as_local(datetime.datetime.fromtimestamp(
            self._next[self._sensor_property]/1000,
            tz=LOCAL_TIMEZONE)) if self._next else 'None'

    @property
    def reminder(self):
        """Return the reminder of the sensor."""
        return self._next['reminderLabel'] if self._next else None

    @property
    def device_state_attributes(self):
        """Return the scene state attributes."""
        attr = super().device_state_attributes
        attr.update(
            {
             'reminder': self.reminder
            }
        )
        return attr
