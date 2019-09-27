#!/usr/bin/env python
# -*- coding: utf-8 -*-
#  SPDX-License-Identifier: Apache-2.0
"""
Alexa Config Flow.

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""
import logging
from collections import OrderedDict
from typing import Text

import voluptuous as vol
from alexapy import AlexapyConnectionError
from homeassistant import config_entries
from homeassistant.const import (CONF_EMAIL, CONF_NAME, CONF_PASSWORD,
                                 CONF_SCAN_INTERVAL, CONF_URL,
                                 EVENT_HOMEASSISTANT_STOP)
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

from .const import (CONF_DEBUG, CONF_EXCLUDE_DEVICES, CONF_INCLUDE_DEVICES,
                    DATA_ALEXAMEDIA, DOMAIN)

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
                    # _LOGGER.debug(
                    #     "Replacing (%s:default(%s), %s) with (%s:default(%s), %s)",
                    #     k,
                    #     k.default() if hasattr(k.default, '__call__') else "",
                    #     v,
                    #     key,
                    #     key.default() if hasattr(key.default, '__call__') else "",
                    #     value,
                    # )
                    result.update([(key, value)])
                    break
            if k not in result:
                # _LOGGER.debug("Keeping (%s, %s)", k, v)
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
                (vol.Required(CONF_URL, default="amazon.com"), str),
                (vol.Optional(CONF_DEBUG, default=False), bool),
                (vol.Optional(CONF_INCLUDE_DEVICES, default=""), str),
                (vol.Optional(CONF_EXCLUDE_DEVICES, default=""), str),
                (vol.Optional(CONF_SCAN_INTERVAL, default=60), int),
            ]
        )
        self.captcha_schema = OrderedDict(
            [(vol.Required(CONF_PASSWORD), str), (vol.Required("captcha"), str)]
        )
        self.twofactor_schema = OrderedDict([(vol.Required("securitycode"), str)])
        self.claimspicker_schema = OrderedDict([(vol.Required("claimsoption"), str)])
        self.authselect_schema = OrderedDict([(vol.Required("authselectoption"), int)])
        self.verificationcode_schema = OrderedDict(
            [(vol.Required("verificationcode"), str)]
        )

    async def _show_form(
        self, step="user", placeholders=None, errors=None, data_schema=None
    ) -> None:
        """Show the form to the user."""
        _LOGGER.debug("show_form %s %s %s %s", step, placeholders, errors, data_schema)
        data_schema = data_schema or vol.Schema(self.data_schema)
        if step == "user":
            return self.async_show_form(
                step_id=step,
                data_schema=data_schema,
                errors=errors if errors else {},
                description_placeholders=placeholders if placeholders else {},
            )
        elif step == "captcha":
            return self.async_show_form(
                step_id=step,
                data_schema=data_schema,
                errors={},
                description_placeholders=placeholders if placeholders else {},
            )
        elif step == "twofactor":
            return self.async_show_form(
                step_id=step,
                data_schema=data_schema,
                errors={},
                description_placeholders=placeholders if placeholders else {},
            )
        elif step == "claimspicker":
            return self.async_show_form(
                step_id=step,
                data_schema=data_schema,
                errors=errors if errors else {},
                description_placeholders=placeholders if placeholders else {},
            )
        elif step == "authselect":
            return self.async_show_form(
                step_id=step,
                data_schema=data_schema,
                errors=errors if errors else {},
                description_placeholders=placeholders if placeholders else {},
            )
        elif step == "verificationcode":
            return self.async_show_form(
                step_id=step,
                data_schema=data_schema,
                errors=errors if errors else {},
                description_placeholders=placeholders if placeholders else {},
            )

    async def async_step_import(self, import_config):
        """Import a config entry from configuration.yaml."""
        return await self.async_step_user(import_config)

    async def async_step_user(self, user_input=None):
        """Handle the start of the config flow."""
        from alexapy import AlexaLogin

        if not user_input:
            return await self._show_form(data_schema=vol.Schema(self.data_schema))

        if "{} - {}".format(
            user_input[CONF_EMAIL], user_input[CONF_URL]
        ) in configured_instances(self.hass):
            return await self._show_form(errors={CONF_EMAIL: "identifier_exists"})

        self.config[CONF_EMAIL] = user_input[CONF_EMAIL]
        self.config[CONF_PASSWORD] = user_input[CONF_PASSWORD]
        self.config[CONF_URL] = user_input[CONF_URL]
        self.config[CONF_DEBUG] = user_input[CONF_DEBUG]
        from datetime import timedelta

        self.config[CONF_SCAN_INTERVAL] = (
            user_input[CONF_SCAN_INTERVAL]
            if not isinstance(user_input[CONF_SCAN_INTERVAL], timedelta)
            else user_input[CONF_SCAN_INTERVAL].total_seconds()
        )
        if isinstance(user_input[CONF_INCLUDE_DEVICES], str):
            self.config[CONF_INCLUDE_DEVICES] = (
                user_input[CONF_INCLUDE_DEVICES].split(",")
                if CONF_INCLUDE_DEVICES in user_input and
                user_input[CONF_INCLUDE_DEVICES] != ""
                else []
            )
        else:
            self.config[CONF_INCLUDE_DEVICES] = user_input[CONF_INCLUDE_DEVICES]
        if isinstance(user_input[CONF_EXCLUDE_DEVICES], str):
            self.config[CONF_EXCLUDE_DEVICES] = (
                user_input[CONF_EXCLUDE_DEVICES].split(",")
                if CONF_EXCLUDE_DEVICES in user_input and
                user_input[CONF_EXCLUDE_DEVICES] != ""
                else []
            )
        else:
            self.config[CONF_EXCLUDE_DEVICES] = user_input[CONF_EXCLUDE_DEVICES]
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
                await self.login.login_with_cookie()
                return await self._test_login()
            else:
                _LOGGER.debug("Using existing login")
                await self.login.login(data=user_input)
                return await self._test_login()
        except AlexapyConnectionError:
            return await self._show_form(errors={"base": "connection_error"})
        except BaseException as ex:
            _LOGGER.warning("Unknown error: %s", ex)
            return await self._show_form(errors={"base": "unknown_error"})

    async def async_step_captcha(self, user_input=None):
        """Handle the input processing of the config flow."""
        return await self.async_step_process(user_input)

    async def async_step_twofactor(self, user_input=None):
        """Handle the input processing of the config flow."""
        return await self.async_step_process(user_input)

    async def async_step_claimspicker(self, user_input=None):
        """Handle the input processing of the config flow."""
        return await self.async_step_process(user_input)

    async def async_step_authselect(self, user_input=None):
        """Handle the input processing of the config flow."""
        return await self.async_step_process(user_input)

    async def async_step_verificationcode(self, user_input=None):
        """Handle the input processing of the config flow."""
        return await self.async_step_process(user_input)

    async def async_step_process(self, user_input=None):
        """Handle the input processing of the config flow."""
        if user_input:
            if CONF_PASSWORD in user_input:
                password = user_input[CONF_PASSWORD]
                self.config[CONF_PASSWORD] = password
            try:
                await self.login.login(data=user_input)
            except AlexapyConnectionError:
                return await self._show_form(
                    errors={"base": "connection_error"})
            except BaseException as ex:
                _LOGGER.warning("Unknown error: %s", ex)
                return await self._show_form(errors={"base": "unknown_error"})
        return await self._test_login()

    async def _test_login(self):
        login = self.login
        config = self.config
        _LOGGER.debug("Testing login status: %s", login.status)
        if "login_successful" in login.status and login.status["login_successful"]:
            _LOGGER.debug("Setting up Alexa devices with %s", dict(config))
            await login.close()
            return self.async_create_entry(
                title="{} - {}".format(login.email, login.url), data=config
            )
        if "captcha_required" in login.status and login.status["captcha_required"]:
            new_schema = self._update_ord_dict(
                self.captcha_schema,
                {vol.Required(CONF_PASSWORD, default=config[CONF_PASSWORD]): str},
            )
            _LOGGER.debug("Creating config_flow to request captcha")
            return await self._show_form(
                "captcha",
                data_schema=vol.Schema(new_schema),
                errors={},
                placeholders={
                    "email": login.email,
                    "url": login.url,
                    "captcha_image": "[![captcha]({0})]({0})".format(
                        login.status["captcha_image_url"]
                    ),
                    "message": "\n> {0}".format(
                        login.status["error_message"]
                        if "error_message" in login.status
                        else ""
                    ),
                },
            )
        elif (
            "securitycode_required" in login.status
            and login.status["securitycode_required"]
        ):
            _LOGGER.debug("Creating config_flow to request 2FA")
            message = "> {0}".format(
                login.status["error_message"] if "error_message" in login.status else ""
            )
            return await self._show_form(
                "twofactor",
                data_schema=vol.Schema(self.twofactor_schema),
                errors={},
                placeholders={
                    "email": login.email,
                    "url": login.url,
                    "message": message,
                },
            )
        elif (
            "claimspicker_required" in login.status
            and login.status["claimspicker_required"]
        ):
            message = "> {0}".format(
                login.status["error_message"] if "error_message" in login.status else ""
            )
            _LOGGER.debug("Creating config_flow to select verification method")
            return await self._show_form(
                "claimspicker",
                data_schema=vol.Schema(self.claimspicker_schema),
                errors={},
                placeholders={
                    "email": login.email,
                    "url": login.url,
                    "message": message,
                },
            )
        elif (
            "authselect_required" in login.status
            and login.status["authselect_required"]
        ):
            _LOGGER.debug("Creating config_flow to select OTA method")
            error_message = (
                login.status["error_message"] if "error_message" in login.status else ""
            )
            authselect_message = login.status["authselect_message"]
            return await self._show_form(
                "authselect",
                data_schema=vol.Schema(self.authselect_schema),
                placeholders={
                    "email": login.email,
                    "url": login.url,
                    "message": "> {0}\n> {1}".format(authselect_message, error_message),
                },
            )
        elif (
            "verificationcode_required" in login.status
            and login.status["verificationcode_required"]
        ):
            _LOGGER.debug("Creating config_flow to enter verification code")
            return await self._show_form(
                "verificationcode", data_schema=vol.Schema(self.verificationcode_schema)
            )
        elif "login_failed" in login.status and login.status["login_failed"]:
            _LOGGER.debug("Login failed")
            return self.async_abort(reason="Login failed")
        new_schema = self._update_ord_dict(
            self.data_schema,
            {
                vol.Required(CONF_EMAIL, default=config[CONF_EMAIL]): str,
                vol.Required(CONF_PASSWORD, default=config[CONF_PASSWORD]): str,
                vol.Required(CONF_URL, default=config[CONF_URL]): str,
                vol.Optional(CONF_DEBUG, default=config[CONF_DEBUG]): bool,
                vol.Optional(
                    CONF_INCLUDE_DEVICES,
                    default=(
                        config[CONF_INCLUDE_DEVICES]
                        if isinstance(config[CONF_INCLUDE_DEVICES], str)
                        else ",".join(map(str, config[CONF_INCLUDE_DEVICES]))
                    ),
                ): str,
                vol.Optional(
                    CONF_EXCLUDE_DEVICES,
                    default=(
                        config[CONF_EXCLUDE_DEVICES]
                        if isinstance(config[CONF_EXCLUDE_DEVICES], str)
                        else ",".join(map(str, config[CONF_EXCLUDE_DEVICES]))
                    ),
                ): str,
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=config[CONF_SCAN_INTERVAL]
                ): int,
            },
        )
        return await self._show_form(data_schema=vol.Schema(new_schema))
