#!/usr/bin/env python
# -*- coding: utf-8 -*-
#  SPDX-License-Identifier: Apache-2.0
"""
Alexa Devices Switches.

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""
import logging
from typing import List  # noqa pylint: disable=unused-import

from homeassistant import util
from homeassistant.components.switch import SwitchDevice
from homeassistant.exceptions import NoEntitySpecifiedError
from homeassistant.helpers.event import async_call_later

from . import (CONF_EMAIL, CONF_EXCLUDE_DEVICES, CONF_INCLUDE_DEVICES,
               DATA_ALEXAMEDIA)
from . import DOMAIN as ALEXA_DOMAIN
from . import (MIN_TIME_BETWEEN_FORCED_SCANS, MIN_TIME_BETWEEN_SCANS,
               hide_email, hide_serial)
from .helpers import add_devices, retry_async

_LOGGER = logging.getLogger(__name__)


@retry_async(limit=5, delay=2, catch_exceptions=True)
async def async_setup_platform(hass, config, add_devices_callback,
                               discovery_info=None):
    """Set up the Alexa switch platform."""
    devices = []  # type: List[DNDSwitch]
    SWITCH_TYPES = [
        ('dnd', DNDSwitch),
        ('shuffle', ShuffleSwitch),
        ('repeat', RepeatSwitch)
    ]
    config = discovery_info['config']
    account = config[CONF_EMAIL]
    include_filter = config.get(CONF_INCLUDE_DEVICES, [])
    exclude_filter = config.get(CONF_EXCLUDE_DEVICES, [])
    account_dict = hass.data[DATA_ALEXAMEDIA]['accounts'][account]
    _LOGGER.debug("%s: Loading switches",
                  hide_email(account))
    if 'switch' not in account_dict['entities']:
        (hass.data[DATA_ALEXAMEDIA]
         ['accounts']
         [account]
         ['entities']
         ['switch']) = {}
    for key, device in account_dict['devices']['media_player'].items():
        if key not in account_dict['entities']['media_player']:
            _LOGGER.debug("%s: Media player %s not loaded yet; delaying load",
                          hide_email(account),
                          hide_serial(key))
            return False
        if key not in (hass.data[DATA_ALEXAMEDIA]
                       ['accounts']
                       [account]
                       ['entities']
                       ['switch']):
            (hass.data[DATA_ALEXAMEDIA]
             ['accounts']
             [account]
             ['entities']
             ['switch'][key]) = {}
            for (switch_key, class_) in SWITCH_TYPES:
                alexa_client = class_(account_dict['entities']
                                      ['media_player']
                                      [key],
                                      account)  # type: AlexaMediaSwitch
                _LOGGER.debug("%s: Found %s %s switch with status: %s",
                              hide_email(account),
                              hide_serial(key),
                              switch_key,
                              alexa_client.is_on)
                devices.append(alexa_client)
                (hass.data[DATA_ALEXAMEDIA]
                 ['accounts']
                 [account]
                 ['entities']
                 ['switch']
                 [key]
                 [switch_key]) = alexa_client
        else:
            for alexa_client in (hass.data[DATA_ALEXAMEDIA]
                                             ['accounts']
                                             [account]
                                             ['entities']
                                             ['switch']
                                             [key].values()):
                _LOGGER.debug("%s: Skipping already added device: %s",
                              hide_email(account),
                              alexa_client)
    return await add_devices(hide_email(account),
                             devices, add_devices_callback,
                             include_filter, exclude_filter)


class AlexaMediaSwitch(SwitchDevice):
    """Representation of a Alexa Media switch."""

    def __init__(self,
                 client,
                 switch_property,
                 switch_function,
                 account,
                 name="Alexa"):
        """Initialize the Alexa Switch device."""
        # Class info
        self._client = client
        self._account = account
        self._name = name
        self._switch_property = switch_property
        self._state = False
        self._switch_function = switch_function

    async def async_added_to_hass(self):
        """Store register state change callback."""
        # Register event handler on bus
        self.hass.bus.async_listen(
            ('{}_{}'.format(
                            ALEXA_DOMAIN,
                            hide_email(self._account)))[0:32],
            self._handle_event)

    def _handle_event(self, event):
        """Handle events.

        This will update PUSH_MEDIA_QUEUE_CHANGE events to see if the switch
        should be updated.
        """
        if 'queue_state' in event.data:
            queue_state = event.data['queue_state']
            if (queue_state['dopplerId']
                    ['deviceSerialNumber'] == self._client.unique_id):
                self._state = getattr(self._client, self._switch_property)
                self.async_schedule_update_ha_state()

    async def _set_switch(self, state, **kwargs):
        success = await self._switch_function(state)
        # if function returns  success, make immediate state change
        if success:
            setattr(self._client, self._switch_property, state)
            _LOGGER.debug("Switch set to %s based on %s",
                          getattr(self._client,
                                  self._switch_property),
                          state)
            self.async_schedule_update_ha_state()
        elif self.should_poll:
            # if we need to poll, refresh media_client
            _LOGGER.debug("Requesting update of %s due to %s switch to %s",
                          self._client,
                          self._name,
                          state)
            await self._client.async_update()

    @property
    def is_on(self):
        """Return true if on."""
        return getattr(self._client, self._switch_property)

    async def async_turn_on(self, **kwargs):
        """Turn on switch."""
        await self._set_switch(True, **kwargs)

    async def async_turn_off(self, **kwargs):
        """Turn off switch."""
        await self._set_switch(False, **kwargs)

    @property
    def unique_id(self):
        """Return the unique ID."""
        return self._client.unique_id + '_' + self._name

    @property
    def name(self):
        """Return the name of the switch."""
        return "{} {} switch".format(self._client.name, self._name)

    @property
    def should_poll(self):
        """Return the polling state."""
        return not (self.hass.data[DATA_ALEXAMEDIA]
                    ['accounts'][self._account]['websocket'])

    async def async_update(self):
        """Update state."""
        try:
            self.async_schedule_update_ha_state()
        except NoEntitySpecifiedError:
            pass  # we ignore this due to a harmless startup race condition


class DNDSwitch(AlexaMediaSwitch):
    """Representation of a Alexa Media Do Not Disturb switch."""

    def __init__(self, client, account):
        """Initialize the Alexa Switch."""
        # Class info
        super().__init__(
            client,
            'dnd_state',
            client.alexa_api.set_dnd_state,
            account,
            "do not disturb")


class ShuffleSwitch(AlexaMediaSwitch):
    """Representation of a Alexa Media Shuffle switch."""

    def __init__(self, client, account):
        """Initialize the Alexa Switch."""
        # Class info
        super().__init__(
            client,
            'shuffle_state',
            client.alexa_api.shuffle,
            account,
            "shuffle")


class RepeatSwitch(AlexaMediaSwitch):
    """Representation of a Alexa Media Repeat switch."""

    def __init__(self, client, account):
        """Initialize the Alexa Switch."""
        # Class info
        super().__init__(
            client,
            'repeat_state',
            client.alexa_api.repeat,
            account,
            "repeat")
