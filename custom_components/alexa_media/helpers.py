#!/usr/bin/env python
# -*- coding: utf-8 -*-
#  SPDX-License-Identifier: Apache-2.0
"""
Helper functions for Alexa Media Player.

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""

import logging
from typing import List
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_component import EntityComponent

_LOGGER = logging.getLogger(__name__)


async def add_devices(devices: List[EntityComponent],
                      add_devices_callback: callable) -> bool:
    """Add devices using add_devices_callback."""
    if devices:
        _LOGGER.debug("Adding %s", devices)
        try:
            add_devices_callback(devices, True)
            return True
        except HomeAssistantError as exception_:
            message = exception_.message  # type: str
            if message.startswith("Entity id already exists"):
                _LOGGER.debug("Device already added: %s",
                              message)
            else:
                _LOGGER.debug("Unable to add devices: %s : %s",
                              devices,
                              message)
    return False
