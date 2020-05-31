#!/usr/bin/env python
# -*- coding: utf-8 -*-
#  SPDX-License-Identifier: Apache-2.0
"""
Helper functions for Alexa Media Player.

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""

import logging
from typing import Any, Callable, List, Text

from alexapy import AlexapyLoginError, hide_email
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_component import EntityComponent

from . import DATA_ALEXAMEDIA

_LOGGER = logging.getLogger(__name__)


async def add_devices(
    account: Text,
    devices: List[EntityComponent],
    add_devices_callback: Callable,
    include_filter: List[Text] = None,
    exclude_filter: List[Text] = None,
) -> bool:
    """Add devices using add_devices_callback."""
    include_filter = [] or include_filter
    exclude_filter = [] or exclude_filter
    new_devices = []
    for device in devices:
        if (
            include_filter
            and device.name not in include_filter
            or exclude_filter
            and device.name in exclude_filter
        ):
            _LOGGER.debug("%s: Excluding device: %s", account, device)
            continue
        new_devices.append(device)
    devices = new_devices
    if devices:
        _LOGGER.debug("%s: Adding %s", account, devices)
        try:
            add_devices_callback(devices, False)
            return True
        except HomeAssistantError as exception_:
            message = exception_.message  # type: str
            if message.startswith("Entity id already exists"):
                _LOGGER.debug("%s: Device already added: %s", account, message)
            else:
                _LOGGER.debug(
                    "%s: Unable to add devices: %s : %s", account, devices, message
                )
        except BaseException as ex:
            template = "An exception of type {0} occurred." " Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            _LOGGER.debug("%s: Unable to add devices: %s", account, message)
    else:
        return True
    return False


def retry_async(
    limit: int = 5, delay: float = 1, catch_exceptions: bool = True
) -> Callable:
    """Wrap function with retry logic.

    The function will retry until true or the limit is reached. It will delay
    for the period of time specified exponentialy increasing the delay.

    Parameters
    ----------
    limit : int
        The max number of retries.
    delay : float
        The delay in seconds between retries.
    catch_exceptions : bool
        Whether exceptions should be caught and treated as failures or thrown.
    Returns
    -------
    def
        Wrapped function.

    """

    def wrap(func) -> Callable:
        import functools
        import asyncio

        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            _LOGGER.debug(
                "%s.%s: Trying with limit %s delay %s catch_exceptions %s",
                func.__module__[func.__module__.find(".") + 1 :],
                func.__name__,
                limit,
                delay,
                catch_exceptions,
            )
            retries: int = 0
            result: bool = False
            next_try: int = 0
            while not result and retries < limit:
                if retries != 0:
                    next_try = delay * 2 ** retries
                    await asyncio.sleep(next_try)
                retries += 1
                try:
                    result = await func(*args, **kwargs)
                except Exception as ex:  # pylint: disable=broad-except
                    if not catch_exceptions:
                        raise
                    template = "An exception of type {0} occurred." " Arguments:\n{1!r}"
                    message = template.format(type(ex).__name__, ex.args)
                    _LOGGER.debug(
                        "%s.%s: failure caught due to exception: %s",
                        func.__module__[func.__module__.find(".") + 1 :],
                        func.__name__,
                        message,
                    )
                _LOGGER.debug(
                    "%s.%s: Try: %s/%s after waiting %s seconds result: %s",
                    func.__module__[func.__module__.find(".") + 1 :],
                    func.__name__,
                    retries,
                    limit,
                    next_try,
                    result,
                )
            return result

        return wrapper

    return wrap


def _catch_login_errors(func) -> Callable:
    """Detect AlexapyLoginError and attempt relogin."""
    import functools

    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        try:
            result = await func(*args, **kwargs)
        except AlexapyLoginError as ex:  # pylint: disable=broad-except
            template = "An exception of type {0} occurred." " Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            _LOGGER.debug(
                "%s.%s: detected bad login: %s",
                func.__module__[func.__module__.find(".") + 1 :],
                func.__name__,
                message,
            )
            instance = args[0]
            if hasattr(instance, "_login"):
                login = instance._login
                email = login.email
                hass = instance.hass if instance.hass else None
                if hass and (
                    "configurator"
                    not in (hass.data[DATA_ALEXAMEDIA]["accounts"][email])
                    or not (
                        hass.data[DATA_ALEXAMEDIA]["accounts"][email]["configurator"]
                    )
                ):
                    config_entry = hass.data[DATA_ALEXAMEDIA]["accounts"][email][
                        "config_entry"
                    ]
                    setup_alexa = hass.data[DATA_ALEXAMEDIA]["accounts"][email][
                        "setup_alexa"
                    ]
                    test_login_status = hass.data[DATA_ALEXAMEDIA]["accounts"][email][
                        "test_login_status"
                    ]
                    _LOGGER.debug(
                        "%s: Alexa API disconnected; attempting to relogin",
                        hide_email(email),
                    )
                    if login.status:
                        await login.reset()
                        await login.login()
                        await test_login_status(hass, config_entry, login, setup_alexa)
            return None
        return result

    return wrapper


def _existing_serials(hass, login_obj) -> List:
    email: Text = login_obj.email
    existing_serials = (
        list(
            hass.data[DATA_ALEXAMEDIA]["accounts"][email]["entities"][
                "media_player"
            ].keys()
        )
        if "entities" in (hass.data[DATA_ALEXAMEDIA]["accounts"][email])
        else []
    )
    for serial in existing_serials:
        device = hass.data[DATA_ALEXAMEDIA]["accounts"][email]["devices"][
            "media_player"
        ][serial]
        if "appDeviceList" in device and device["appDeviceList"]:
            apps = list(
                map(
                    lambda x: x["serialNumber"] if "serialNumber" in x else None,
                    device["appDeviceList"],
                )
            )
            # _LOGGER.debug("Combining %s with %s",
            #               existing_serials, apps)
            existing_serials = existing_serials + apps
    return existing_serials
