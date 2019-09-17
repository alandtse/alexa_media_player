#!/usr/bin/env python
# -*- coding: utf-8 -*-
#  SPDX-License-Identifier: Apache-2.0
"""
Alexa Devices notification service.

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""
import logging

from homeassistant.components.notify import (ATTR_DATA, ATTR_TARGET,
                                             ATTR_TITLE, ATTR_TITLE_DEFAULT,
                                             SERVICE_NOTIFY,
                                             BaseNotificationService)

from . import CONF_EMAIL, DATA_ALEXAMEDIA, DOMAIN, hide_email, hide_serial
from .helpers import retry_async

_LOGGER = logging.getLogger(__name__)


@retry_async(limit=5, delay=2, catch_exceptions=True)
async def async_get_service(hass, config, discovery_info=None):
    # pylint: disable=unused-argument
    """Get the demo notification service."""
    for account, account_dict in (
            hass.data[DATA_ALEXAMEDIA]['accounts'].items()):
        for key, _ in account_dict['devices']['media_player'].items():
            if key not in account_dict['entities']['media_player']:
                _LOGGER.debug(
                    "%s: Media player %s not loaded yet; delaying load",
                    hide_email(account),
                    hide_serial(key))
                return False
    return AlexaNotificationService(hass)


async def async_unload_entry(hass, entry) -> bool:
    """Unload a config entry."""
    target_account = entry.data[CONF_EMAIL]
    other_accounts = False
    for account, account_dict in (hass.data[DATA_ALEXAMEDIA]
                                  ['accounts'].items()):
        if account == target_account:
            for device in (account_dict['entities']
                                       ['media_player'].values()):
                entity_id = device.entity_id.split('.')
                hass.services.async_remove(
                    SERVICE_NOTIFY,
                    f"{DOMAIN}_{entity_id[1]}")
        else:
            other_accounts = True
    if not other_accounts:
        hass.services.async_remove(SERVICE_NOTIFY, f"{DOMAIN}")
    return True


class AlexaNotificationService(BaseNotificationService):
    """Implement Alexa Media Player notification service."""

    def __init__(self, hass):
        """Initialize the service."""
        self.hass = hass

    async def convert(self, names, type_="entities", filter_matches=False):
        """Return a list of converted Alexa devices based on names.

        Names may be matched either by serialNumber, accountName, or
        Homeassistant entity_id and can return any of the above plus entities

        Parameters
        ----------
        names : list(string)
            A list of names to convert
        type : string
            The type to return entities, entity_ids, serialnumbers, names
        filter_matches : bool
            Whether non-matching items are removed from the returned list.

        Returns
        -------
        list(string)
            List of home assistant entity_ids

        """
        devices = []
        if isinstance(names, str):
            names = [names]
        for item in names:
            matched = False
            for alexa in self.devices:
                _LOGGER.debug("Testing item: %s against (%s, %s, %s, %s)",
                              item,
                              alexa,
                              alexa.name,
                              hide_serial(alexa.unique_id),
                              alexa.entity_id)
                if item in (alexa, alexa.name, alexa.unique_id,
                            alexa.entity_id):
                    if type_ == "entities":
                        converted = alexa
                    elif type_ == "serialnumbers":
                        converted = alexa.unique_id
                    elif type_ == "names":
                        converted = alexa.name
                    elif type_ == "entity_ids":
                        converted = alexa.entity_id
                    devices.append(converted)
                    matched = True
                    _LOGGER.debug("Converting: %s to (%s): %s",
                                  item,
                                  type_,
                                  converted)
            if not filter_matches and not matched:
                devices.append(item)
        return devices

    @property
    def targets(self):
        """Return a dictionary of Alexa devices."""
        devices = {}
        for _, account_dict in (self.hass.data[DATA_ALEXAMEDIA]
                                ['accounts'].items()):
            if ('devices' not in account_dict):
                return devices
            for serial, alexa in (account_dict
                                  ['devices']['media_player'].items()):
                devices[alexa['accountName']] = serial
        return devices

    @property
    def devices(self):
        """Return a list of Alexa devices."""
        devices = []
        if ('accounts' not in self.hass.data[DATA_ALEXAMEDIA] and
                not self.hass.data[DATA_ALEXAMEDIA]['accounts'].items()):
            return devices
        for _, account_dict in (self.hass.data[DATA_ALEXAMEDIA]
                                ['accounts'].items()):
            devices = devices + list(account_dict
                                     ['entities']['media_player'].values())
        return devices

    async def async_send_message(self, message="", **kwargs):
        """Send a message to a Alexa device."""
        _LOGGER.debug("Message: %s, kwargs: %s",
                      message,
                      kwargs)
        kwargs['message'] = message
        targets = kwargs.get(ATTR_TARGET)
        title = (kwargs.get(ATTR_TITLE) if ATTR_TITLE in kwargs
                 else ATTR_TITLE_DEFAULT)
        data = kwargs.get(ATTR_DATA)
        if isinstance(targets, str):
            targets = [targets]
        entities = await self.convert(targets, type_="entities")
        try:
            entities.extend(self.hass.components.group.expand_entity_ids(
                entities))
        except ValueError:
            _LOGGER.debug("Invalid Home Assistant entity in %s", entities)
        if data['type'] == "tts":
            targets = await self.convert(entities, type_="entities",
                                         filter_matches=True)
            _LOGGER.debug("TTS entities: %s", targets)
            for alexa in targets:
                _LOGGER.debug("TTS by %s : %s", alexa, message)
                await alexa.async_send_tts(message)
        elif data['type'] == "announce":
            targets = await self.convert(entities, type_="serialnumbers",
                                         filter_matches=True)
            _LOGGER.debug("Announce targets: %s entities: %s",
                          list(map(hide_serial, targets)),
                          entities)
            for account, account_dict in (self.hass.data[DATA_ALEXAMEDIA]
                                          ['accounts'].items()):
                for alexa in (account_dict['entities']
                              ['media_player'].values()):
                    if alexa.unique_id in targets and alexa.available:
                        _LOGGER.debug(("%s: Announce by %s to "
                                       "targets: %s: %s"),
                                      hide_email(account),
                                      alexa,
                                      list(map(hide_serial, targets)),
                                      message)
                        await alexa.async_send_announcement(
                            message,
                            targets=targets,
                            title=title,
                            method=(data['method'] if
                                    'method' in data
                                    else 'all'))
                        break
        elif data['type'] == "push":
            targets = await self.convert(entities, type_="entities",
                                         filter_matches=True)
            for alexa in targets:
                _LOGGER.debug("Push by %s : %s %s", alexa, title, message)
                await alexa.async_send_mobilepush(message, title=title)
