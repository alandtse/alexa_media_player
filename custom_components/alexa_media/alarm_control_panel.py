#!/usr/bin/env python
# -*- coding: utf-8 -*-
#  SPDX-License-Identifier: Apache-2.0
"""
Alexa Devices Alarm Control Panel using Guard Mode.

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""
import logging
from typing import List  # noqa pylint: disable=unused-import

from homeassistant import util
from homeassistant.components.alarm_control_panel import AlarmControlPanel
from homeassistant.const import STATE_ALARM_ARMED_AWAY, STATE_ALARM_DISARMED
from homeassistant.helpers.event import async_call_later

from . import (CONF_EMAIL, CONF_EXCLUDE_DEVICES, CONF_INCLUDE_DEVICES,
               DATA_ALEXAMEDIA)
from . import DOMAIN as ALEXA_DOMAIN
from . import MIN_TIME_BETWEEN_FORCED_SCANS, MIN_TIME_BETWEEN_SCANS, hide_email
from .helpers import add_devices, retry_async

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = [ALEXA_DOMAIN]

@retry_async(limit=5, delay=2, catch_exceptions=True)
async def async_setup_platform(hass,
                               config,
                               add_devices_callback,
                               discovery_info=None) -> bool:
    """Set up the Alexa alarm control panel platform."""
    devices = []  # type: List[AlexaAlarmControlPanel]
    config = discovery_info['config']
    account = config[CONF_EMAIL]
    include_filter = config.get(CONF_INCLUDE_DEVICES, [])
    exclude_filter = config.get(CONF_EXCLUDE_DEVICES, [])
    account_dict = hass.data[DATA_ALEXAMEDIA]['accounts'][account]
    if 'alarm_control_panel' not in (account_dict
                                     ['entities']):
        (hass.data[DATA_ALEXAMEDIA]
         ['accounts']
         [account]
         ['entities']['alarm_control_panel']) = {}
    alexa_client: AlexaAlarmControlPanel = AlexaAlarmControlPanel(
        account_dict['login_obj'])
    await alexa_client.init()
    if not (alexa_client and alexa_client.unique_id):
        _LOGGER.debug("%s: Skipping creation of uninitialized device: %s",
                      hide_email(account),
                      alexa_client)
    elif alexa_client.unique_id not in (account_dict
                                        ['entities']
                                        ['alarm_control_panel']):
        devices.append(alexa_client)
        (hass.data[DATA_ALEXAMEDIA]
         ['accounts']
         [account]
         ['entities']
         ['alarm_control_panel'][alexa_client.unique_id]) = alexa_client
    else:
        _LOGGER.debug("%s: Skipping already added device: %s",
                      hide_email(account),
                      alexa_client)
    return await add_devices(hide_email(account),
                             devices, add_devices_callback,
                             include_filter, exclude_filter)


class AlexaAlarmControlPanel(AlarmControlPanel):
    """Implementation of Alexa Media Player alarm control panel."""

    def __init__(self, login) -> None:
        # pylint: disable=unexpected-keyword-arg
        """Initialize the Alexa device."""
        from alexapy import AlexaAPI
        # Class info
        self._login = login
        self.alexa_api = AlexaAPI(self, login)
        self.alexa_api_session = login.session
        self.account = hide_email(login.email)

        # Guard info
        self._appliance_id = None
        self._guard_entity_id = None
        self._friendly_name = "Alexa Guard"
        self._state = None
        self._should_poll = False
        self._attrs = {}

    async def init(self):
        try:
            from simplejson import JSONDecodeError
            data = await self.alexa_api.get_guard_details(self._login)
            guard_dict = (data['locationDetails']
                          ['locationDetails']['Default_Location']
                          ['amazonBridgeDetails']['amazonBridgeDetails']
                          ['LambdaBridge_AAA/OnGuardSmartHomeBridgeService']
                          ['applianceDetails']['applianceDetails'])
        except (KeyError, TypeError, JSONDecodeError):
            guard_dict = {}
        for key, value in guard_dict.items():
            if value['modelName'] == "REDROCK_GUARD_PANEL":
                self._appliance_id = value['applianceId']
                self._guard_entity_id = value['entityId']
                self._friendly_name += " " + self._appliance_id[-5:]
                _LOGGER.debug("%s: Discovered %s: %s %s",
                              self.account,
                              self._friendly_name,
                              self._appliance_id,
                              self._guard_entity_id)
        if not self._appliance_id:
            _LOGGER.debug("%s: No Alexa Guard entity found", self.account)

    async def async_added_to_hass(self):
        """Store register state change callback."""
        # Register event handler on bus
        self.hass.bus.async_listen(('{}_{}'.format(
            ALEXA_DOMAIN,
            hide_email(self._login.email)))[0:32],
            self._handle_event)

    def _handle_event(self, event):
        """Handle websocket events.

        Used instead of polling.
        """
        if 'push_activity' in event.data:
            async_call_later(self.hass, 2, lambda _:
                             self.hass.async_create_task(
                                self.async_update(no_throttle=True)))

    @util.Throttle(MIN_TIME_BETWEEN_SCANS, MIN_TIME_BETWEEN_FORCED_SCANS)
    async def async_update(self):
        """Update Guard state."""
        import json
        _LOGGER.debug("%s: Refreshing %s", self.account, self.name)
        state = None
        state_json = await self.alexa_api.get_guard_state(self._login,
                                                          self._appliance_id)
        # _LOGGER.debug("%s: state_json %s", self.account, state_json)
        if (state_json and 'deviceStates' in state_json
                and state_json['deviceStates']):
            cap = state_json['deviceStates'][0]['capabilityStates']
            # _LOGGER.debug("%s: cap %s", self.account, cap)
            for item_json in cap:
                item = json.loads(item_json)
                # _LOGGER.debug("%s: item %s", self.account, item)
                if item['name'] == 'armState':
                    state = item['value']
                    # _LOGGER.debug("%s: state %s", self.account, state)
        elif state_json['errors']:
            _LOGGER.debug("%s: Error refreshing alarm_control_panel %s: %s",
                          self.account,
                          self.name,
                          json.dumps(state_json['errors']) if state_json
                          else None)
        if state is None:
            return
        if state == "ARMED_AWAY":
            self._state = STATE_ALARM_ARMED_AWAY
        elif state == "ARMED_STAY":
            self._state = STATE_ALARM_DISARMED
        else:
            self._state = STATE_ALARM_DISARMED
        _LOGGER.debug("%s: Alarm State: %s", self.account, self.state)
        self.async_schedule_update_ha_state()

    async def async_alarm_disarm(self, code=None) -> None:
        # pylint: disable=unexpected-keyword-arg
        """Send disarm command.

        We use the arm_home state as Alexa does not have disarm state.
        """
        await self.async_alarm_arm_home()

    async def async_alarm_arm_home(self, code=None) -> None:
        """Send arm home command."""
        await self.alexa_api.set_guard_state(self._login,
                                             self._guard_entity_id,
                                             "ARMED_STAY")
        await self.async_update(no_throttle=True)
        self.async_schedule_update_ha_state()

    async def async_alarm_arm_away(self, code=None) -> None:
        """Send arm away command."""
        # pylint: disable=unexpected-keyword-arg
        await self.alexa_api.set_guard_state(self._login,
                                             self._guard_entity_id,
                                             "ARMED_AWAY")
        await self.async_update(no_throttle=True)
        self.async_schedule_update_ha_state()

    @property
    def unique_id(self):
        """Return the unique ID."""
        return self._guard_entity_id

    @property
    def name(self):
        """Return the name of the device."""
        return self._friendly_name

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self._attrs

    @property
    def should_poll(self):
        """Return the polling state."""
        return self._should_poll or not (self.hass.data[DATA_ALEXAMEDIA]
                                         ['accounts'][self._login.email]
                                         ['websocket'])
