#!/usr/bin/env python
# -*- coding: utf-8 -*-
#  SPDX-License-Identifier: Apache-2.0
"""
Alexa Config Flow.

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""
from collections import OrderedDict
from datetime import timedelta
import logging
from typing import Text

from alexapy import AlexaLogin, AlexapyConnectionError, hide_email, obfuscate
from homeassistant import config_entries
from homeassistant.const import (
    CONF_EMAIL,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_URL,
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .const import (
    CONF_DEBUG,
    CONF_EXCLUDE_DEVICES,
    CONF_INCLUDE_DEVICES,
    CONF_QUEUE_DELAY,
    DATA_ALEXAMEDIA,
    DEFAULT_QUEUE_DELAY,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


@callback
def configured_instances(hass):
    """Return a set of configured Alexa Media instances."""
    return set(entry.title for entry in hass.config_entries.async_entries(DOMAIN))


@config_entries.HANDLERS.register(DOMAIN)
class AlexaMediaFlowHandler(config_entries.ConfigFlow):
    """Handle a Alexa Media config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def _update_ord_dict(self, old_dict: OrderedDict, new_dict: dict) -> OrderedDict:
        result: OrderedDict = OrderedDict()
        for k, v in old_dict.items():
            for key, value in new_dict.items():
                if k == key:
                    result.update([(key, value)])
                    break
            if k not in result:
                result.update([(k, v)])
        return result

    def __init__(self):
        """Initialize the config flow."""
        self.login = None
        self.config = OrderedDict()
        self.data_schema = OrderedDict(
            [
                (vol.Required(CONF_EMAIL), str),
                (vol.Required(CONF_PASSWORD), str),
                (vol.Optional("securitycode"), str),
                (vol.Required(CONF_URL, default="amazon.com"), str),
                (vol.Optional(CONF_DEBUG, default=False), bool),
                (vol.Optional(CONF_INCLUDE_DEVICES, default=""), str),
                (vol.Optional(CONF_EXCLUDE_DEVICES, default=""), str),
                (vol.Optional(CONF_SCAN_INTERVAL, default=60), int),
            ]
        )
        self.captcha_schema = OrderedDict(
            [
                (vol.Required(CONF_PASSWORD), str),
                (vol.Optional("securitycode"), str),
                (vol.Required("captcha"), str),
            ]
        )
        self.twofactor_schema = OrderedDict([(vol.Required("securitycode"), str)])
        self.claimspicker_schema = OrderedDict(
            [
                (
                    vol.Required("claimsoption", default=0),
                    vol.All(cv.positive_int, vol.Clamp(min=0)),
                )
            ]
        )
        self.authselect_schema = OrderedDict(
            [
                (
                    vol.Required("authselectoption", default=0),
                    vol.All(cv.positive_int, vol.Clamp(min=0)),
                )
            ]
        )
        self.verificationcode_schema = OrderedDict(
            [(vol.Required("verificationcode"), str)]
        )

    async def async_step_import(self, import_config):
        """Import a config entry from configuration.yaml."""
        return await self.async_step_user(import_config)

    async def async_step_user(self, user_input=None):
        """Handle the start of the config flow."""
        if not user_input:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(self.data_schema),
                description_placeholders={"message": ""},
            )

        if (
            f"{user_input[CONF_EMAIL]} - {user_input[CONF_URL]}"
            in configured_instances(self.hass)
        ):
            return self.async_show_form(
                step_id="user",
                errors={CONF_EMAIL: "identifier_exists"},
                description_placeholders={"message": f""},
            )

        self.config[CONF_EMAIL] = user_input[CONF_EMAIL]
        self.config[CONF_PASSWORD] = user_input[CONF_PASSWORD]
        self.config[CONF_URL] = user_input[CONF_URL]
        self.config[CONF_DEBUG] = user_input[CONF_DEBUG]

        self.config[CONF_SCAN_INTERVAL] = (
            user_input[CONF_SCAN_INTERVAL]
            if not isinstance(user_input[CONF_SCAN_INTERVAL], timedelta)
            else user_input[CONF_SCAN_INTERVAL].total_seconds()
        )
        if isinstance(user_input[CONF_INCLUDE_DEVICES], str):
            self.config[CONF_INCLUDE_DEVICES] = (
                user_input[CONF_INCLUDE_DEVICES].split(",")
                if CONF_INCLUDE_DEVICES in user_input
                and user_input[CONF_INCLUDE_DEVICES] != ""
                else []
            )
        else:
            self.config[CONF_INCLUDE_DEVICES] = user_input[CONF_INCLUDE_DEVICES]
        if isinstance(user_input[CONF_EXCLUDE_DEVICES], str):
            self.config[CONF_EXCLUDE_DEVICES] = (
                user_input[CONF_EXCLUDE_DEVICES].split(",")
                if CONF_EXCLUDE_DEVICES in user_input
                and user_input[CONF_EXCLUDE_DEVICES] != ""
                else []
            )
        else:
            self.config[CONF_EXCLUDE_DEVICES] = user_input[CONF_EXCLUDE_DEVICES]
        if self.login is None:
            try:
                self.login = self.hass.data[DATA_ALEXAMEDIA]["accounts"][
                    self.config[CONF_EMAIL]
                ].get("login_obj")
            except KeyError:
                self.login = None
        try:
            if not self.login:
                _LOGGER.debug("Creating new login")
                self.login = AlexaLogin(
                    self.config[CONF_URL],
                    self.config[CONF_EMAIL],
                    self.config[CONF_PASSWORD],
                    self.hass.config.path,
                    self.config[CONF_DEBUG],
                )
                await self.login.login(data=self.config)
            else:
                _LOGGER.debug("Using existing login")
                await self.login.login(data=self.config)
            return await self._test_login()
        except AlexapyConnectionError:
            return self.async_show_form(
                step_id="user", errors={"base": "connection_error"}
            )
        except BaseException as ex:
            _LOGGER.warning("Unknown error: %s", ex)
            if self.config[CONF_DEBUG]:
                raise
            return self.async_show_form(
                step_id="user", errors={"base": "unknown_error"}
            )

    async def async_step_captcha(self, user_input=None):
        """Handle the input processing of the config flow."""
        return await self.async_step_process("captcha", user_input)

    async def async_step_twofactor(self, user_input=None):
        """Handle the input processing of the config flow."""
        return await self.async_step_process("two_factor", user_input)

    async def async_step_claimspicker(self, user_input=None):
        """Handle the input processing of the config flow."""
        return await self.async_step_process("claimspicker", user_input)

    async def async_step_authselect(self, user_input=None):
        """Handle the input processing of the config flow."""
        return await self.async_step_process("authselect", user_input)

    async def async_step_verificationcode(self, user_input=None):
        """Handle the input processing of the config flow."""
        return await self.async_step_process("verificationcode", user_input)

    async def async_step_action_required(self, user_input=None):
        """Handle the input processing of the config flow."""
        return await self.async_step_process("action_required", user_input)

    async def async_step_process(self, step_id, user_input=None):
        """Handle the input processing of the config flow."""
        if user_input:
            if CONF_PASSWORD in user_input:
                self.config[CONF_PASSWORD] = user_input[CONF_PASSWORD]
            try:
                await self.login.login(data=user_input)
            except AlexapyConnectionError:
                return self.async_show_form(
                    step_id=step_id, errors={"base": "connection_error"}
                )
            except BaseException as ex:
                _LOGGER.warning("Unknown error: %s", ex)
                if self.config[CONF_DEBUG]:
                    raise
                return self.async_show_form(
                    step_id=step_id, errors={"base": "unknown_error"}
                )
        return await self._test_login()

    async def async_step_reauth(self, user_input=None):
        """Handle reauth processing for the config flow."""
        self.config = user_input
        self.login = self.hass.data[DATA_ALEXAMEDIA]["accounts"][
            user_input[CONF_EMAIL]
        ].get("login_obj")
        try:
            _LOGGER.debug(
                "Attempting relogin for %s to %s",
                hide_email(self.config[CONF_EMAIL]),
                self.config[CONF_URL],
            )
            await self.login.login(data=self.config)
            return await self._test_login()
        except AlexapyConnectionError:
            return self.async_show_form(
                step_id="reauth", errors={"base": "connection_error"}
            )

    async def _test_login(self):
        login = self.login
        email = login.email
        _LOGGER.debug("Testing login status: %s", login.status)
        if login.status and login.status.get("login_successful"):
            existing_entry = await self.async_set_unique_id(f"{email} - {login.url}")
            if existing_entry:
                self.hass.config_entries.async_update_entry(
                    existing_entry, data=self.config
                )
                _LOGGER.debug("Reauth successful for %s", hide_email(email))
                self.hass.bus.async_fire(
                    "alexa_media_player_relogin_success",
                    event_data={"email": hide_email(email), "url": login.url},
                )
                self.hass.components.persistent_notification.async_dismiss(
                    "alexa_media_player_relogin_required"
                )
                self.hass.data[DATA_ALEXAMEDIA]["accounts"][self.config[CONF_EMAIL]][
                    "login_obj"
                ] = self.login
                return self.async_abort(reason="reauth_successful")
            _LOGGER.debug(
                "Setting up Alexa devices with %s", dict(obfuscate(self.config))
            )
            self._abort_if_unique_id_configured(self.config)
            return self.async_create_entry(
                title=f"{login.email} - {login.url}", data=self.config
            )
        if login.status and login.status.get("captcha_required"):
            new_schema = self._update_ord_dict(
                self.captcha_schema,
                {vol.Required(CONF_PASSWORD, default=self.config[CONF_PASSWORD]): str},
            )
            _LOGGER.debug("Creating config_flow to request captcha")
            return self.async_show_form(
                step_id="captcha",
                data_schema=vol.Schema(new_schema),
                errors={},
                description_placeholders={
                    "email": login.email,
                    "url": login.url,
                    "captcha_image": "[![captcha]({0})]({0})".format(
                        login.status["captcha_image_url"]
                    ),
                    "message": f"\n> {login.status.get('error_message','')}",
                },
            )
        if login.status and login.status.get("securitycode_required"):
            _LOGGER.debug("Creating config_flow to request 2FA")
            return self.async_show_form(
                step_id="twofactor",
                data_schema=vol.Schema(self.twofactor_schema),
                errors={},
                description_placeholders={
                    "email": login.email,
                    "url": login.url,
                    "message": f"\n> {login.status.get('error_message','')}",
                },
            )
        if login.status and login.status.get("claimspicker_required"):
            error_message = f"\n> {login.status.get('error_message', '')}"
            _LOGGER.debug("Creating config_flow to select verification method")
            claimspicker_message = login.status["claimspicker_message"]
            return self.async_show_form(
                step_id="claimspicker",
                data_schema=vol.Schema(self.claimspicker_schema),
                errors={},
                description_placeholders={
                    "email": login.email,
                    "url": login.url,
                    "message": "\n> {0}\n> {1}".format(
                        claimspicker_message, error_message
                    ),
                },
            )
        if login.status and login.status.get("authselect_required"):
            _LOGGER.debug("Creating config_flow to select OTA method")
            error_message = login.status.get("error_message", "")
            authselect_message = login.status["authselect_message"]
            return self.async_show_form(
                step_id="authselect",
                data_schema=vol.Schema(self.authselect_schema),
                description_placeholders={
                    "email": login.email,
                    "url": login.url,
                    "message": "\n> {0}\n> {1}".format(
                        authselect_message, error_message
                    ),
                },
            )
        if login.status and login.status.get("verificationcode_required"):
            _LOGGER.debug("Creating config_flow to enter verification code")
            return self.async_show_form(
                step_id="verificationcode",
                data_schema=vol.Schema(self.verificationcode_schema),
            )
        if login.status and login.status.get("force_get"):
            _LOGGER.debug("Creating config_flow to wait for user action")
            return self.async_show_form(
                step_id="action_required",
                data_schema=vol.Schema(OrderedDict()),
                description_placeholders={
                    "email": login.email,
                    "url": login.url,
                    "message": f"```text\n{login.status.get('message','')}\n```",
                },
            )
        if login.status and login.status.get("login_failed"):
            _LOGGER.debug("Login failed: %s", login.status.get("login_failed"))
            await login.close()
            return self.async_abort(reason=login.status.get("login_failed"),)
        new_schema = self._update_ord_dict(
            self.data_schema,
            {
                vol.Required(CONF_EMAIL, default=self.config[CONF_EMAIL]): str,
                vol.Required(CONF_PASSWORD, default=self.config[CONF_PASSWORD]): str,
                vol.Optional("securitycode"): str,
                vol.Required(CONF_URL, default=self.config[CONF_URL]): str,
                vol.Optional(CONF_DEBUG, default=self.config[CONF_DEBUG]): bool,
                vol.Optional(
                    CONF_INCLUDE_DEVICES,
                    default=(
                        self.config[CONF_INCLUDE_DEVICES]
                        if isinstance(self.config[CONF_INCLUDE_DEVICES], str)
                        else ",".join(map(str, self.config[CONF_INCLUDE_DEVICES]))
                    ),
                ): str,
                vol.Optional(
                    CONF_EXCLUDE_DEVICES,
                    default=(
                        self.config[CONF_EXCLUDE_DEVICES]
                        if isinstance(self.config[CONF_EXCLUDE_DEVICES], str)
                        else ",".join(map(str, self.config[CONF_EXCLUDE_DEVICES]))
                    ),
                ): str,
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=self.config[CONF_SCAN_INTERVAL]
                ): int,
            },
        )
        if login.status and login.status.get("error_message"):
            _LOGGER.debug("Login error detected: %s", login.status.get("error_message"))
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(new_schema),
                description_placeholders={
                    "message": f"\n> {login.status.get('error_message','')}"
                },
            )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(new_schema),
            description_placeholders={
                "message": f"\n> {login.status.get('error_message','')}"
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle a option flow for Alexa Media."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Handle options flow."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_QUEUE_DELAY,
                    default=self.config_entry.options.get(
                        CONF_QUEUE_DELAY, DEFAULT_QUEUE_DELAY
                    ),
                ): vol.All(vol.Coerce(float), vol.Clamp(min=0))
            }
        )
        return self.async_show_form(step_id="init", data_schema=data_schema)
