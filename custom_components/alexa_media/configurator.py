#!/usr/bin/env python
# -*- coding: utf-8 -*-
#  SPDX-License-Identifier: Apache-2.0
"""
Support to interface with Alexa Devices.

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""
import logging
from typing import Text

from . import hide_email
from .const import DATA_ALEXAMEDIA

_LOGGER = logging.getLogger(__name__)


async def test_login_status(hass, config_entry, login, alexa_setup_callback) -> bool:
    """Test the login status and spawn requests for info."""

    async def request_configuration(hass, config_entry, login):
        """Request configuration steps from the user using the configurator."""

        async def configuration_callback(callback_data):
            """Handle the submitted configuration."""
            await hass.async_add_job(
                setup_platform_callback, hass, config_entry, login, callback_data
            )

        configurator = hass.components.configurator
        status = login.status
        email = login.email
        # links = ""
        footer = ""
        if "error_message" in status and status["error_message"]:
            footer = (
                "\n<b>NOTE: Actual Amazon error message in red below. "
                "Remember password will be provided automatically"
                " and Amazon error message normally appears first!</b>"
            )
        # if login.links:
        #     links = '\n\nGo to link with link# (e.g. link0)\n' + login.links
        # Get Captcha
        if (
            status
            and "captcha_image_url" in status
            and status["captcha_image_url"] is not None
        ):
            config_id = configurator.async_request_config(
                "Alexa Media Player - Captcha - {}".format(email),
                configuration_callback,
                description=(
                    "Please enter the text for the captcha."
                    " Please hit confirm to reload image."
                    # + links
                    + footer
                ),
                description_image=status["captcha_image_url"],
                submit_caption="Confirm",
                fields=[{"id": "captcha", "name": "Captcha"}],
            )
        elif (
            status
            and "securitycode_required" in status
            and status["securitycode_required"]
        ):  # Get 2FA code
            config_id = configurator.async_request_config(
                "Alexa Media Player - 2FA - {}".format(email),
                configuration_callback,
                description=(
                    "Please enter your Two-Factor Security code."
                    # + links
                    + footer
                ),
                submit_caption="Confirm",
                fields=[{"id": "securitycode", "name": "Security Code"}],
            )
        elif (
            status
            and "claimspicker_required" in status
            and status["claimspicker_required"]
        ):  # Get picker method
            options = status["claimspicker_message"]
            if options:
                config_id = configurator.async_request_config(
                    "Alexa Media Player - Verification Method - {}".format(email),
                    configuration_callback,
                    description=(
                        "Please select the verification method by number. "
                        "(e.g., `0` or `1`).\n{}".format(options)
                        # + links
                        + footer
                    ),
                    submit_caption="Confirm",
                    fields=[{"id": "claimsoption", "name": "Option"}],
                )
            else:
                await configuration_callback({})
        elif (
            status and "authselect_required" in status and status["authselect_required"]
        ):  # Get picker method
            options = status["authselect_message"]
            if options:
                config_id = configurator.async_request_config(
                    "Alexa Media Player - OTP Method - {}".format(email),
                    configuration_callback,
                    description=(
                        "Please select the OTP method by number. "
                        "(e.g., `0`, `1`).<br />{}".format(options)
                        # + links
                        + footer
                    ),
                    submit_caption="Confirm",
                    fields=[{"id": "authselectoption", "name": "Option"}],
                )
            else:
                await configuration_callback({})
        elif (
            status
            and "verificationcode_required" in status
            and status["verificationcode_required"]
        ):  # Get picker method
            config_id = configurator.async_request_config(
                "Alexa Media Player - Verification Code - {}".format(email),
                configuration_callback,
                description=(
                    "Please enter received verification code."
                    # + links
                    + footer
                ),
                submit_caption="Confirm",
                fields=[{"id": "verificationcode", "name": "Verification Code"}],
            )
        else:  # Check login
            config_id = configurator.async_request_config(
                "Alexa Media Player - Begin - {}".format(email),
                configuration_callback,
                description=("Please hit confirm to begin login attempt."),
                submit_caption="Confirm",
                fields=[],
            )
        hass.data[DATA_ALEXAMEDIA]["accounts"][email]["configurator"].append(config_id)
        if "error_message" in status and status["error_message"]:
            configurator.async_notify_errors(config_id, status["error_message"])
        if len(hass.data[DATA_ALEXAMEDIA]["accounts"][email]["configurator"]) > 1:
            configurator.async_request_done(
                (hass.data[DATA_ALEXAMEDIA]["accounts"][email]["configurator"]).pop(0)
            )

    async def setup_platform_callback(hass, config_entry, login, callback_data):
        """Handle response from configurator.

        Args:
        callback_data (json): Returned data from configurator passed through
                            request_configuration and configuration_callback

        """
        _LOGGER.debug(
            (
                "Configurator closed for Status: %s\n"
                " got captcha: %s securitycode: %s"
                " Claimsoption: %s AuthSelectOption: %s "
                " VerificationCode: %s"
            ),
            login.status,
            callback_data.get("captcha"),
            callback_data.get("securitycode"),
            callback_data.get("claimsoption"),
            callback_data.get("authselectoption"),
            callback_data.get("verificationcode"),
        )
        await login.login(data=callback_data)
        await test_login_status(hass, config_entry, login, alexa_setup_callback)

    _LOGGER.debug("Testing login status: %s", login.status)
    if "login_successful" in login.status and login.status["login_successful"]:
        _LOGGER.debug("Setting up Alexa devices for %s", hide_email(login.email))
        await clear_configurator(hass, login.email)
        await hass.async_add_job(alexa_setup_callback, hass, config_entry, login)
        return True
    if "captcha_required" in login.status and login.status["captcha_required"]:
        _LOGGER.debug("Creating configurator to request captcha")
    elif (
        "securitycode_required" in login.status
        and login.status["securitycode_required"]
    ):
        _LOGGER.debug("Creating configurator to request 2FA")
    elif (
        "claimspicker_required" in login.status
        and login.status["claimspicker_required"]
    ):
        _LOGGER.debug("Creating configurator to select verification option")
    elif "authselect_required" in login.status and login.status["authselect_required"]:
        _LOGGER.debug("Creating configurator to select OTA option")
    elif (
        "verificationcode_required" in login.status
        and login.status["verificationcode_required"]
    ):
        _LOGGER.debug("Creating configurator to enter verification code")
    elif "login_failed" in login.status and login.status["login_failed"]:
        _LOGGER.debug("Creating configurator to start new login attempt")
    await hass.async_add_job(request_configuration, hass, config_entry, login)


async def clear_configurator(hass, email: Text) -> None:
    """Clear open configurators for email."""
    if email not in hass.data[DATA_ALEXAMEDIA]["accounts"]:
        return
    if "configurator" in hass.data[DATA_ALEXAMEDIA]["accounts"][email]:
        for config_id in hass.data[DATA_ALEXAMEDIA]["accounts"][email]["configurator"]:
            configurator = hass.components.configurator
            configurator.async_request_done(config_id)
        hass.data[DATA_ALEXAMEDIA]["accounts"][email]["configurator"] = []
