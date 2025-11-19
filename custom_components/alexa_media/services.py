"""
Alexa Services.

SPDX-License-Identifier: Apache-2.0

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""

from dataclasses import dataclass
import logging
from typing import Any, Callable

from alexapy import AlexaAPI, AlexapyLoginError, hide_email
from alexapy.errors import AlexapyConnectionError
from homeassistant.const import ATTR_DEVICE_ID, ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv, entity_registry as er
import voluptuous as vol

from .const import ATTR_EMAIL, ATTR_NUM_ENTRIES, DATA_ALEXAMEDIA, DOMAIN
from .helpers import _catch_login_errors, report_relogin_required

_LOGGER = logging.getLogger(__name__)


FORCE_LOGOUT_SCHEMA = vol.Schema(
    {vol.Optional(ATTR_EMAIL, default=[]): vol.All(cv.ensure_list, [cv.string])}
)
LAST_CALL_UPDATE_SCHEMA = vol.Schema(
    {vol.Optional(ATTR_EMAIL, default=[]): vol.All(cv.ensure_list, [cv.string])}
)
RESTORE_VOLUME_SCHEMA = vol.Schema({vol.Required(ATTR_ENTITY_ID): cv.entity_id})

GET_HISTORY_RECORDS_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_id,
        vol.Optional(ATTR_NUM_ENTRIES, default=5): cv.positive_int,
    }
)

ENABLE_NETWORK_DISCOVERY_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_EMAIL, default=[]): vol.All(
            cv.ensure_list,
            [cv.string],
        ),
    }
)


@dataclass(frozen=True)
class AlexaServiceDef:
    """Definition for an Alexa Media custom service."""

    name: str  # service name as exposed in HA: alexa_media.<name>
    schema: vol.Schema  # voluptuous schema
    handler: str  # method name on AlexaMediaServices


SERVICE_DEFS: tuple[AlexaServiceDef, ...] = (
    AlexaServiceDef(
        name="force_logout",
        schema=FORCE_LOGOUT_SCHEMA,
        handler="force_logout",
    ),
    AlexaServiceDef(
        name="update_last_called",
        schema=LAST_CALL_UPDATE_SCHEMA,
        handler="last_call_handler",
    ),
    AlexaServiceDef(
        name="restore_volume",
        schema=RESTORE_VOLUME_SCHEMA,
        handler="restore_volume",
    ),
    AlexaServiceDef(
        name="get_history_records",
        schema=GET_HISTORY_RECORDS_SCHEMA,
        handler="get_history_records",
    ),
    AlexaServiceDef(
        name="enable_network_discovery",
        schema=ENABLE_NETWORK_DISCOVERY_SCHEMA,
        handler="enable_network_discovery",
    ),
)


class AlexaMediaServices:
    def __init__(self, hass: HomeAssistant, functions: dict[str, Callable[..., Any]]):
        self.hass = hass
        self._functions = functions

    async def register(self) -> None:
        """Register Alexa Media custom services."""
        for service_def in SERVICE_DEFS:
            handler = getattr(self, service_def.handler)
            self.hass.services.async_register(
                DOMAIN,
                service_def.name,
                handler,
                schema=service_def.schema,
            )

    async def unregister(self) -> None:
        """Unregister Alexa Media custom services."""
        for service_def in SERVICE_DEFS:
            self.hass.services.async_remove(DOMAIN, service_def.name)

    @_catch_login_errors
    async def force_logout(self, call: ServiceCall) -> bool:
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
                # We successfully called force_logout for this account
                success = True
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
    async def last_call_handler(self, call: ServiceCall) -> None:
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
            update_last_called = self._functions.get("update_last_called")
            if not callable(update_last_called):
                _LOGGER.error(
                    "update_last_called function not registered; "
                    "skipping update for %s",
                    hide_email(email),
                )
                continue
            try:
                await update_last_called(login_obj)
            except AlexapyLoginError:
                report_relogin_required(self.hass, login_obj, email)
            except AlexapyConnectionError:
                _LOGGER.error(
                    "Unable to connect to Alexa for %s;"
                    " check your network connection and try again",
                    hide_email(email),
                )
    
    async def restore_volume(self, call: ServiceCall) -> bool:
        """Handle restore volume service request.

        Arguments:
            call.ATTR_ENTITY_ID {str: None} -- Alexa Media Player entity.

        """
        entity_id = call.data.get(ATTR_ENTITY_ID)
        _LOGGER.debug("Service restore_volume called for: %s", entity_id)

        # Retrieve the entity registry and entity entry
        entity_registry = er.async_get(self.hass)
        entity_entry = entity_registry.async_get(entity_id)

        if not entity_entry:
            _LOGGER.error("Entity %s not found in registry", entity_id)
            return False

        # Retrieve the state and attributes
        state = self.hass.states.get(entity_id)
        if not state:
            _LOGGER.warning("Entity %s has no state; cannot restore volume", entity_id)
            return False

        previous_volume = state.attributes.get("previous_volume")
        current_volume = state.attributes.get("volume_level")

        if previous_volume is None:
            _LOGGER.warning(
                "Previous volume not found for %s; attempting to use current volume level: %s",
                entity_id,
                current_volume,
            )
            previous_volume = current_volume

        if previous_volume is None:
            _LOGGER.warning(
                "No valid volume levels found for entity %s; cannot restore volume",
                entity_id,
            )
            return False

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

    async def get_history_records(self, call: ServiceCall) -> bool:
        """Handle request to get history records and store them on the entity."""
        entity_id = call.data.get(ATTR_ENTITY_ID)
        number_of_entries = call.data.get(ATTR_NUM_ENTRIES)
        _LOGGER.debug(
            "Service get_history_records for: %s with %d entries",
            entity_id,
            number_of_entries,
        )

        # Validate the target entity
        entity_registry = er.async_get(self.hass)
        entity_entry = entity_registry.async_get(entity_id)
        if not entity_entry or entity_entry.platform != DOMAIN:
            _LOGGER.error("Entity %s not found or not part of %s", entity_id, DOMAIN)
            return False
        target_serial_number = entity_entry.unique_id

        history_data_total = []
        for email, account_dict in self.hass.data[DATA_ALEXAMEDIA]["accounts"].items():
            login_obj = account_dict["login_obj"]
            try:
                # Get the history records. Input: Time from, Time to,
                history_data = await AlexaAPI.get_customer_history_records(
                    login_obj, None, None
                )
                if history_data:
                    for item in history_data:
                        summary = item.get("description", {}).get("summary", "")
                        device_serial_number = item.get("deviceSerialNumber")
                        if (
                            not summary
                            or summary == ","
                            or device_serial_number != target_serial_number
                        ):
                            continue
                        entry = {
                            "timestamp": item.get("creationTimestamp"),
                            "summary": summary,
                            "response": item.get("alexaResponse", ""),
                        }
                        history_data_total.append(entry)
            except Exception as e:
                _LOGGER.error(
                    "Error retrieving history for %s: %s", hide_email(email), str(e)
                )

        # Sort and limit entries
        history_data_total.sort(key=lambda x: x["timestamp"], reverse=True)
        history_data_total = history_data_total[:number_of_entries]

        # Update the entity's attributes
        state = self.hass.states.get(entity_id)
        if state and self.hass.states.async_set:
            new_attributes = dict(state.attributes)
            new_attributes["history_records"] = history_data_total
            self.hass.states.async_set(entity_id, state.state, new_attributes)
        else:
            _LOGGER.error("Entity %s state not found", entity_id)
            return False

        return True

    @_catch_login_errors
    async def enable_network_discovery(self, call: ServiceCall) -> None:
        """Re-enable network discovery for one or more Alexa accounts."""
        data = call.data or {}
        target_emails: list[str] = data.get(ATTR_EMAIL, [])

        accounts = self.hass.data[DATA_ALEXAMEDIA]["accounts"]

        for email, account_dict in accounts.items():
            if target_emails and email not in target_emails:
                continue

            if "should_get_network" not in account_dict:
                _LOGGER.debug(
                    "Account %s has no 'should_get_network' flag; skipping",
                    hide_email(email),
                )
                continue

            account_dict["should_get_network"] = True
            _LOGGER.debug(
                "Re-enabled network discovery for Alexa Media account %s",
                hide_email(email),
            )
