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
from homeassistant.helpers.event import call_later

from . import DATA_ALEXAMEDIA
from . import DOMAIN as ALEXA_DOMAIN
from . import (
    MIN_TIME_BETWEEN_FORCED_SCANS, MIN_TIME_BETWEEN_SCANS,
    hide_email, hide_serial
)

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_devices_callback,
                   discovery_info=None):
    """Set up the Alexa switch platform."""
    _LOGGER.debug("Loading switches")
    devices = []  # type: List[DNDSwitch]
    SWITCH_TYPES = [
        ('dnd', DNDSwitch),
        ('shuffle', ShuffleSwitch),
        ('repeat', RepeatSwitch)
    ]
    for account, account_dict in (hass.data[DATA_ALEXAMEDIA]
                                  ['accounts'].items()):
        for key, device in account_dict['devices']['media_player'].items():
            if 'switch' not in account_dict['entities']:
                (hass.data[DATA_ALEXAMEDIA]
                 ['accounts']
                 [account]
                 ['entities']
                 ['switch']) = {}
            if key not in account_dict['entities']['media_player']:
                _LOGGER.debug("Media Players not loaded yet; delaying load")
                call_later(hass, 5, lambda _:
                           setup_platform(hass,
                                          config,
                                          add_devices_callback,
                                          discovery_info))
                return True
            elif key not in account_dict['entities']['switch']:
                (hass.data[DATA_ALEXAMEDIA]
                 ['accounts']
                 [account]
                 ['entities']
                 ['switch'][key]) = {}
                for (switch_key, class_) in SWITCH_TYPES:
                    alexa_client = class_(account_dict['entities']
                                          ['media_player']
                                          [key])  # type: AlexaMediaSwitch
                    (hass.data[DATA_ALEXAMEDIA]
                     ['accounts']
                     [account]
                     ['entities']
                     ['switch'][key][switch_key]) = alexa_client
                    _LOGGER.debug("%s: Found %s %s switch",
                                  hide_email(account),
                                  hide_serial(key),
                                  switch_key)
                    devices.append(alexa_client)
    if devices:
        add_devices_callback(devices, True)
    return True


class AlexaMediaSwitch(SwitchDevice):
    """Representation of a Alexa Media switch."""

    def __init__(self,
                 client,
                 switch_property,
                 switch_function,
                 name="Alexa"):
        """Initialize the Alexa Switch device."""
        # Class info
        self._client = client
        self._name = name
        self._switch_property = switch_property
        self._switch_function = switch_function
        _LOGGER.debug("Creating %s switch for %s", name, client)

    def _set_switch(self, state, **kwargs):
        success = self._switch_function(state)
        # if function returns  success, make immediate state change
        if success:
            self._switch_property = state

    @property
    def is_on(self):
        """Return true if on."""
        return self._switch_property

    def turn_on(self, **kwargs):
        """Turn on switch."""
        self._set_switch(True, **kwargs)

    def turn_off(self, **kwargs):
        """Turn off switch."""
        self._set_switch(False, **kwargs)

    @property
    def name(self):
        """Return the name of the switch."""
        return "{} {} switch".format(self._client.name, self._name)


class DNDSwitch(AlexaMediaSwitch):
    """Representation of a Alexa Media Do Not Disturb switch."""

    def __init__(self, client):
        """Initialize the Alexa Switch."""
        # Class info
        super().__init__(client,
                         client.dnd_state,
                         client.alexa_api.set_dnd_state,
                         "do not disturb")


class ShuffleSwitch(AlexaMediaSwitch):
    """Representation of a Alexa Media Shuffle switch."""

    def __init__(self, client):
        """Initialize the Alexa Switch."""
        # Class info
        super().__init__(client,
                         client.shuffle_state,
                         client.alexa_api.shuffle,
                         "shuffle")


class RepeatSwitch(AlexaMediaSwitch):
    """Representation of a Alexa Media Repeat switch."""

    def __init__(self, client):
        """Initialize the Alexa Switch."""
        # Class info
        super().__init__(client,
                         client.repeat_state,
                         client.alexa_api.repeat,
                         "repeat")
