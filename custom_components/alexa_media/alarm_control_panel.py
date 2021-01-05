#!/usr/bin/env python
# -*- coding: utf-8 -*-
#  SPDX-License-Identifier: Apache-2.0
"""
Alexa Devices Alarm Control Panel using Guard Mode.

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""
from asyncio import sleep
import logging
from typing import Dict, List, Text  # noqa pylint: disable=unused-import

from alexapy import AlexaAPI, hide_email, hide_serial
from homeassistant import util
from homeassistant.const import (
    CONF_EMAIL,
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_DISARMED,
    STATE_UNAVAILABLE,
)
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_call_later
from simplejson import JSONDecodeError

from .alexa_media import AlexaMedia
from .const import (
    CONF_EXCLUDE_DEVICES,
    CONF_INCLUDE_DEVICES,
    CONF_QUEUE_DELAY,
    DATA_ALEXAMEDIA,
    DEFAULT_QUEUE_DELAY,
    DOMAIN as ALEXA_DOMAIN,
    MIN_TIME_BETWEEN_FORCED_SCANS,
    MIN_TIME_BETWEEN_SCANS,
)
from .helpers import _catch_login_errors, add_devices

try:
    from homeassistant.components.alarm_control_panel import (
        AlarmControlPanelEntity as AlarmControlPanel,
    )
except ImportError:
    from homeassistant.components.alarm_control_panel import AlarmControlPanel


_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = [ALEXA_DOMAIN]


async def async_setup_platform(
    hass, config, add_devices_callback, discovery_info=None
) -> bool:
    """Set up the Alexa alarm control panel platform."""
    devices = []  # type: List[AlexaAlarmControlPanel]
    account = config[CONF_EMAIL]
    include_filter = config.get(CONF_INCLUDE_DEVICES, [])
    exclude_filter = config.get(CONF_EXCLUDE_DEVICES, [])
    account_dict = hass.data[DATA_ALEXAMEDIA]["accounts"][account]
    guard_media_players = {}
    for key, device in account_dict["devices"]["media_player"].items():
        if key not in account_dict["entities"]["media_player"]:
            _LOGGER.debug(
                "%s: Media player %s not loaded yet; delaying load",
                hide_email(account),
                hide_serial(key),
            )
            raise ConfigEntryNotReady
        if "GUARD_EARCON" in device["capabilities"]:
            guard_media_players[key] = account_dict["entities"]["media_player"][key]
    if "alarm_control_panel" not in (account_dict["entities"]):
        (
            hass.data[DATA_ALEXAMEDIA]["accounts"][account]["entities"][
                "alarm_control_panel"
            ]
        ) = {}
    alexa_client: AlexaAlarmControlPanel = AlexaAlarmControlPanel(
        account_dict["login_obj"], guard_media_players
    )
    await alexa_client.init()
    if not (alexa_client and alexa_client.unique_id):
        _LOGGER.debug(
            "%s: Skipping creation of uninitialized device: %s",
            hide_email(account),
            alexa_client,
        )
    elif alexa_client.unique_id not in (
        account_dict["entities"]["alarm_control_panel"]
    ):
        devices.append(alexa_client)
        (
            hass.data[DATA_ALEXAMEDIA]["accounts"][account]["entities"][
                "alarm_control_panel"
            ][alexa_client.unique_id]
        ) = alexa_client
    else:
        _LOGGER.debug(
            "%s: Skipping already added device: %s", hide_email(account), alexa_client
        )
    return await add_devices(
        hide_email(account),
        devices,
        add_devices_callback,
        include_filter,
        exclude_filter,
    )


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Set up the Alexa alarm control panel platform by config_entry."""
    return await async_setup_platform(
        hass, config_entry.data, async_add_devices, discovery_info=None
    )


async def async_unload_entry(hass, entry) -> bool:
    """Unload a config entry."""
    account = entry.data[CONF_EMAIL]
    account_dict = hass.data[DATA_ALEXAMEDIA]["accounts"][account]
    for device in account_dict["entities"]["alarm_control_panel"].values():
        await device.async_remove()
    return True


class AlexaAlarmControlPanel(AlarmControlPanel, AlexaMedia):
    """Implementation of Alexa Media Player alarm control panel."""

    def __init__(self, login, media_players=None) -> None:
        # pylint: disable=unexpected-keyword-arg
        """Initialize the Alexa device."""
        super().__init__(None, login)
        # AlexaAPI requires a AlexaClient object, need to clean this up
        self._available = None
        self._assumed_state = None

        # Guard info
        self._appliance_id = None
        self._guard_entity_id = None
        self._friendly_name = "Alexa Guard"
        self._state = None
        self._should_poll = False
        self._attrs: Dict[Text, Text] = {}
        self._media_players = {} or media_players

    @_catch_login_errors
    async def init(self):
        """Initialize."""
        try:

            data = await self.alexa_api.get_guard_details(self._login)
            guard_dict = data["locationDetails"]["locationDetails"]["Default_Location"][
                "amazonBridgeDetails"
            ]["amazonBridgeDetails"]["LambdaBridge_AAA/OnGuardSmartHomeBridgeService"][
                "applianceDetails"
            ][
                "applianceDetails"
            ]
        except (KeyError, TypeError, JSONDecodeError):
            guard_dict = {}
        for _, value in guard_dict.items():
            if value["modelName"] == "REDROCK_GUARD_PANEL":
                self._appliance_id = value["applianceId"]
                self._guard_entity_id = value["entityId"]
                self._friendly_name += " " + self._appliance_id[-5:]
                _LOGGER.debug(
                    "%s: Discovered %s: %s %s",
                    self.account,
                    self._friendly_name,
                    self._appliance_id,
                    self._guard_entity_id,
                )
        if not self._appliance_id:
            _LOGGER.debug("%s: No Alexa Guard entity found", self.account)

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
            f"{ALEXA_DOMAIN}_{hide_email(self._login.email)}"[0:32],
            self._handle_event,
        )
        await self.async_update()

    async def async_will_remove_from_hass(self):
        """Prepare to remove entity."""
        # Register event handler on bus
        self._listener()

    def _handle_event(self, event):
        """Handle websocket events.

        Used instead of polling.
        """
        try:
            if not self.enabled:
                return
        except AttributeError:
            pass
        if "push_activity" in event:
            async_call_later(
                self.hass,
                2,
                lambda _: self.hass.async_create_task(
                    self.async_update(no_throttle=True)
                ),
            )

    @util.Throttle(MIN_TIME_BETWEEN_SCANS, MIN_TIME_BETWEEN_FORCED_SCANS)
    @_catch_login_errors
    async def async_update(self):
        """Update Guard state."""
        try:
            if not self.enabled:
                return
        except AttributeError:
            pass
        import json

        if self._login.session.closed:
            self._available = False
            self._assumed_state = True
            return
        _LOGGER.debug("%s: Refreshing %s", self.account, self.name)
        state = None
        state_json = await self.alexa_api.get_guard_state(
            self._login, self._appliance_id
        )
        # _LOGGER.debug("%s: state_json %s", self.account, state_json)
        if state_json and "deviceStates" in state_json and state_json["deviceStates"]:
            cap = state_json["deviceStates"][0]["capabilityStates"]
            # _LOGGER.debug("%s: cap %s", self.account, cap)
            for item_json in cap:
                item = json.loads(item_json)
                # _LOGGER.debug("%s: item %s", self.account, item)
                if item["name"] == "armState":
                    state = item["value"]
                    # _LOGGER.debug("%s: state %s", self.account, state)
        elif state_json["errors"]:
            _LOGGER.debug(
                "%s: Error refreshing alarm_control_panel %s: %s",
                self.account,
                self.name,
                json.dumps(state_json["errors"]) if state_json else None,
            )
        if state is None:
            self._available = False
            self._assumed_state = True
            return
        if state == "ARMED_AWAY":
            self._state = STATE_ALARM_ARMED_AWAY
        elif state == "ARMED_STAY":
            self._state = STATE_ALARM_DISARMED
        else:
            self._state = STATE_ALARM_DISARMED
        self._available = True
        self._assumed_state = False
        _LOGGER.debug("%s: Alarm State: %s", self.account, self.state)
        self.async_write_ha_state()

    @_catch_login_errors
    async def _async_alarm_set(self, command: Text = "", code=None) -> None:
        # pylint: disable=unexpected-keyword-arg
        """Send command."""
        try:
            if not self.enabled:
                return
        except AttributeError:
            pass
        if command not in (STATE_ALARM_ARMED_AWAY, STATE_ALARM_DISARMED):
            _LOGGER.error("Invalid command: %s", command)
            return
        command_map = {STATE_ALARM_ARMED_AWAY: "AWAY", STATE_ALARM_DISARMED: "HOME"}
        available_media_players = list(
            filter(lambda x: x.state != STATE_UNAVAILABLE, self._media_players.values())
        )
        if available_media_players:
            _LOGGER.debug("Sending guard command to: %s", available_media_players[0])
            available_media_players[0].check_login_changes()
            await available_media_players[0].alexa_api.set_guard_state(
                self._appliance_id.split("_")[2],
                command_map[command],
                queue_delay=self.hass.data[DATA_ALEXAMEDIA]["accounts"][self.email][
                    "options"
                ].get(CONF_QUEUE_DELAY, DEFAULT_QUEUE_DELAY),
            )
            await sleep(2)  # delay
        else:
            _LOGGER.debug("Performing static guard command")
            await self.alexa_api.static_set_guard_state(
                self._login, self._guard_entity_id, command
            )
        await self.async_update(no_throttle=True)
        self.async_write_ha_state()

    async def async_alarm_disarm(self, code=None) -> None:
        # pylint: disable=unexpected-keyword-arg
        """Send disarm command."""
        await self._async_alarm_set(STATE_ALARM_DISARMED)

    async def async_alarm_arm_away(self, code=None) -> None:
        """Send arm away command."""
        # pylint: disable=unexpected-keyword-arg
        await self._async_alarm_set(STATE_ALARM_ARMED_AWAY)

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
        return self._should_poll or not (
            self.hass.data[DATA_ALEXAMEDIA]["accounts"][self._login.email]["websocket"]
        )

    @property
    def supported_features(self) -> int:
        """Return the list of supported features."""
        try:
            from homeassistant.components.alarm_control_panel import (
                SUPPORT_ALARM_ARM_AWAY,
            )
        except ImportError:
            return 0
        return SUPPORT_ALARM_ARM_AWAY

    @property
    def available(self):
        """Return the availability of the device."""
        return self._available

    @property
    def assumed_state(self):
        """Return whether the state is an assumed_state."""
        return self._assumed_state
