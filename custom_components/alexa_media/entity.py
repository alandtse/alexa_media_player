"""
Base entity for Alexa Media Player.

SPDX-License-Identifier: Apache-2.0

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""

import logging

from alexapy import AlexaAPI, hide_email

from .const import DATA_ALEXAMEDIA

_LOGGER = logging.getLogger(__name__)


class AlexaMedia:
    """Implementation of Alexa Media Base object."""

    def __init__(self, device, login) -> None:
        """Initialize the Alexa device."""
        self._login = login
        self.alexa_api = AlexaAPI(device, login)
        self.email = login.email
        self.account = hide_email(login.email)

    def check_login_changes(self):
        """Update Login object if it has changed."""
        try:
            login = self.hass.data[DATA_ALEXAMEDIA]["accounts"][self.email]["login_obj"]
        except (AttributeError, KeyError):
            return
        if self.alexa_api.update_login(login):
            _LOGGER.debug("Login object has changed; updating")
            self._login = login
            self.email = login.email
            self.account = hide_email(login.email)
