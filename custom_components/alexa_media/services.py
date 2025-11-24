"""
Alexa Services.

SPDX-License-Identifier: Apache-2.0

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""

import asyncio
from dataclasses import dataclass
import logging
from typing import Any, Callable

from alexapy import AlexaAPI, AlexapyLoginError, hide_email
from alexapy.errors import AlexapyConnectionError
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv, entity_registry as er
import voluptuous as vol

from .const import (
    ATTR_EMAIL,
    ATTR_ENTITY_ID,
    ATTR_NUM_ENTRIES,
    DATA_ALEXAMEDIA,
    DOMAIN,
    SERVICE_ENABLE_NETWORK_DISCOVERY,
    SERVICE_FORCE_LOGOUT,
    SERVICE_GET_HISTORY_RECORDS,
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
        name=SERVICE_FORCE_LOGOUT,
        schema=FORCE_LOGOUT_SCHEMA,
        handler="force_logout",
    ),
    AlexaServiceDef(
        name=SERVICE_UPDATE_LAST_CALLED,
        schema=LAST_CALL_UPDATE_SCHEMA,
        handler="last_call_handler",
    ),
    AlexaServiceDef(
        name=SERVICE_RESTORE_VOLUME,
        schema=RESTORE_VOLUME_SCHEMA,
        handler="restore_volume",
    ),
    AlexaServiceDef(
        name=SERVICE_GET_HISTORY_RECORDS,
        schema=GET_HISTORY_RECORDS_SCHEMA,
        handler="get_history_records",
    ),
    AlexaServiceDef(
        name=SERVICE_ENABLE_NETWORK_DISCOVERY,
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

    async def force_logout(self, call: ServiceCall) -> bool:
        """Handle force logout service request.

        Arguments
            call.ATTR_EMAIL {List[str] | None}: List of case-sensitive Alexa emails.
                                                If None, all accounts are logged out.

        Returns
            bool -- True if at least one account was marked for relogin.
        """
        requested_emails = call.data.get(ATTR_EMAIL)
        _LOGGER.debug("Service force_logout called for: %s", requested_emails)

        accounts = self.hass.data[DATA_ALEXAMEDIA]["accounts"]
        success = False

        for email, account_dict in accounts.items():
            if requested_emails and email not in requested_emails:
                continue

            login_obj = account_dict["login_obj"]

            # This is the effective “force logout” for this account: mark it as
            # requiring reauthentication and notify the user/UI.
            report_relogin_required(self.hass, login_obj, email)
            success = True
            _LOGGER.debug(
                "Marked Alexa Media account %s for relogin via force_logout service",
                hide_email(email),
            )

        if requested_emails and not success:
            _LOGGER.warning(
                "force_logout called for %s but no matching Alexa Media accounts were found",
                requested_emails,
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
        update_last_called = self._functions.get("update_last_called")

        if not callable(update_last_called):
            _LOGGER.error(
                "update_last_called function not registered; cannot update last_called"
            )
            return

        _LOGGER.debug("Service update_last_called called for: %s", requested_emails)

        for email, account_dict in self.hass.data[DATA_ALEXAMEDIA]["accounts"].items():
            if requested_emails and email not in requested_emails:
                continue

            login_obj = account_dict["login_obj"]
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
            blocking=True,
        )

        _LOGGER.debug("Volume restored to %s for entity %s", previous_volume, entity_id)
        return True

    async def get_history_records(self, call: ServiceCall) -> bool:
        """Handle request to get history records and store them on the entity."""
        entity_id = call.data.get(ATTR_ENTITY_ID)
        number_of_entries = call.data.get(ATTR_NUM_ENTRIES)

        # Validate number_of_entries
        try:
            number_of_entries_int = int(number_of_entries)
        except (TypeError, ValueError):
            _LOGGER.exception(
                "Service get_history_records for %s has invalid entries value: %s",
                entity_id,
                number_of_entries,
            )
            return False

        if number_of_entries_int <= 0:
            _LOGGER.error(
                "Service get_history_records for %s with %s entries is invalid; must be > 0",
                entity_id,
                number_of_entries_int,
            )
            return False

        _LOGGER.debug(
            "Service get_history_records for: %s with %s entries",
            entity_id,
            number_of_entries_int,
        )

        # Validate the target entity
        entity_registry = er.async_get(self.hass)
        entity_entry = entity_registry.async_get(entity_id)
        if not entity_entry or entity_entry.platform != DOMAIN:
            _LOGGER.error("Entity %s not found or not part of %s", entity_id, DOMAIN)
            return False
        target_serial_number = entity_entry.unique_id

        history_data_total: list[dict[str, Any]] = []

        async def _collect_history_for_account(login_obj) -> None:
            """Collect history entries for a single account matching the target device."""
            # Get the history records. Input: time_from, time_to (both None here).
            history_data = await AlexaAPI.get_customer_history_records(
                login_obj, None, None
            )
            if not history_data:
                return

            for item in history_data:
                summary = item.get("description", {}).get("summary", "")
                device_serial_number = item.get("deviceSerialNumber")
                timestamp = item.get("creationTimestamp")

                if (
                    not summary
                    or summary == ","
                    or device_serial_number != target_serial_number
                    or timestamp is None
                ):
                    continue

                entry = {
                    "timestamp": timestamp,
                    "summary": summary,
                    "response": item.get("alexaResponse", ""),
                }
                history_data_total.append(entry)

        # Iterate accounts and collect history
        for email, account_dict in self.hass.data[DATA_ALEXAMEDIA]["accounts"].items():
            login_obj = account_dict["login_obj"]
            try:
                await _collect_history_for_account(login_obj)
            except AlexapyConnectionError:
                _LOGGER.exception(
                    "Error retrieving history for %s",
                    hide_email(email),
                )
            except AlexapyLoginError:
                _LOGGER.exception(
                    "Login error retrieving history for %s",
                    hide_email(email),
                )
                report_relogin_required(self.hass, login_obj, email)

            except asyncio.CancelledError:
                # Let HA cancellation propagate
                raise
            except Exception:
                # Fallback for truly unexpected errors
                _LOGGER.exception(
                    "Unexpected error retrieving history for %s",
                    hide_email(email),
                )

        # Sort and limit entries
        history_data_total.sort(key=lambda x: x["timestamp"], reverse=True)
        history_data_total = history_data_total[:number_of_entries_int]

        # Update the entity's attributes
        state = self.hass.states.get(entity_id)
        if state is not None:
            new_attributes = dict(state.attributes)
            new_attributes["history_records"] = history_data_total
            self.hass.states.async_set(entity_id, state.state, new_attributes)
            return True

        _LOGGER.error("Entity %s state not found", entity_id)
        return False

    async def enable_network_discovery(self, call: ServiceCall) -> None:
        """Re-enable network discovery for one or more Alexa accounts."""
        data = call.data or {}
        target_emails: list[str] = data.get(ATTR_EMAIL, [])

        accounts = self.hass.data[DATA_ALEXAMEDIA]["accounts"]
        any_matched = False

        for email, account_dict in accounts.items():
            if target_emails and email not in target_emails:
                continue

            any_matched = True

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

        if target_emails and not any_matched:
            _LOGGER.warning(
                "enable_network_discovery called for %s but no matching Alexa Media accounts were found",
                target_emails,
            )
