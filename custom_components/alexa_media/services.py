"""
Alexa Services.

SPDX-License-Identifier: Apache-2.0

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""

import logging
from typing import Callable

from alexapy import AlexaAPI, AlexapyLoginError, hide_email
from alexapy.errors import AlexapyConnectionError
from homeassistant.const import ATTR_DEVICE_ID, ATTR_ENTITY_ID
from homeassistant.helpers import config_validation as cv, entity_registry as er
import voluptuous as vol

from .const import (
    ATTR_EMAIL,
    ATTR_NUM_ENTRIES,
    DATA_ALEXAMEDIA,
    DOMAIN,
    SERVICE_FORCE_LOGOUT,
    SERVICE_RESTORE_VOLUME,
    SERVICE_UPDATE_LAST_CALLED,
)
from .helpers import _catch_login_errors, report_relogin_required

_LOGGER = logging.getLogger(__name__)


FORCE_LOGOUT_SCHEMA = vol.Schema(
    {vol.Optional(ATTR_EMAIL, default=[]): vol.All(cv.ensure_list, [cv.string])}
)
LAST_CALL_UPDATE_SCHEMA = vol.Schema(
    {vol.Optional(ATTR_EMAIL, default=[]): vol.All(cv.ensure_list, [cv.string])}
)
RESTORE_VOLUME_SCHEMA = vol.Schema({vol.Required(ATTR_ENTITY_ID): cv.entity_id})


class AlexaMediaServices:
    """Class that holds our services that should be published to hass."""

    def __init__(self, hass, functions: dict[str, Callable]):
        """Initialize with self.hass."""
        self.hass = hass
        self.functions: dict[str, Callable] = functions

    async def register(self):
        """Register services to hass."""
        self.hass.services.async_register(
            DOMAIN, SERVICE_FORCE_LOGOUT, self.force_logout, schema=FORCE_LOGOUT_SCHEMA
        )
        self.hass.services.async_register(
            DOMAIN,
            SERVICE_UPDATE_LAST_CALLED,
            self.last_call_handler,
            schema=LAST_CALL_UPDATE_SCHEMA,
        )
        self.hass.services.async_register(
            DOMAIN,
            SERVICE_RESTORE_VOLUME,
            self.restore_volume,
            schema=RESTORE_VOLUME_SCHEMA,
        )

    async def unregister(self):
        """Deregister services from hass."""
        self.hass.services.async_remove(DOMAIN, SERVICE_FORCE_LOGOUT)
        self.hass.services.async_remove(
            DOMAIN,
            SERVICE_UPDATE_LAST_CALLED,
        )
        self.hass.services.async_remove(
            DOMAIN,
            SERVICE_RESTORE_VOLUME,
        )

    @_catch_login_errors
    async def force_logout(self, call) -> bool:
        """Handle force logout service request.

        Arguments
            call.ATTR_EMAIL {List[str: None]}: List of case-sensitive Alexa emails.
                                               If None, all accounts are logged out.

        Returns
            bool -- True if force logout successful

        """
        requested_emails = call.data.get(ATTR_EMAIL)

        _LOGGER.debug("Service force_logout called for: %s", requested_emails)
        success = False
        for email, account_dict in self.hass.data[DATA_ALEXAMEDIA]["accounts"].items():
            if requested_emails and email not in requested_emails:
                continue
            login_obj = account_dict["login_obj"]
            try:
                await AlexaAPI.force_logout()
            except AlexapyLoginError:
                report_relogin_required(self.hass, login_obj, email)
                success = True
            except AlexapyConnectionError:
                _LOGGER.error(
                    "Unable to connect to Alexa for %s;"
                    " check your network connection and try again",
                    hide_email(email),
                )
        return success

    @_catch_login_errors
    async def last_call_handler(self, call):
        """Handle last call service request.

        Arguments
        call.ATTR_EMAIL: {List[str: None]}: List of case-sensitive Alexa emails.
                                            If None, all accounts are updated.

        """
        requested_emails = call.data.get(ATTR_EMAIL)
        _LOGGER.debug("Service update_last_called for: %s", requested_emails)
        for email, account_dict in self.hass.data[DATA_ALEXAMEDIA]["accounts"].items():
            if requested_emails and email not in requested_emails:
                continue
            login_obj = account_dict["login_obj"]
            try:
                await self.functions.get("update_last_called")(login_obj)
            except AlexapyLoginError:
                report_relogin_required(self.hass, login_obj, email)
            except AlexapyConnectionError:
                _LOGGER.error(
                    "Unable to connect to Alexa for %s;"
                    " check your network connection and try again",
                    hide_email(email),
                )

    async def restore_volume(self, call) -> bool:
        """Handle restore volume service request.

        Arguments
            call.ATTR_ENTITY_ID {str: None} -- Alexa media player entity.

        """
        entity_id = call.data.get(ATTR_ENTITY_ID)
        _LOGGER.debug("Service restore_volume called for: %s", entity_id)

        # Retrieve the entity registry and entity entry
        entity_registry = er.async_get(self.hass)
        entity_entry = entity_registry.async_get(entity_id)

        if not entity_entry:
            _LOGGER.error("Entity %s not found in registry", entity_id)
            return False

        # Retrieve the previous volume from the entity's state attributes
        state = self.hass.states.get(entity_id)
        if not state or "previous_volume" not in state.attributes:
            _LOGGER.error(
                "Previous volume attribute not found for entity %s", entity_id
            )
            return False

        previous_volume = state.attributes["previous_volume"]

        # Call the volume_set service with the retrieved volume
        await self.hass.services.async_call(
            domain="media_player",
            service="volume_set",
            service_data={
                "volume_level": previous_volume,
            },
            target={"entity_id": entity_id},
        )

        _LOGGER.debug("Volume restored to %s for entity %s", previous_volume, entity_id)
        return True
