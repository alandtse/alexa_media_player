#!/usr/bin/env python
# -*- coding: utf-8 -*-
#  SPDX-License-Identifier: Apache-2.0
"""
Support to interface with Alexa Devices.

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""
import asyncio
from datetime import datetime, timedelta
from json import JSONDecodeError
import logging
import time
from typing import Optional, Text

from alexapy import AlexapyLoginError, WebsocketEchoClient, hide_email, hide_serial
import async_timeout
from homeassistant import util
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import (
    CONF_EMAIL,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_URL,
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv, entity
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt
import voluptuous as vol

from .config_flow import configured_instances
from .configurator import clear_configurator, test_login_status
from .const import (
    ALEXA_COMPONENTS,
    ATTR_EMAIL,
    ATTR_NUM_ENTRIES,
    CONF_ACCOUNTS,
    CONF_DEBUG,
    CONF_EXCLUDE_DEVICES,
    CONF_INCLUDE_DEVICES,
    DATA_ALEXAMEDIA,
    DOMAIN,
    ISSUE_URL,
    MIN_TIME_BETWEEN_FORCED_SCANS,
    MIN_TIME_BETWEEN_SCANS,
    SCAN_INTERVAL,
    SERVICE_CLEAR_HISTORY,
    SERVICE_UPDATE_LAST_CALLED,
    STARTUP,
)
from .helpers import _existing_serials

_LOGGER = logging.getLogger(__name__)


ACCOUNT_CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_URL): cv.string,
        vol.Optional(CONF_DEBUG, default=False): cv.boolean,
        vol.Optional(CONF_INCLUDE_DEVICES, default=[]): vol.All(
            cv.ensure_list, [cv.string]
        ),
        vol.Optional(CONF_EXCLUDE_DEVICES, default=[]): vol.All(
            cv.ensure_list, [cv.string]
        ),
        vol.Optional(CONF_SCAN_INTERVAL, default=SCAN_INTERVAL): cv.time_period,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_ACCOUNTS): vol.All(
                    cv.ensure_list, [ACCOUNT_CONFIG_SCHEMA]
                )
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

CLEAR_HISTORY_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_EMAIL, default=[]): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(ATTR_NUM_ENTRIES, default=50): vol.All(
            int, vol.Range(min=1, max=50)
        ),
    }
)

LAST_CALL_UPDATE_SCHEMA = vol.Schema(
    {vol.Optional(ATTR_EMAIL, default=[]): vol.All(cv.ensure_list, [cv.string])}
)


async def async_setup(hass, config, discovery_info=None):
    # pylint: disable=unused-argument
    """Set up the Alexa domain."""
    if DOMAIN not in config:
        _LOGGER.debug(
            "Nothing to import from configuration.yaml, loading from Integrations",
        )
        return True

    domainconfig = config.get(DOMAIN)
    for account in domainconfig[CONF_ACCOUNTS]:
        entry_title = "{} - {}".format(account[CONF_EMAIL], account[CONF_URL])
        _LOGGER.debug(
            "Importing config information for %s - %s from configuration.yaml",
            hide_email(account[CONF_EMAIL]),
            account[CONF_URL],
        )
        if entry_title in configured_instances(hass):
            for entry in hass.config_entries.async_entries(DOMAIN):
                if entry_title == entry.title:
                    hass.config_entries.async_update_entry(
                        entry,
                        data={
                            CONF_EMAIL: account[CONF_EMAIL],
                            CONF_PASSWORD: account[CONF_PASSWORD],
                            CONF_URL: account[CONF_URL],
                            CONF_DEBUG: account[CONF_DEBUG],
                            CONF_INCLUDE_DEVICES: account[CONF_INCLUDE_DEVICES],
                            CONF_EXCLUDE_DEVICES: account[CONF_EXCLUDE_DEVICES],
                            CONF_SCAN_INTERVAL: account[
                                CONF_SCAN_INTERVAL
                            ].total_seconds(),
                        },
                    )
                    break
        else:
            hass.async_create_task(
                hass.config_entries.flow.async_init(
                    DOMAIN,
                    context={"source": SOURCE_IMPORT},
                    data={
                        CONF_EMAIL: account[CONF_EMAIL],
                        CONF_PASSWORD: account[CONF_PASSWORD],
                        CONF_URL: account[CONF_URL],
                        CONF_DEBUG: account[CONF_DEBUG],
                        CONF_INCLUDE_DEVICES: account[CONF_INCLUDE_DEVICES],
                        CONF_EXCLUDE_DEVICES: account[CONF_EXCLUDE_DEVICES],
                        CONF_SCAN_INTERVAL: account[CONF_SCAN_INTERVAL].total_seconds(),
                    },
                )
            )
    return True


# @retry_async(limit=5, delay=5, catch_exceptions=True)
async def async_setup_entry(hass, config_entry):
    """Set up Alexa Media Player as config entry."""

    async def close_alexa_media(event=None) -> None:
        """Clean up Alexa connections."""
        _LOGGER.debug("Received shutdown request: %s", event)
        for email, _ in hass.data[DATA_ALEXAMEDIA]["accounts"].items():
            await close_connections(hass, email)

    hass.data.setdefault(DATA_ALEXAMEDIA, {"accounts": {}})
    from alexapy import AlexaLogin, __version__ as alexapy_version

    _LOGGER.info(STARTUP)
    _LOGGER.info("Loaded alexapy==%s", alexapy_version)
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, close_alexa_media)
    account = config_entry.data
    email = account.get(CONF_EMAIL)
    password = account.get(CONF_PASSWORD)
    url = account.get(CONF_URL)
    hass.data[DATA_ALEXAMEDIA]["accounts"].setdefault(
        email,
        {
            "coordinator": None,
            "config_entry": config_entry,
            "setup_alexa": setup_alexa,
            "test_login_status": test_login_status,
            "devices": {"media_player": {}, "switch": {}},
            "entities": {"media_player": {}, "switch": {}},
            "excluded": {},
            "new_devices": True,
            "websocket_lastattempt": 0,
            "websocketerror": 0,
            "websocket_commands": {},
            "websocket_activity": {"serials": {}, "refreshed": {}},
            "websocket": None,
            "auth_info": None,
            "configurator": [],
        },
    )
    login = hass.data[DATA_ALEXAMEDIA]["accounts"][email].get(
        "login_obj",
        AlexaLogin(url, email, password, hass.config.path, account.get(CONF_DEBUG)),
    )
    await login.login_with_cookie()
    if await test_login_status(hass, config_entry, login, setup_alexa):
        return True
    return False


async def setup_alexa(hass, config_entry, login_obj):
    """Set up a alexa api based on host parameter."""

    async def async_update_data():
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.

        This will ping Alexa API to identify all devices, bluetooth, and the last
        called device.

        This will add new devices and services when discovered. By default this
        runs every SCAN_INTERVAL seconds unless another method calls it. if
        websockets is connected, it will increase the delay 10-fold between updates.
        While throttled at MIN_TIME_BETWEEN_SCANS, care should be taken to
        reduce the number of runs to avoid flooding. Slow changing states
        should be checked here instead of in spawned components like
        media_player since this object is one per account.
        Each AlexaAPI call generally results in two webpage requests.
        """
        from alexapy import AlexaAPI

        email: Text = login_obj.email
        if email not in hass.data[DATA_ALEXAMEDIA]["accounts"]:
            return
        existing_serials = _existing_serials(hass, login_obj)
        existing_entities = hass.data[DATA_ALEXAMEDIA]["accounts"][email]["entities"][
            "media_player"
        ].values()
        auth_info = hass.data[DATA_ALEXAMEDIA]["accounts"][email].get("auth_info")
        new_devices = hass.data[DATA_ALEXAMEDIA]["accounts"][email]["new_devices"]
        devices = {}
        bluetooth = {}
        preferences = {}
        dnd = {}
        raw_notifications = {}
        tasks = [
            AlexaAPI.get_devices(login_obj),
            AlexaAPI.get_bluetooth(login_obj),
            AlexaAPI.get_device_preferences(login_obj),
            AlexaAPI.get_dnd_state(login_obj),
            AlexaAPI.get_notifications(login_obj),
        ]
        if new_devices:
            tasks.append(AlexaAPI.get_authentication(login_obj))

        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with async_timeout.timeout(10):
                if new_devices:
                    (
                        devices,
                        bluetooth,
                        preferences,
                        dnd,
                        raw_notifications,
                        auth_info,
                    ) = await asyncio.gather(*tasks)
                else:
                    (
                        devices,
                        bluetooth,
                        preferences,
                        dnd,
                        raw_notifications,
                    ) = await asyncio.gather(*tasks)
                _LOGGER.debug(
                    "%s: Found %s devices, %s bluetooth",
                    hide_email(email),
                    len(devices) if devices is not None else "",
                    len(bluetooth.get("bluetoothStates", []))
                    if bluetooth is not None
                    else "",
                )
                if (devices is None or bluetooth is None) and not (
                    hass.data[DATA_ALEXAMEDIA]["accounts"][email]["configurator"]
                ):
                    raise AlexapyLoginError()
        except (AlexapyLoginError, RuntimeError, JSONDecodeError):
            _LOGGER.debug(
                "%s: Alexa API disconnected; attempting to relogin", hide_email(email)
            )
            await login_obj.login_with_cookie()
            await test_login_status(hass, config_entry, login_obj, setup_alexa)
            return
        except BaseException as err:
            raise UpdateFailed(f"Error communicating with API: {err}")

        await process_notifications(login_obj, raw_notifications)
        # Process last_called data to fire events
        await update_last_called(login_obj)

        new_alexa_clients = []  # list of newly discovered device names
        exclude_filter = []
        include_filter = []

        for device in devices:
            serial = device["serialNumber"]
            dev_name = device["accountName"]
            if include and dev_name not in include:
                include_filter.append(dev_name)
                if "appDeviceList" in device:
                    for app in device["appDeviceList"]:
                        (
                            hass.data[DATA_ALEXAMEDIA]["accounts"][email]["excluded"][
                                app["serialNumber"]
                            ]
                        ) = device
                hass.data[DATA_ALEXAMEDIA]["accounts"][email]["excluded"][
                    serial
                ] = device
                continue
            elif exclude and dev_name in exclude:
                exclude_filter.append(dev_name)
                if "appDeviceList" in device:
                    for app in device["appDeviceList"]:
                        (
                            hass.data[DATA_ALEXAMEDIA]["accounts"][email]["excluded"][
                                app["serialNumber"]
                            ]
                        ) = device
                hass.data[DATA_ALEXAMEDIA]["accounts"][email]["excluded"][
                    serial
                ] = device
                continue

            if "bluetoothStates" in bluetooth:
                for b_state in bluetooth["bluetoothStates"]:
                    if serial == b_state["deviceSerialNumber"]:
                        device["bluetooth_state"] = b_state
                        break

            if "devicePreferences" in preferences:
                for dev in preferences["devicePreferences"]:
                    if dev["deviceSerialNumber"] == serial:
                        device["locale"] = dev["locale"]
                        device["timeZoneId"] = dev["timeZoneId"]
                        _LOGGER.debug(
                            "%s: Locale %s timezone %s",
                            dev_name,
                            device["locale"],
                            device["timeZoneId"],
                        )
                        break

            if "doNotDisturbDeviceStatusList" in dnd:
                for dev in dnd["doNotDisturbDeviceStatusList"]:
                    if dev["deviceSerialNumber"] == serial:
                        device["dnd"] = dev["enabled"]
                        _LOGGER.debug("%s: DND %s", dev_name, device["dnd"])
                        hass.data[DATA_ALEXAMEDIA]["accounts"][email]["devices"][
                            "switch"
                        ].setdefault(serial, {"dnd": True})

                        break
            hass.data[DATA_ALEXAMEDIA]["accounts"][email]["auth_info"] = device[
                "auth_info"
            ] = auth_info
            hass.data[DATA_ALEXAMEDIA]["accounts"][email]["devices"]["media_player"][
                serial
            ] = device

            if serial not in existing_serials:
                new_alexa_clients.append(dev_name)
            elif serial in existing_entities:
                await hass.data[DATA_ALEXAMEDIA]["accounts"][email]["entities"][
                    "media_player"
                ].get(serial).refresh(device, no_api=True)
        _LOGGER.debug(
            "%s: Existing: %s New: %s;"
            " Filtered out by not being in include: %s "
            "or in exclude: %s",
            hide_email(email),
            list(existing_entities),
            new_alexa_clients,
            include_filter,
            exclude_filter,
        )

        if new_alexa_clients:
            cleaned_config = config.copy()
            cleaned_config.pop(CONF_PASSWORD, None)
            # CONF_PASSWORD contains sensitive info which is no longer needed
            for component in ALEXA_COMPONENTS:
                _LOGGER.debug("Loading %s", component)
                hass.async_add_job(
                    hass.config_entries.async_forward_entry_setup(
                        config_entry, component
                    )
                )

        hass.data[DATA_ALEXAMEDIA]["accounts"][email]["new_devices"] = False

    async def process_notifications(login_obj, raw_notifications=None):
        """Process raw notifications json."""
        from alexapy import AlexaAPI

        if not raw_notifications:
            raw_notifications = await AlexaAPI.get_notifications(login_obj)
        email: Text = login_obj.email
        notifications = {"process_timestamp": datetime.utcnow()}
        for notification in raw_notifications:
            n_dev_id = notification.get("deviceSerialNumber")
            if n_dev_id is None:
                # skip notifications untied to a device for now
                # https://github.com/custom-components/alexa_media_player/issues/633#issuecomment-610705651
                continue
            n_type = notification.get("type")
            if n_type is None:
                continue
            if n_type == "MusicAlarm":
                n_type = "Alarm"
            n_id = notification["notificationIndex"]
            if n_type == "Alarm":
                n_date = notification.get("originalDate")
                n_time = notification.get("originalTime")
                notification["date_time"] = (
                    f"{n_date} {n_time}" if n_date and n_time else None
                )
            if n_dev_id not in notifications:
                notifications[n_dev_id] = {}
            if n_type not in notifications[n_dev_id]:
                notifications[n_dev_id][n_type] = {}
            notifications[n_dev_id][n_type][n_id] = notification
        hass.data[DATA_ALEXAMEDIA]["accounts"][email]["notifications"] = notifications
        _LOGGER.debug(
            "%s: Updated %s notifications for %s devices at %s",
            hide_email(email),
            len(raw_notifications),
            len(notifications),
            dt.as_local(
                hass.data[DATA_ALEXAMEDIA]["accounts"][email]["notifications"][
                    "process_timestamp"
                ]
            ),
        )

    async def update_last_called(login_obj, last_called=None):
        """Update the last called device for the login_obj.

        This will store the last_called in hass.data and also fire an event
        to notify listeners.
        """
        from alexapy import AlexaAPI

        if not last_called:
            last_called = await AlexaAPI.get_last_device_serial(login_obj)
        _LOGGER.debug(
            "%s: Updated last_called: %s", hide_email(email), hide_serial(last_called)
        )
        stored_data = hass.data[DATA_ALEXAMEDIA]["accounts"][email]
        if (
            "last_called" in stored_data and last_called != stored_data["last_called"]
        ) or ("last_called" not in stored_data and last_called is not None):
            _LOGGER.debug(
                "%s: last_called changed: %s to %s",
                hide_email(email),
                hide_serial(
                    stored_data["last_called"] if "last_called" in stored_data else None
                ),
                hide_serial(last_called),
            )
            async_dispatcher_send(
                hass,
                f"{DOMAIN}_{hide_email(email)}"[0:32],
                {"last_called_change": last_called},
            )
        hass.data[DATA_ALEXAMEDIA]["accounts"][email]["last_called"] = last_called

    async def update_bluetooth_state(login_obj, device_serial):
        """Update the bluetooth state on ws bluetooth event."""
        from alexapy import AlexaAPI

        bluetooth = await AlexaAPI.get_bluetooth(login_obj)
        device = hass.data[DATA_ALEXAMEDIA]["accounts"][email]["devices"][
            "media_player"
        ][device_serial]

        if "bluetoothStates" in bluetooth:
            for b_state in bluetooth["bluetoothStates"]:
                if device_serial == b_state["deviceSerialNumber"]:
                    # _LOGGER.debug("%s: setting value for: %s to %s",
                    #               hide_email(email),
                    #               hide_serial(device_serial),
                    #               hide_serial(b_state))
                    device["bluetooth_state"] = b_state
                    return device["bluetooth_state"]
        _LOGGER.debug(
            "%s: get_bluetooth for: %s failed with %s",
            hide_email(email),
            hide_serial(device_serial),
            hide_serial(bluetooth),
        )
        return None

    async def clear_history(call):
        """Handle clear history service request.

        Arguments
            call.ATTR_EMAIL {List[str: None]} -- Case-sensitive Alexa emails.
                                                 Default is all known emails.
            call.ATTR_NUM_ENTRIES {int: 50} -- Number of entries to delete.

        Returns
            bool -- True if deletion successful

        """
        from alexapy import AlexaAPI

        requested_emails = call.data.get(ATTR_EMAIL)
        items: int = int(call.data.get(ATTR_NUM_ENTRIES))

        _LOGGER.debug(
            "Service clear_history called for: %i items for %s", items, requested_emails
        )
        for email, account_dict in hass.data[DATA_ALEXAMEDIA]["accounts"].items():
            if requested_emails and email not in requested_emails:
                continue
            login_obj = account_dict["login_obj"]
        return await AlexaAPI.clear_history(login_obj, items)

    async def last_call_handler(call):
        """Handle last call service request.

        Args:
        call.ATTR_EMAIL: List of case-sensitive Alexa email addresses. If None
                         all accounts are updated.

        """
        requested_emails = call.data.get(ATTR_EMAIL)
        _LOGGER.debug("Service update_last_called for: %s", requested_emails)
        for email, account_dict in hass.data[DATA_ALEXAMEDIA]["accounts"].items():
            if requested_emails and email not in requested_emails:
                continue
            login_obj = account_dict["login_obj"]
            await update_last_called(login_obj)

    async def ws_connect() -> WebsocketEchoClient:
        """Open WebSocket connection.

        This will only attempt one login before failing.
        """
        websocket: Optional[WebsocketEchoClient] = None
        try:
            websocket = WebsocketEchoClient(
                login_obj,
                ws_handler,
                ws_open_handler,
                ws_close_handler,
                ws_error_handler,
            )
            _LOGGER.debug("%s: Websocket created: %s", hide_email(email), websocket)
            await websocket.async_run()
        except BaseException as exception_:  # pylint: disable=broad-except
            _LOGGER.debug(
                "%s: Websocket creation failed: %s", hide_email(email), exception_
            )
            return
        return websocket

    async def ws_handler(message_obj):
        """Handle websocket messages.

        This allows push notifications from Alexa to update last_called
        and media state.
        """

        command = (
            message_obj.json_payload["command"]
            if isinstance(message_obj.json_payload, dict)
            and "command" in message_obj.json_payload
            else None
        )
        json_payload = (
            message_obj.json_payload["payload"]
            if isinstance(message_obj.json_payload, dict)
            and "payload" in message_obj.json_payload
            else None
        )
        existing_serials = _existing_serials(hass, login_obj)
        seen_commands = hass.data[DATA_ALEXAMEDIA]["accounts"][email][
            "websocket_commands"
        ]
        if command and json_payload:

            _LOGGER.debug(
                "%s: Received websocket command: %s : %s",
                hide_email(email),
                command,
                hide_serial(json_payload),
            )
            serial = None
            if command not in seen_commands:
                seen_commands[command] = time.time()
                _LOGGER.debug("Adding %s to seen_commands: %s", command, seen_commands)
            if (
                "dopplerId" in json_payload
                and "deviceSerialNumber" in json_payload["dopplerId"]
            ):
                serial = json_payload["dopplerId"]["deviceSerialNumber"]
            elif (
                "key" in json_payload
                and "entryId" in json_payload["key"]
                and json_payload["key"]["entryId"].find("#") != -1
            ):
                serial = (json_payload["key"]["entryId"]).split("#")[2]
                json_payload["key"]["serialNumber"] = serial
            else:
                serial = None
            if command == "PUSH_ACTIVITY":
                #  Last_Alexa Updated
                last_called = {
                    "serialNumber": serial,
                    "timestamp": json_payload["timestamp"],
                }
                if serial and serial in existing_serials:
                    await update_last_called(login_obj, last_called)
                async_dispatcher_send(
                    hass,
                    f"{DOMAIN}_{hide_email(email)}"[0:32],
                    {"push_activity": json_payload},
                )
            elif command in (
                "PUSH_AUDIO_PLAYER_STATE",
                "PUSH_MEDIA_CHANGE",
                "PUSH_MEDIA_PROGRESS_CHANGE",
            ):
                # Player update/ Push_media from tune_in
                if serial and serial in existing_serials:
                    _LOGGER.debug(
                        "Updating media_player: %s", hide_serial(json_payload)
                    )
                    async_dispatcher_send(
                        hass,
                        f"{DOMAIN}_{hide_email(email)}"[0:32],
                        {"player_state": json_payload},
                    )
            elif command == "PUSH_VOLUME_CHANGE":
                # Player volume update
                if serial and serial in existing_serials:
                    _LOGGER.debug(
                        "Updating media_player volume: %s", hide_serial(json_payload)
                    )
                    async_dispatcher_send(
                        hass,
                        f"{DOMAIN}_{hide_email(email)}"[0:32],
                        {"player_state": json_payload},
                    )
            elif command in (
                "PUSH_DOPPLER_CONNECTION_CHANGE",
                "PUSH_EQUALIZER_STATE_CHANGE",
            ):
                # Player availability update
                if serial and serial in existing_serials:
                    _LOGGER.debug(
                        "Updating media_player availability %s",
                        hide_serial(json_payload),
                    )
                    async_dispatcher_send(
                        hass,
                        f"{DOMAIN}_{hide_email(email)}"[0:32],
                        {"player_state": json_payload},
                    )
            elif command == "PUSH_BLUETOOTH_STATE_CHANGE":
                # Player bluetooth update
                bt_event = json_payload["bluetoothEvent"]
                bt_success = json_payload["bluetoothEventSuccess"]
                if (
                    serial
                    and serial in existing_serials
                    and bt_success
                    and bt_event
                    and bt_event in ["DEVICE_CONNECTED", "DEVICE_DISCONNECTED"]
                ):
                    _LOGGER.debug(
                        "Updating media_player bluetooth %s", hide_serial(json_payload)
                    )
                    bluetooth_state = await update_bluetooth_state(login_obj, serial)
                    # _LOGGER.debug("bluetooth_state %s",
                    #               hide_serial(bluetooth_state))
                    if bluetooth_state:
                        async_dispatcher_send(
                            hass,
                            f"{DOMAIN}_{hide_email(email)}"[0:32],
                            {"bluetooth_change": bluetooth_state},
                        )
            elif command == "PUSH_MEDIA_QUEUE_CHANGE":
                # Player availability update
                if serial and serial in existing_serials:
                    _LOGGER.debug(
                        "Updating media_player queue %s", hide_serial(json_payload)
                    )
                    async_dispatcher_send(
                        hass,
                        f"{DOMAIN}_{hide_email(email)}"[0:32],
                        {"queue_state": json_payload},
                    )
            elif command == "PUSH_NOTIFICATION_CHANGE":
                # Player update
                await process_notifications(login_obj)
                if serial and serial in existing_serials:
                    _LOGGER.debug(
                        "Updating mediaplayer notifications: %s",
                        hide_serial(json_payload),
                    )
                    async_dispatcher_send(
                        hass,
                        f"{DOMAIN}_{hide_email(email)}"[0:32],
                        {"notification_update": json_payload},
                    )
            elif command in [
                "PUSH_DELETE_DOPPLER_ACTIVITIES",  # delete Alexa history
                "PUSH_LIST_ITEM_CHANGE",  # update shopping list
                "PUSH_CONTENT_FOCUS_CHANGE",  # likely prime related refocus
            ]:
                pass
            else:
                _LOGGER.warning(
                    "Unhandled command: %s with data %s. Please report at %s",
                    command,
                    hide_serial(json_payload),
                    ISSUE_URL,
                )
            if serial in existing_serials:
                hass.data[DATA_ALEXAMEDIA]["accounts"][email]["websocket_activity"][
                    "serials"
                ][serial] = time.time()
            if (
                serial
                and serial not in existing_serials
                and serial
                not in (
                    hass.data[DATA_ALEXAMEDIA]["accounts"][email]["excluded"].keys()
                )
            ):
                _LOGGER.debug("Discovered new media_player %s", serial)
                (hass.data[DATA_ALEXAMEDIA]["accounts"][email]["new_devices"]) = True
                coordinator = hass.data[DATA_ALEXAMEDIA]["accounts"][email].get(
                    "coordinator"
                )
                if coordinator:
                    await coordinator.async_request_refresh()

    async def ws_open_handler():
        """Handle websocket open."""
        import time

        email: Text = login_obj.email
        _LOGGER.debug("%s: Websocket succesfully connected", hide_email(email))
        hass.data[DATA_ALEXAMEDIA]["accounts"][email][
            "websocketerror"
        ] = 0  # set errors to 0
        hass.data[DATA_ALEXAMEDIA]["accounts"][email][
            "websocket_lastattempt"
        ] = time.time()

    async def ws_close_handler():
        """Handle websocket close.

        This should attempt to reconnect up to 5 times
        """
        from asyncio import sleep
        import time

        email: Text = login_obj.email
        errors: int = (hass.data[DATA_ALEXAMEDIA]["accounts"][email]["websocketerror"])
        delay: int = 5 * 2 ** errors
        last_attempt = hass.data[DATA_ALEXAMEDIA]["accounts"][email][
            "websocket_lastattempt"
        ]
        now = time.time()
        if (now - last_attempt) < delay:
            return
        while errors < 5 and not (
            hass.data[DATA_ALEXAMEDIA]["accounts"][email]["websocket"]
        ):
            _LOGGER.debug(
                "%s: Websocket closed; reconnect #%i in %is",
                hide_email(email),
                errors,
                delay,
            )
            hass.data[DATA_ALEXAMEDIA]["accounts"][email][
                "websocket_lastattempt"
            ] = time.time()
            hass.data[DATA_ALEXAMEDIA]["accounts"][email][
                "websocket"
            ] = await ws_connect()
            errors = hass.data[DATA_ALEXAMEDIA]["accounts"][email]["websocketerror"] = (
                hass.data[DATA_ALEXAMEDIA]["accounts"][email]["websocketerror"] + 1
            )
            delay = 5 * 2 ** errors
            await sleep(delay)
            errors = hass.data[DATA_ALEXAMEDIA]["accounts"][email]["websocketerror"]
        _LOGGER.debug(
            "%s: Websocket closed; retries exceeded; polling", hide_email(email)
        )
        hass.data[DATA_ALEXAMEDIA]["accounts"][email]["websocket"] = None
        coordinator = hass.data[DATA_ALEXAMEDIA]["accounts"][email].get("coordinator")
        if coordinator:
            coordinator.update_interval = scan_interval
            await coordinator.async_request_refresh()

    async def ws_error_handler(message):
        """Handle websocket error.

        This currently logs the error.  In the future, this should invalidate
        the websocket and determine if a reconnect should be done. By
        specification, websockets will issue a close after every error.
        """
        email: Text = login_obj.email
        errors = hass.data[DATA_ALEXAMEDIA]["accounts"][email]["websocketerror"]
        _LOGGER.debug(
            "%s: Received websocket error #%i %s: type %s",
            hide_email(email),
            errors,
            message,
            type(message),
        )
        hass.data[DATA_ALEXAMEDIA]["accounts"][email]["websocket"] = None
        if message == "<class 'aiohttp.streams.EofStream'>":
            hass.data[DATA_ALEXAMEDIA]["accounts"][email]["websocketerror"] = 5
            _LOGGER.debug("%s: Immediate abort on EoFstream", hide_email(email))
            return
        hass.data[DATA_ALEXAMEDIA]["accounts"][email]["websocketerror"] = errors + 1

    config = config_entry.data
    email = config.get(CONF_EMAIL)
    include = config.get(CONF_INCLUDE_DEVICES)
    exclude = config.get(CONF_EXCLUDE_DEVICES)
    scan_interval: float = (
        config.get(CONF_SCAN_INTERVAL).total_seconds()
        if isinstance(config.get(CONF_SCAN_INTERVAL), timedelta)
        else config.get(CONF_SCAN_INTERVAL)
    )
    hass.data[DATA_ALEXAMEDIA]["accounts"][email]["login_obj"] = login_obj
    websocket_enabled = hass.data[DATA_ALEXAMEDIA]["accounts"][email][
        "websocket"
    ] = await ws_connect()
    coordinator = hass.data[DATA_ALEXAMEDIA]["accounts"][email].get("coordinator")
    if coordinator is None:
        _LOGGER.debug("Creating coordinator")
        hass.data[DATA_ALEXAMEDIA]["accounts"][email][
            "coordinator"
        ] = coordinator = DataUpdateCoordinator(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="alexa_media",
            update_method=async_update_data,
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(
                seconds=scan_interval * 10 if websocket_enabled else scan_interval
            ),
        )
    # Fetch initial data so we have data when entities subscribe
    _LOGGER.debug("Refreshing coordinator")
    await coordinator.async_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_LAST_CALLED,
        last_call_handler,
        schema=LAST_CALL_UPDATE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_CLEAR_HISTORY, clear_history, schema=CLEAR_HISTORY_SCHEMA
    )
    # Clear configurator. We delay till here to avoid leaving a modal orphan
    await clear_configurator(hass, email)
    return True


async def async_unload_entry(hass, entry) -> bool:
    """Unload a config entry."""
    hass.services.async_remove(DOMAIN, SERVICE_UPDATE_LAST_CALLED)
    hass.services.async_remove(DOMAIN, SERVICE_CLEAR_HISTORY)
    for component in ALEXA_COMPONENTS:
        await hass.config_entries.async_forward_entry_unload(entry, component)
    # notify has to be handled manually as the forward does not work yet
    from .notify import async_unload_entry as notify_async_unload_entry

    await notify_async_unload_entry(hass, entry)
    email = entry.data["email"]
    await close_connections(hass, email)
    await clear_configurator(hass, email)
    hass.data[DATA_ALEXAMEDIA]["accounts"].pop(email)
    _LOGGER.debug("Unloaded entry for %s", hide_email(email))
    return True


async def close_connections(hass, email: Text) -> None:
    """Clear open aiohttp connections for email."""
    if (
        email not in hass.data[DATA_ALEXAMEDIA]["accounts"]
        or "login_obj" not in hass.data[DATA_ALEXAMEDIA]["accounts"][email]
    ):
        return
    account_dict = hass.data[DATA_ALEXAMEDIA]["accounts"][email]
    login_obj = account_dict["login_obj"]
    await login_obj.close()
    _LOGGER.debug(
        "%s: Connection closed: %s", hide_email(email), login_obj._session.closed
    )
    await clear_configurator(hass, email)
