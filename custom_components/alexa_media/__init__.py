"""
Support to interface with Alexa Devices.

SPDX-License-Identifier: Apache-2.0

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""

import asyncio
from datetime import datetime, timedelta
from json import JSONDecodeError, loads
import logging
import os
import time
from typing import Optional

from alexapy import (
    AlexaAPI,
    AlexaLogin,
    AlexapyConnectionError,
    AlexapyLoginError,
    HTTP2EchoClient,
    __version__ as alexapy_version,
    hide_email,
    hide_serial,
    obfuscate,
)
from alexapy.helpers import delete_cookie as alexapy_delete_cookie
import async_timeout
from homeassistant import util
from homeassistant.components.persistent_notification import (
    async_create as async_create_persistent_notification,
    async_dismiss as async_dismiss_persistent_notification,
)
from homeassistant.config_entries import SOURCE_IMPORT, SOURCE_REAUTH
from homeassistant.const import (
    CONF_EMAIL,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_URL,
    EVENT_HOMEASSISTANT_STARTED,
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import UnknownFlow
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.issue_registry import IssueSeverity, async_create_issue
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt, slugify
import voluptuous as vol

from .alexa_entity import AlexaEntityData, get_entity_data, parse_alexa_entities
from .config_flow import in_progress_instances
from .const import (
    ALEXA_COMPONENTS,
    CONF_ACCOUNTS,
    CONF_DEBUG,
    CONF_EXCLUDE_DEVICES,
    CONF_EXTENDED_ENTITY_DISCOVERY,
    CONF_INCLUDE_DEVICES,
    CONF_OAUTH,
    CONF_OTPSECRET,
    CONF_PUBLIC_URL,
    CONF_QUEUE_DELAY,
    DATA_ALEXAMEDIA,
    DATA_LISTENER,
    DEFAULT_EXTENDED_ENTITY_DISCOVERY,
    DEFAULT_PUBLIC_URL,
    DEFAULT_QUEUE_DELAY,
    DEFAULT_SCAN_INTERVAL,
    DEPENDENT_ALEXA_COMPONENTS,
    DOMAIN,
    ISSUE_URL,
    MIN_TIME_BETWEEN_FORCED_SCANS,
    MIN_TIME_BETWEEN_SCANS,
    SCAN_INTERVAL,
    STARTUP,
)
from .exceptions import TimeoutException
from .helpers import (
    _catch_login_errors,
    _existing_serials,
    alarm_just_dismissed,
    calculate_uuid,
)
from .notify import async_unload_entry as notify_async_unload_entry
from .services import AlexaMediaServices

_LOGGER = logging.getLogger(__name__)

# Simple cooldown in seconds; tweak if needed
NOTIFICATION_COOLDOWN = 60
# seconds between retries when API says "Rate exceeded"/None
NOTIFY_REFRESH_BACKOFF = 15.0
# Maximum number of retries
NOTIFY_REFRESH_MAX_RETRIES = 3

ACCOUNT_CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_URL): cv.string,
        vol.Optional(CONF_INCLUDE_DEVICES, default=[]): vol.All(
            cv.ensure_list, [cv.string]
        ),
        vol.Optional(CONF_EXCLUDE_DEVICES, default=[]): vol.All(
            cv.ensure_list, [cv.string]
        ),
        vol.Optional(CONF_SCAN_INTERVAL, default=SCAN_INTERVAL): cv.time_period,
        vol.Optional(CONF_QUEUE_DELAY, default=DEFAULT_QUEUE_DELAY): cv.positive_float,
        vol.Optional(CONF_EXTENDED_ENTITY_DISCOVERY, default=False): cv.boolean,
        vol.Optional(CONF_DEBUG, default=False): cv.boolean,
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


async def async_setup(hass, config, discovery_info=None):
    # pylint: disable=unused-argument
    """Set up the Alexa domain."""
    if DOMAIN not in config:
        _LOGGER.debug(
            "Nothing to import from configuration.yaml, loading from Integrations",
        )
        return True

    async_create_issue(
        hass,
        DOMAIN,
        "deprecated_yaml_configuration",
        is_fixable=False,
        issue_domain=DOMAIN,
        severity=IssueSeverity.WARNING,
        translation_key="deprecated_yaml_configuration",
        learn_more_url="https://github.com/alandtse/alexa_media_player/wiki/Configuration#configurationyaml",
    )
    _LOGGER.warning(
        "YAML configuration of Alexa Media Player is deprecated "
        "and will be removed in version 4.14.0."
        "There will be no automatic import of this. "
        "Please remove it from your configuration, "
        "restart Home Assistant and use the UI to configure it instead. "
        "Settings > Devices and services > Integrations > ADD INTEGRATION"
    )

    domainconfig = config.get(DOMAIN)
    for account in domainconfig[CONF_ACCOUNTS]:
        entry_found = False
        _LOGGER.debug(
            "Importing config information for %s - %s from configuration.yaml",
            hide_email(account[CONF_EMAIL]),
            account[CONF_URL],
        )
        if hass.config_entries.async_entries(DOMAIN):
            _LOGGER.debug("Found existing config entries")
            for entry in hass.config_entries.async_entries(DOMAIN):
                if (
                    entry.data.get(CONF_EMAIL) == account[CONF_EMAIL]
                    and entry.data.get(CONF_URL) == account[CONF_URL]
                ):
                    _LOGGER.debug("Updating existing entry")
                    hass.config_entries.async_update_entry(
                        entry,
                        data={
                            CONF_EMAIL: account[CONF_EMAIL],
                            CONF_PASSWORD: account[CONF_PASSWORD],
                            CONF_URL: account[CONF_URL],
                            CONF_INCLUDE_DEVICES: account[CONF_INCLUDE_DEVICES],
                            CONF_EXCLUDE_DEVICES: account[CONF_EXCLUDE_DEVICES],
                            CONF_SCAN_INTERVAL: account[
                                CONF_SCAN_INTERVAL
                            ].total_seconds(),
                            CONF_QUEUE_DELAY: account[CONF_QUEUE_DELAY],
                            CONF_OAUTH: account.get(
                                CONF_OAUTH, entry.data.get(CONF_OAUTH, {})
                            ),
                            CONF_OTPSECRET: account.get(
                                CONF_OTPSECRET, entry.data.get(CONF_OTPSECRET, "")
                            ),
                            CONF_EXTENDED_ENTITY_DISCOVERY: account[
                                CONF_EXTENDED_ENTITY_DISCOVERY
                            ],
                            CONF_DEBUG: account[CONF_DEBUG],
                        },
                    )
                    entry_found = True
                    break
        if not entry_found:
            _LOGGER.debug("Creating new config entry")
            hass.async_create_task(
                hass.config_entries.flow.async_init(
                    DOMAIN,
                    context={"source": SOURCE_IMPORT},
                    data={
                        CONF_URL: account[CONF_URL],
                        CONF_EMAIL: account[CONF_EMAIL],
                        CONF_PASSWORD: account[CONF_PASSWORD],
                        CONF_PUBLIC_URL: account[CONF_PUBLIC_URL],
                        CONF_INCLUDE_DEVICES: account[CONF_INCLUDE_DEVICES],
                        CONF_EXCLUDE_DEVICES: account[CONF_EXCLUDE_DEVICES],
                        CONF_SCAN_INTERVAL: account[CONF_SCAN_INTERVAL].total_seconds(),
                        CONF_QUEUE_DELAY: account[CONF_QUEUE_DELAY],
                        CONF_OAUTH: account.get(CONF_OAUTH, {}),
                        CONF_OTPSECRET: account.get(CONF_OTPSECRET, ""),
                        CONF_EXTENDED_ENTITY_DISCOVERY: account[
                            CONF_EXTENDED_ENTITY_DISCOVERY
                        ],
                        CONF_DEBUG: account[CONF_DEBUG],
                    },
                )
            )
    return True


# @retry_async(limit=5, delay=5, catch_exceptions=True)
async def async_setup_entry(hass, config_entry):
    # noqa: MC0001
    """Set up Alexa Media Player as config entry."""

    async def close_alexa_media(event=None) -> None:
        """Clean up Alexa connections."""
        _LOGGER.debug("Received shutdown request: %s", event)
        if hass.data.get(DATA_ALEXAMEDIA, {}).get("accounts"):
            for email, _ in hass.data[DATA_ALEXAMEDIA]["accounts"].items():
                await close_connections(hass, email)

    async def complete_startup(event=None) -> None:
        # pylint: disable=unused-argument
        """Run final tasks after startup."""
        _LOGGER.debug("Completing remaining startup tasks.")
        await asyncio.sleep(10)
        if hass.data[DATA_ALEXAMEDIA].get("notify_service"):
            notify = hass.data[DATA_ALEXAMEDIA].get("notify_service")
            _LOGGER.debug("Refreshing notify targets")
            await notify.async_register_services()

    async def relogin(event=None) -> None:
        """Relogin to Alexa."""
        if hide_email(email) == event.data.get("email"):
            _LOGGER.debug("%s: Received relogin request: %s", hide_email(email), event)
            login_obj: AlexaLogin = hass.data[DATA_ALEXAMEDIA]["accounts"][email].get(
                "login_obj"
            )
            uuid = (await calculate_uuid(hass, email, url))["uuid"]
            if login_obj is None:
                login_obj = AlexaLogin(
                    url=url,
                    email=email,
                    password=password,
                    outputpath=hass.config.path,
                    debug=account.get(CONF_DEBUG),
                    otp_secret=account.get(CONF_OTPSECRET, ""),
                    oauth=account.get(CONF_OAUTH, {}),
                    uuid=uuid,
                    oauth_login=True,
                )
                hass.data[DATA_ALEXAMEDIA]["accounts"][email]["login_obj"] = login_obj
            else:
                login_obj.oauth_login = True
            await login_obj.reset()
            # await login_obj.login()
            if await test_login_status(hass, config_entry, login_obj):
                await setup_alexa(hass, config_entry, login_obj)

    async def login_success(event=None) -> None:
        """Relogin to Alexa."""
        if hide_email(email) == event.data.get("email"):
            _LOGGER.debug("Received Login success: %s", event)
            login_obj: AlexaLogin = hass.data[DATA_ALEXAMEDIA]["accounts"][email].get(
                "login_obj"
            )
            await setup_alexa(hass, config_entry, login_obj)

    if not hass.data.get(DATA_ALEXAMEDIA):
        _LOGGER.debug(STARTUP)
        _LOGGER.debug("Loaded alexapy==%s", alexapy_version)
    hass.data.setdefault(
        DATA_ALEXAMEDIA, {"accounts": {}, "config_flows": {}, "notify_service": None}
    )
    if not hass.data[DATA_ALEXAMEDIA].get("accounts"):
        hass.data[DATA_ALEXAMEDIA] = {
            "accounts": {},
            "config_flows": {},
        }
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
            "devices": {
                "media_player": {},
                "switch": {},
                "guard": [],
                "light": [],
                "binary_sensor": [],
                "temperature": [],
                "smart_switch": [],
            },
            "entities": {
                "media_player": {},
                "switch": {},
                "sensor": {},
                "light": [],
                "binary_sensor": [],
                "alarm_control_panel": {},
                "smart_switch": [],
            },
            "excluded": {},
            "new_devices": True,
            "http2_lastattempt": 0,
            "http2error": 0,
            "http2_commands": {},
            "http2_activity": {"serials": {}, "refreshed": {}},
            "http2": None,
            "auth_info": None,
            "second_account_index": 0,
            "should_get_network": True,
            "notifications": {},  # already used for the raw notifications dict
            "notifications_pending": set(),  # doppler serials that need a refresh
            "notifications_refresh_task": None,  # running task or None
            "notifications_retry_count": 0,  # simple backoff counter
            "options": {
                CONF_INCLUDE_DEVICES: config_entry.data.get(CONF_INCLUDE_DEVICES, ""),
                CONF_EXCLUDE_DEVICES: config_entry.data.get(CONF_EXCLUDE_DEVICES, ""),
                CONF_QUEUE_DELAY: config_entry.data.get(
                    CONF_QUEUE_DELAY, DEFAULT_QUEUE_DELAY
                ),
                CONF_SCAN_INTERVAL: config_entry.data.get(
                    CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                ),
                CONF_PUBLIC_URL: config_entry.data.get(
                    CONF_PUBLIC_URL, DEFAULT_PUBLIC_URL
                ),
                CONF_EXTENDED_ENTITY_DISCOVERY: config_entry.data.get(
                    CONF_EXTENDED_ENTITY_DISCOVERY, DEFAULT_EXTENDED_ENTITY_DISCOVERY
                ),
                CONF_DEBUG: config_entry.data.get(CONF_DEBUG, False),
            },
            DATA_LISTENER: [config_entry.add_update_listener(update_listener)],
        },
    )
    uuid_dict = await calculate_uuid(hass, email, url)
    uuid = uuid_dict["uuid"]
    hass.data[DATA_ALEXAMEDIA]["accounts"][email]["second_account_index"] = uuid_dict[
        "index"
    ]
    login: AlexaLogin = hass.data[DATA_ALEXAMEDIA]["accounts"][email].get(
        "login_obj",
        AlexaLogin(
            url=url,
            email=email,
            password=password,
            outputpath=hass.config.path,
            debug=account.get(CONF_DEBUG),
            otp_secret=account.get(CONF_OTPSECRET, ""),
            oauth=account.get(CONF_OAUTH, {}),
            uuid=uuid,
            oauth_login=True,
        ),
    )
    hass.data[DATA_ALEXAMEDIA]["accounts"][email]["login_obj"] = login
    hass.data[DATA_ALEXAMEDIA]["accounts"][email]["last_push_activity"] = 0
    if not hass.data[DATA_ALEXAMEDIA]["accounts"][email]["second_account_index"]:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, close_alexa_media)
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, complete_startup)
    hass.bus.async_listen("alexa_media_relogin_required", relogin)
    hass.bus.async_listen("alexa_media_relogin_success", login_success)
    try:
        await login.login(cookies=await login.load_cookie())
        if await test_login_status(hass, config_entry, login):
            await setup_alexa(hass, config_entry, login)
            return True
        return False
    except AlexapyConnectionError as err:
        raise ConfigEntryNotReady(str(err) or "Connection Error during login") from err


async def setup_alexa(hass, config_entry, login_obj: AlexaLogin):
    # pylint: disable=too-many-statements,too-many-locals
    """Set up a alexa api based on host parameter."""

    # Initialize throttling state and lock
    last_dnd_update_times: dict[str, datetime] = {}
    pending_dnd_updates: dict[str, bool] = {}
    dnd_update_lock = asyncio.Lock()

    async def async_update_data() -> Optional[AlexaEntityData]:
        # noqa pylint: disable=too-many-branches
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.

        This will ping Alexa API to identify all devices, bluetooth, and the last
        called device.

        If any guards, temperature sensors, or lights are configured, their
        current state will be acquired. This data is returned directly so that it is available on the coordinator.

        This will add new devices and services when discovered. By default this
        runs every SCAN_INTERVAL seconds unless another method calls it. if
        push is connected, it will increase the delay 10-fold between updates.
        While throttled at MIN_TIME_BETWEEN_SCANS, care should be taken to
        reduce the number of runs to avoid flooding. Slow changing states
        should be checked here instead of in spawned components like
        media_player since this object is one per account.
        Each AlexaAPI call generally results in two webpage requests.
        """
        email = config.get(CONF_EMAIL)
        login_obj = hass.data[DATA_ALEXAMEDIA]["accounts"][email]["login_obj"]
        if (
            email not in hass.data[DATA_ALEXAMEDIA]["accounts"]
            or not login_obj.status.get("login_successful")
            or login_obj.session.closed
            or login_obj.close_requested
        ):
            return
        existing_serials = _existing_serials(hass, login_obj)
        existing_entities = hass.data[DATA_ALEXAMEDIA]["accounts"][email]["entities"][
            "media_player"
        ].values()
        auth_info = hass.data[DATA_ALEXAMEDIA]["accounts"][email].get("auth_info")
        new_devices = hass.data[DATA_ALEXAMEDIA]["accounts"][email]["new_devices"]
        extended_entity_discovery = hass.data[DATA_ALEXAMEDIA]["accounts"][email][
            "options"
        ].get(CONF_EXTENDED_ENTITY_DISCOVERY)
        should_get_network = (
            extended_entity_discovery
            and hass.data[DATA_ALEXAMEDIA]["accounts"][email]["should_get_network"]
        )

        devices = {}
        bluetooth = {}
        preferences = {}
        dnd = {}
        entity_state = {}
        tasks = [
            AlexaAPI.get_devices(login_obj),
            AlexaAPI.get_bluetooth(login_obj),
            AlexaAPI.get_device_preferences(login_obj),
            AlexaAPI.get_dnd_state(login_obj),
        ]
        if new_devices:
            tasks.append(AlexaAPI.get_authentication(login_obj))

        entities_to_monitor = set()
        for sensor in hass.data[DATA_ALEXAMEDIA]["accounts"][email]["entities"][
            "sensor"
        ].values():
            temp = sensor.get("Temperature")
            if temp and temp.enabled:
                entities_to_monitor.add(temp.alexa_entity_id)

            temp = sensor.get("Air_Quality")
            if temp and temp.enabled:
                entities_to_monitor.add(temp.alexa_entity_id)

        for light in hass.data[DATA_ALEXAMEDIA]["accounts"][email]["entities"]["light"]:
            if light.enabled:
                entities_to_monitor.add(light.alexa_entity_id)

        for binary_sensor in hass.data[DATA_ALEXAMEDIA]["accounts"][email]["entities"][
            "binary_sensor"
        ]:
            if binary_sensor.enabled:
                entities_to_monitor.add(binary_sensor.alexa_entity_id)

        for guard in hass.data[DATA_ALEXAMEDIA]["accounts"][email]["entities"][
            "alarm_control_panel"
        ].values():
            if guard.enabled:
                entities_to_monitor.add(guard.unique_id)

        if entities_to_monitor:
            tasks.append(get_entity_data(login_obj, list(entities_to_monitor)))

        if should_get_network:
            tasks.append(AlexaAPI.get_network_details(login_obj))

        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            # Increase timeout from 30s to 45s to permit
            # get_network_details() retries which could up to 30s.
            async with async_timeout.timeout(45):
                (
                    devices,
                    bluetooth,
                    preferences,
                    dnd,
                    *optional_task_results,
                ) = await asyncio.gather(*tasks)

                if should_get_network:
                    _LOGGER.info("%s: Network Discovery: Checking", hide_email(email))
                    api_devices = optional_task_results.pop()
                    if not api_devices:
                        _LOGGER.warning(
                            "%s: Network Discovery: AlexaAPI returned an unexpected response. Retrying on next polling cycle",
                            hide_email(email),
                        )
                    else:
                        _LOGGER.debug(
                            "%s: Network Discovery: Success, processing response",
                            hide_email(email),
                        )
                        # Only process this once after success
                        hass.data[DATA_ALEXAMEDIA]["accounts"][email][
                            "should_get_network"
                        ] = False

                        # Discard the entities_to_monitor results since we now have full network details
                        if entities_to_monitor:
                            optional_task_results.pop()
                            entities_to_monitor.clear()

                        alexa_entities = parse_alexa_entities(api_devices)
                        hass.data[DATA_ALEXAMEDIA]["accounts"][email]["devices"].update(
                            alexa_entities
                        )

                        # First run is a special case. Get the state of all entities(including disabled)
                        # This ensures all entities have state during startup without needing to request coordinator refresh

                        _entities_to_monitor = set()
                        for type_of_entity, entities in alexa_entities.items():
                            if type_of_entity == "guard" or extended_entity_discovery:
                                for entity in entities:
                                    _entities_to_monitor.add(entity.get("id"))
                        _LOGGER.debug(
                            "%s: Network Discovery: %s entities will be monitored",
                            hide_email(email),
                            len(list(_entities_to_monitor)),
                        )
                        entity_state = await get_entity_data(
                            login_obj, list(_entities_to_monitor)
                        )

                if entities_to_monitor:
                    entity_state = optional_task_results.pop()
                    _LOGGER.debug(
                        "%s: Processing %s entities to monitor",
                        hide_email(email),
                        len(list(entities_to_monitor)),
                    )

                if new_devices:
                    auth_info = optional_task_results.pop()
                    _LOGGER.debug(
                        "%s: Found %s devices, %s bluetooth",
                        hide_email(email),
                        len(devices) if devices is not None else "",
                        (
                            len(bluetooth.get("bluetoothStates", []))
                            if bluetooth is not None
                            else ""
                        ),
                    )

                # Always keep notifications in sync; internal cooldown prevents API spam
                await process_notifications(login_obj)

                # Process last_called data to fire events
                await update_last_called(login_obj)

        except (AlexapyLoginError, JSONDecodeError):
            _LOGGER.debug(
                "%s: Alexa API disconnected; attempting to relogin : status %s",
                hide_email(email),
                login_obj.status,
            )
            if login_obj.status:
                hass.bus.async_fire(
                    "alexa_media_relogin_required",
                    event_data={"email": hide_email(email), "url": login_obj.url},
                )
            return
        except BaseException as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

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
            if exclude and dev_name in exclude:
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

            if (
                dev_name not in include_filter
                and device.get("capabilities")
                and not any(
                    x in device["capabilities"]
                    for x in ["MUSIC_SKILL", "TIMERS_AND_ALARMS", "REMINDERS"]
                )
            ):
                # skip devices without music or notification skill
                _LOGGER.debug("Excluding %s for lacking capability", dev_name)
                continue

            if bluetooth is not None and "bluetoothStates" in bluetooth:
                for b_state in bluetooth["bluetoothStates"]:
                    if serial == b_state["deviceSerialNumber"]:
                        device["bluetooth_state"] = b_state
                        break

            if preferences is not None and "devicePreferences" in preferences:
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

            if dnd is not None and "doNotDisturbDeviceStatusList" in dnd:
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
            elif (
                serial in existing_serials
                and hass.data[DATA_ALEXAMEDIA]["accounts"][email]["entities"][
                    "media_player"
                ].get(serial)
                and hass.data[DATA_ALEXAMEDIA]["accounts"][email]["entities"][
                    "media_player"
                ]
                .get(serial)
                .enabled
            ):
                await hass.data[DATA_ALEXAMEDIA]["accounts"][email]["entities"][
                    "media_player"
                ].get(serial).refresh(device, skip_api=True)
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
            # Load multiple platforms in parallel using async_forward_entry_setups
            _LOGGER.debug("Loading platforms: %s", ", ".join(ALEXA_COMPONENTS))
            try:
                await hass.config_entries.async_forward_entry_setups(
                    config_entry, ALEXA_COMPONENTS
                )
            except (asyncio.TimeoutError, TimeoutException) as ex:
                _LOGGER.error(f"Error while loading platforms: {ex}")
                raise ConfigEntryNotReady(
                    f"Timeout while loading platforms: {ex}"
                ) from ex

        hass.data[DATA_ALEXAMEDIA]["accounts"][email]["new_devices"] = False
        # prune stale devices
        device_registry = dr.async_get(hass)
        for device_entry in dr.async_entries_for_config_entry(
            device_registry, config_entry.entry_id
        ):
            for _, identifier in device_entry.identifiers:
                if identifier in hass.data[DATA_ALEXAMEDIA]["accounts"][email][
                    "devices"
                ]["media_player"].keys() or identifier in map(
                    lambda x: slugify(f"{x}_{email}"),
                    hass.data[DATA_ALEXAMEDIA]["accounts"][email]["devices"][
                        "media_player"
                    ].keys(),
                ):
                    break
            else:
                device_registry.async_remove_device(device_entry.id)
                _LOGGER.debug(
                    "%s: Removing stale device %s", hide_email(email), device_entry.name
                )

        await login_obj.save_cookiefile()
        if login_obj.access_token:
            hass.config_entries.async_update_entry(
                config_entry,
                data={
                    **config_entry.data,
                    CONF_OAUTH: {
                        "access_token": login_obj.access_token,
                        "refresh_token": login_obj.refresh_token,
                        "expires_in": login_obj.expires_in,
                        "mac_dms": login_obj.mac_dms,
                        "code_verifier": login_obj.code_verifier,
                        "authorization_code": login_obj.authorization_code,
                    },
                },
            )
        return entity_state

    @_catch_login_errors
    async def process_notifications(login_obj, raw_notifications=None) -> bool:
        """Process raw notifications json.

        Returns True if notifications were updated, False if we skipped
        (e.g. due to cooldown or alexapy returned None).
        """
        email: str = login_obj.email
        account_dict = hass.data[DATA_ALEXAMEDIA]["accounts"][email]

        if raw_notifications is None:
            now = time.time()
            last = account_dict.get("last_notif_poll", 0.0)
            delta = now - last

            if delta < NOTIFICATION_COOLDOWN:
                _LOGGER.debug(
                    "%s: Skipping get_notifications; last poll %.1fs ago "
                    "(cooldown %ss).",
                    hide_email(email),
                    delta,
                    NOTIFICATION_COOLDOWN,
                )
                return False

            account_dict["last_notif_poll"] = now

            # Small delay to let Alexa settle if we're polling explicitly
            await asyncio.sleep(4)
            raw_notifications = await AlexaAPI.get_notifications(login_obj)

        previous = account_dict.get("notifications", {})
        notifications = {"process_timestamp": dt.utcnow()}

        if raw_notifications is not None:
            for notification in raw_notifications:
                n_dev_id = notification.get("deviceSerialNumber")
                if n_dev_id is None:
                    # skip notifications untied to a device for now
                    # https://github.com/alandtse/alexa_media_player/issues/633#issuecomment-610705651
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
                    previous_alarm = (
                        previous.get(n_dev_id, {}).get("Alarm", {}).get(n_id)
                    )
                    if previous_alarm and alarm_just_dismissed(
                        notification,
                        previous_alarm.get("status"),
                        previous_alarm.get("version"),
                    ):
                        hass.bus.async_fire(
                            "alexa_media_alarm_dismissal_event",
                            event_data={
                                "device": {"id": n_dev_id},
                                "event": notification,
                            },
                        )

                if n_dev_id not in notifications:
                    notifications[n_dev_id] = {}
                if n_type not in notifications[n_dev_id]:
                    notifications[n_dev_id][n_type] = {}
                notifications[n_dev_id][n_type][n_id] = notification

        account_dict["notifications"] = notifications
        _LOGGER.debug(
            "%s: Updated %s notifications for %s devices at %s",
            hide_email(email),
            len(raw_notifications) if raw_notifications is not None else 0,
            len(notifications),
            dt.as_local(account_dict["notifications"]["process_timestamp"]),
        )
        # Notify sensors that the notifications snapshot has been refreshed
        async_dispatcher_send(
            hass,
            f"{DOMAIN}_{hide_email(email)}"[0:32],
            {"notifications_refreshed": True},
        )
        return True

    @_catch_login_errors
    async def update_last_called(login_obj, last_called=None, force=False):
        """Update the last called device for the login_obj.

        This will store the last_called in hass.data and also fire an event
        to notify listeners.
        """
        if not last_called or not (last_called and last_called.get("summary")):
            try:
                async with async_timeout.timeout(10):
                    last_called = await AlexaAPI.get_last_device_serial(login_obj)
            except TypeError:
                _LOGGER.debug(
                    "%s: Error updating last_called: %s",
                    hide_email(email),
                    hide_serial(last_called),
                )
                return
        _LOGGER.debug(
            "%s: Updated last_called: %s", hide_email(email), hide_serial(last_called)
        )
        stored_data = hass.data[DATA_ALEXAMEDIA]["accounts"][email]
        if (
            force
            or "last_called" in stored_data
            and last_called != stored_data["last_called"]
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

    @_catch_login_errors
    async def update_bluetooth_state(login_obj, device_serial):
        """Update the bluetooth state on ws bluetooth event."""
        bluetooth = await AlexaAPI.get_bluetooth(login_obj)
        device = hass.data[DATA_ALEXAMEDIA]["accounts"][email]["devices"][
            "media_player"
        ][device_serial]

        if bluetooth is not None and "bluetoothStates" in bluetooth:
            for b_state in bluetooth["bluetoothStates"]:
                if device_serial == b_state["deviceSerialNumber"]:
                    _LOGGER.debug(
                        "%s: setting value for: %s to %s",
                        hide_email(email),
                        hide_serial(device_serial),
                        hide_serial(b_state),
                    )
                    device["bluetooth_state"] = b_state
                    return device["bluetooth_state"]
        _LOGGER.debug(
            "%s: get_bluetooth for: %s failed with %s",
            hide_email(email),
            hide_serial(device_serial),
            hide_serial(bluetooth),
        )
        return None

    async def schedule_update_dnd_state(email: str):
        """Schedule an update_dnd_state call after MIN_TIME_BETWEEN_FORCED_SCANS."""
        await asyncio.sleep(MIN_TIME_BETWEEN_FORCED_SCANS)
        async with dnd_update_lock:
            if pending_dnd_updates.get(email, False):
                pending_dnd_updates[email] = False
                _LOGGER.debug(
                    "Executing scheduled forced DND update for %s", hide_email(email)
                )
                # Assume login_obj can be retrieved or passed appropriately
                login_obj = hass.data[DATA_ALEXAMEDIA]["accounts"][email]["login_obj"]
                await update_dnd_state(login_obj)

    @_catch_login_errors
    async def update_dnd_state(login_obj) -> None:
        """Update the DND state on websocket DND combo event."""
        email = login_obj.email
        now = datetime.utcnow()

        async with dnd_update_lock:
            last_run = last_dnd_update_times.get(email)
            cooldown = timedelta(seconds=MIN_TIME_BETWEEN_SCANS)

            if last_run and (now - last_run) < cooldown:
                # If within cooldown, mark a pending update if not already marked
                if not pending_dnd_updates.get(email, False):
                    pending_dnd_updates[email] = True
                    _LOGGER.debug(
                        "Throttling active for %s, scheduling a forced DND update.",
                        hide_email(email),
                    )
                    asyncio.create_task(schedule_update_dnd_state(email))
                else:
                    _LOGGER.debug(
                        "Throttling active for %s, forced DND update already scheduled.",
                        hide_email(email),
                    )
                return

            # Update the last run time
            last_dnd_update_times[email] = now

        _LOGGER.debug("Updating DND state for %s", hide_email(email))
        try:
            # Fetch the DND state using the Alexa API
            dnd = await AlexaAPI.get_dnd_state(login_obj)
        except asyncio.TimeoutError:
            _LOGGER.error(
                "Timeout occurred while fetching DND state for %s", hide_email(email)
            )
            return
        except Exception as e:
            _LOGGER.error(
                "Unexpected error while fetching DND state for %s: %s",
                hide_email(email),
                e,
            )
            return

        # Check if DND data is valid and dispatch an update event
        if dnd is not None and "doNotDisturbDeviceStatusList" in dnd:
            async_dispatcher_send(
                hass,
                f"{DOMAIN}_{hide_email(email)}"[0:32],
                {"dnd_update": dnd["doNotDisturbDeviceStatusList"]},
            )
            return
        else:
            _LOGGER.debug("%s: get_dnd_state failed: dnd:%s", hide_email(email), dnd)

    def _schedule_notifications_refresh(
        hass,
        email: str,
        device_serial: str | None = None,
        reason: str = "",
    ) -> None:
        """Mark notifications as needing refresh and ensure worker task is running.

        device_serial is just for debug; we track a set of pending devices but
        we always refresh the full notifications payload once.
        """
        account = hass.data[DATA_ALEXAMEDIA]["accounts"][email]

        if device_serial:
            account["notifications_pending"].add(device_serial)
        else:
            # Special marker for "global" changes if you want one
            account["notifications_pending"].add("*")

        if reason:
            _LOGGER.debug(
                "%s: Scheduling notifications refresh (reason=%s, pending=%s)",
                hide_email(email),
                reason,
                account["notifications_pending"],
            )

        task = account.get("notifications_refresh_task")
        if task is not None and not task.done():
            # Already have a running worker; it'll see the new pending set
            return

        # Start new worker
        account["notifications_refresh_task"] = hass.async_create_task(
            _run_notifications_refresh(hass, email)
        )

    async def _run_notifications_refresh(hass, email: str) -> None:
        """Worker task: refresh notifications for an account if pending.

        - Uses alexapy.AlexaAPI.get_notifications(login)
        - Retries a few times if we only get None (cooldown/throttle)
        - Clears notifications_pending when successful or when we give up
        """
        account = hass.data[DATA_ALEXAMEDIA]["accounts"][email]
        login = account["login_obj"]

        try:
            retries = 0
            while (
                account["notifications_pending"]
                and retries <= NOTIFY_REFRESH_MAX_RETRIES
            ):
                try:
                    data = await AlexaAPI.get_notifications(login)
                except Exception as ex:
                    _LOGGER.warning(
                        "%s: get_notifications raised %s; treating as None. This may indicate an unexpected error.",
                        hide_email(email),
                        ex,
                    )
                    data = None

                if data is not None:
                    # Success: update through the normal processing path
                    await process_notifications(login, raw_notifications=data)
                    account["notifications_retry_count"] = 0
                    account["notifications_pending"].clear()

                    _LOGGER.debug(
                        "%s: Refreshed notifications snapshot (pending cleared)",
                        hide_email(email),
                    )
                    return

                # If we get here, alexapy side returned None (cooldown / throttle)
                retries += 1
                account["notifications_retry_count"] = retries

                if not account["notifications_pending"]:
                    # Nothing to do anymore, bail early
                    break

                _LOGGER.debug(
                    "%s: Notifications refresh returned None (retry %s/%s); "
                    "pending=%s; sleeping %.1fs",
                    hide_email(email),
                    retries,
                    NOTIFY_REFRESH_MAX_RETRIES,
                    account["notifications_pending"],
                    NOTIFY_REFRESH_BACKOFF,
                )
                await asyncio.sleep(NOTIFY_REFRESH_BACKOFF)

            # If we fall through, give up for now but leave pending set alone
            if account["notifications_pending"]:
                _LOGGER.debug(
                    "%s: Giving up notifications refresh after %s attempts; "
                    "still pending=%s",
                    hide_email(email),
                    retries,
                    account["notifications_pending"],
                )

        finally:
            # Always clear the task pointer so future pushes can schedule again
            account["notifications_refresh_task"] = None

    async def http2_connect() -> HTTP2EchoClient:
        """Open HTTP2 Push connection.

        This will only attempt one login before failing.
        """
        http2: Optional[HTTP2EchoClient] = None
        email = login_obj.email
        try:
            if login_obj.session.closed:
                _LOGGER.debug(
                    "%s: HTTP2 creation aborted. Session is closed.",
                    hide_email(email),
                )
                return
            http2 = HTTP2EchoClient(
                login_obj,
                msg_callback=http2_handler,
                open_callback=http2_open_handler,
                close_callback=http2_close_handler,
                error_callback=http2_error_handler,
                loop=hass.loop,
            )
            _LOGGER.debug("%s: HTTP2 created: %s", hide_email(email), http2)
            await http2.async_run()
        except AlexapyLoginError as exception_:
            _LOGGER.debug(
                "%s: Login Error detected from http2: %s",
                hide_email(email),
                exception_,
            )
            hass.bus.async_fire(
                "alexa_media_relogin_required",
                event_data={"email": hide_email(email), "url": login_obj.url},
            )
            return
        except BaseException as exception_:  # pylint: disable=broad-except
            _LOGGER.debug(
                "%s: HTTP2 creation failed: %s", hide_email(email), exception_
            )
            return
        return http2

    @callback
    async def http2_handler(message_obj):
        # pylint: disable=too-many-branches
        """Handle http2 push messages.

        This allows push notifications from Alexa to update last_called
        and media state.
        """
        coordinator = hass.data[DATA_ALEXAMEDIA]["accounts"][email].get("coordinator")

        updates = (
            message_obj.get("directive", {})
            .get("payload", {})
            .get("renderingUpdates", [])
        )
        for item in updates:
            resource = loads(item.get("resourceMetadata", ""))
            command = (
                resource["command"]
                if isinstance(resource, dict) and "command" in resource
                else None
            )
            json_payload = (
                loads(resource["payload"])
                if isinstance(resource, dict) and "payload" in resource
                else None
            )
            existing_serials = _existing_serials(hass, login_obj)
            seen_commands = hass.data[DATA_ALEXAMEDIA]["accounts"][email][
                "http2_commands"
            ]

            if command and json_payload:
                _LOGGER.debug(
                    "%s: Received http2push command: %s : %s",
                    hide_email(email),
                    command,
                    hide_serial(json_payload),
                )
                serial = None
                command_time = time.time()
                if command not in seen_commands:
                    _LOGGER.debug(
                        "Adding %s to seen_commands: %s", command, seen_commands
                    )
                seen_commands[command] = command_time

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
                    try:
                        if coordinator:
                            await coordinator.async_request_refresh()

                        if serial and serial in existing_serials:
                            await update_last_called(login_obj, last_called)
                        _LOGGER.debug("Updating last_called: %s", last_called)
                        async_dispatcher_send(
                            hass,
                            f"{DOMAIN}_{hide_email(email)}"[0:32],
                            {"push_activity": json_payload},
                        )
                    except AlexapyConnectionError:
                        # Catch case where activities doesn't report valid json
                        pass
                elif command in (
                    "PUSH_AUDIO_PLAYER_STATE",
                    "PUSH_MEDIA_CHANGE",
                    "PUSH_MEDIA_PROGRESS_CHANGE",
                    "NotifyMediaSessionsUpdated",
                    "NotifyNowPlayingUpdated",
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
                    elif command == "NotifyNowPlayingUpdated":
                        _LOGGER.debug("Send NowPlaying: %s", hide_serial(json_payload))
                        async_dispatcher_send(
                            hass,
                            f"{DOMAIN}_{hide_email(email)}"[0:32],
                            {"now_playing": json_payload},
                        )
                elif command == "PUSH_VOLUME_CHANGE":
                    # Player volume update
                    if serial and serial in existing_serials:
                        _LOGGER.debug(
                            "Updating media_player volume: %s",
                            hide_serial(json_payload),
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
                            "Updating media_player bluetooth %s",
                            hide_serial(json_payload),
                        )
                        bluetooth_state = await update_bluetooth_state(
                            login_obj, serial
                        )
                        _LOGGER.debug(
                            "bluetooth_state %s", hide_serial(bluetooth_state)
                        )
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
                    # Notification/alarm state changed on this device.
                    # Queue a refresh with backoff to ride out alexa-side cooldowns.
                    _schedule_notifications_refresh(
                        hass,
                        email,
                        device_serial=serial,
                        reason="PUSH_NOTIFICATION_CHANGE",
                    )

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
                    "PUSH_LIST_CHANGE",  # clear a shopping list https://github.com/alandtse/alexa_media_player/issues/1190
                    "PUSH_LIST_ITEM_CHANGE",  # update shopping list
                    "PUSH_CONTENT_FOCUS_CHANGE",  # likely prime related refocus
                    "PUSH_DEVICE_SETUP_STATE_CHANGE",  # likely device changes mid setup
                    "PUSH_MEDIA_PREFERENCE_CHANGE",  # disliking or liking songs, https://github.com/alandtse/alexa_media_player/issues/1599
                ]:
                    pass
                else:
                    _LOGGER.debug(
                        "Unhandled command: %s with data %s. Please report at %s",
                        command,
                        hide_serial(json_payload),
                        ISSUE_URL,
                    )
                if serial in existing_serials:
                    history = hass.data[DATA_ALEXAMEDIA]["accounts"][email][
                        "http2_activity"
                    ]["serials"].get(serial)
                    if history is None or (
                        history and command_time - history[len(history) - 1][1] > 2
                    ):
                        history = [(command, command_time)]
                    else:
                        history.append([command, command_time])
                    hass.data[DATA_ALEXAMEDIA]["accounts"][email]["http2_activity"][
                        "serials"
                    ][serial] = history
                    events = []
                    for old_command, old_command_time in history:
                        if (
                            old_command
                            in {"PUSH_VOLUME_CHANGE", "PUSH_EQUALIZER_STATE_CHANGE"}
                            and command_time - old_command_time < 0.25
                        ):
                            events.append(
                                (old_command, round(command_time - old_command_time, 2))
                            )
                        elif old_command in {"PUSH_AUDIO_PLAYER_STATE"}:
                            # There is a potential false positive generated during this event
                            events = []
                    if len(events) >= 4:
                        _LOGGER.debug(
                            "%s: Detected potential DND http2push change with %s events %s",
                            hide_serial(serial),
                            len(events),
                            events,
                        )
                        await update_dnd_state(login_obj)
                if (
                    serial
                    and serial not in existing_serials
                    and serial
                    not in (
                        hass.data[DATA_ALEXAMEDIA]["accounts"][email]["excluded"].keys()
                    )
                ):
                    _LOGGER.debug("Discovered new media_player %s", hide_serial(serial))
                    (hass.data[DATA_ALEXAMEDIA]["accounts"][email]["new_devices"]) = (
                        True
                    )
                    if coordinator:
                        await coordinator.async_request_refresh()

    @callback
    async def http2_open_handler():
        """Handle http2 open."""

        email: str = login_obj.email
        _LOGGER.debug("%s: HTTP2push successfully connected", hide_email(email))
        hass.data[DATA_ALEXAMEDIA]["accounts"][email][
            "http2error"
        ] = 0  # set errors to 0
        hass.data[DATA_ALEXAMEDIA]["accounts"][email]["http2_lastattempt"] = time.time()

    @callback
    async def http2_close_handler():
        """Handle http2 close.

        This should attempt to reconnect up to 5 times
        """
        email: str = login_obj.email
        hass.data[DATA_ALEXAMEDIA]["accounts"][email]["http2"] = None
        if login_obj.close_requested:
            _LOGGER.debug(
                "%s: Close requested; will not reconnect http2", hide_email(email)
            )
            return
        if not login_obj.status.get("login_successful"):
            _LOGGER.debug(
                "%s: Login error; will not reconnect http2", hide_email(email)
            )
            return
        errors: int = hass.data[DATA_ALEXAMEDIA]["accounts"][email]["http2error"]
        delay: int = 5 * 2**errors
        last_attempt = hass.data[DATA_ALEXAMEDIA]["accounts"][email][
            "http2_lastattempt"
        ]
        now = time.time()
        if (now - last_attempt) < delay:
            return
        http2_enabled: bool = hass.data[DATA_ALEXAMEDIA]["accounts"][email]["http2"]
        while errors < 5 and not (http2_enabled):
            _LOGGER.debug(
                "%s: HTTP2 push closed; reconnect #%i in %is",
                hide_email(email),
                errors,
                delay,
            )
            hass.data[DATA_ALEXAMEDIA]["accounts"][email][
                "http2_lastattempt"
            ] = time.time()
            http2_enabled = hass.data[DATA_ALEXAMEDIA]["accounts"][email]["http2"] = (
                await http2_connect()
            )
            errors = hass.data[DATA_ALEXAMEDIA]["accounts"][email]["http2error"] = (
                hass.data[DATA_ALEXAMEDIA]["accounts"][email]["http2error"] + 1
            )
            delay = 5 * 2**errors
            errors = hass.data[DATA_ALEXAMEDIA]["accounts"][email]["http2error"]
            await asyncio.sleep(delay)
        if not http2_enabled:
            _LOGGER.debug(
                "%s: HTTP2Push connection closed; retries exceeded; polling",
                hide_email(email),
            )
        if coordinator:
            coordinator.update_interval = timedelta(
                seconds=scan_interval * 10 if http2_enabled else scan_interval
            )
            await coordinator.async_request_refresh()

    @callback
    async def http2_error_handler(message):
        """Handle http2push error.

        This currently logs the error.  In the future, this should invalidate
        the http2push and determine if a reconnect should be done.
        """
        email: str = login_obj.email
        errors = hass.data[DATA_ALEXAMEDIA]["accounts"][email]["http2error"]
        _LOGGER.debug(
            "%s: Received http2push error #%i %s: type %s",
            hide_email(email),
            errors,
            message,
            type(message),
        )
        hass.data[DATA_ALEXAMEDIA]["accounts"][email]["http2"] = None
        if not login_obj.close_requested and (
            login_obj.session.closed or isinstance(message, AlexapyLoginError)
        ):
            hass.data[DATA_ALEXAMEDIA]["accounts"][email]["http2error"] = 5
            _LOGGER.debug("%s: Login error detected.", hide_email(email))
            hass.bus.async_fire(
                "alexa_media_relogin_required",
                event_data={"email": hide_email(email), "url": login_obj.url},
            )
            return
        hass.data[DATA_ALEXAMEDIA]["accounts"][email]["http2error"] = errors + 1

    _LOGGER.debug("Setting up Alexa devices for %s", hide_email(login_obj.email))
    config = config_entry.data
    email = config.get(CONF_EMAIL)
    include = (
        cv.ensure_list_csv(config[CONF_INCLUDE_DEVICES])
        if config[CONF_INCLUDE_DEVICES]
        else ""
    )
    _LOGGER.debug("include: %s", include)
    exclude = (
        cv.ensure_list_csv(config[CONF_EXCLUDE_DEVICES])
        if config[CONF_EXCLUDE_DEVICES]
        else ""
    )
    _LOGGER.debug("exclude: %s", exclude)
    scan_interval: float = (
        config.get(CONF_SCAN_INTERVAL).total_seconds()
        if isinstance(config.get(CONF_SCAN_INTERVAL), timedelta)
        else config.get(CONF_SCAN_INTERVAL)
    )
    hass.data[DATA_ALEXAMEDIA]["accounts"][email]["login_obj"] = login_obj
    http2_enabled = hass.data[DATA_ALEXAMEDIA]["accounts"][email]["http2"] = (
        await http2_connect()
    )
    coordinator = hass.data[DATA_ALEXAMEDIA]["accounts"][email].get("coordinator")
    if coordinator is None:
        _LOGGER.debug("%s: Creating coordinator", hide_email(email))
        hass.data[DATA_ALEXAMEDIA]["accounts"][email]["coordinator"] = coordinator = (
            DataUpdateCoordinator(
                hass,
                _LOGGER,
                # Name of the data. For logging purposes.
                name="alexa_media",
                update_method=async_update_data,
                # Polling interval. Will only be polled if there are subscribers.
                update_interval=timedelta(
                    seconds=scan_interval * 10 if http2_enabled else scan_interval
                ),
            )
        )
    else:
        _LOGGER.debug("%s: Reusing coordinator", hide_email(email))
        coordinator.update_interval = timedelta(
            seconds=scan_interval * 10 if http2_enabled else scan_interval
        )
    # Fetch initial data so we have data when entities subscribe
    _LOGGER.debug("%s: Refreshing coordinator", hide_email(email))
    await coordinator.async_refresh()

    hass.data[DATA_ALEXAMEDIA]["services"] = alexa_services = AlexaMediaServices(
        hass, functions={"update_last_called": update_last_called}
    )
    await alexa_services.register()
    return True


async def async_unload_entry(hass, entry) -> bool:
    """Unload a config entry"""
    email = entry.data["email"]
    login_obj = hass.data[DATA_ALEXAMEDIA]["accounts"][email]["login_obj"]
    _LOGGER.debug("Unloading entry: %s", hide_email(email))
    refresh_task = hass.data[DATA_ALEXAMEDIA]["accounts"][email].get(
        "notifications_refresh_task"
    )
    if refresh_task and not refresh_task.done():
        refresh_task.cancel()
        try:
            await refresh_task
        except asyncio.CancelledError:
            # Task cancellation is expected during unload; ignore this exception.
            pass
    for component in ALEXA_COMPONENTS + DEPENDENT_ALEXA_COMPONENTS:
        try:
            if component == "notify":
                await notify_async_unload_entry(hass, entry)
            else:
                _LOGGER.debug("Forwarding unload entry to %s", component)
                await hass.config_entries.async_forward_entry_unload(entry, component)
        except Exception as ex:
            _LOGGER.error("Error unloading: %s", component)
    await close_connections(hass, email)
    for listener in hass.data[DATA_ALEXAMEDIA]["accounts"][email][DATA_LISTENER]:
        listener()
    hass.data[DATA_ALEXAMEDIA]["accounts"].pop(email)
    # Clean up config flows in progress
    flows_to_remove = []
    if hass.data[DATA_ALEXAMEDIA].get("config_flows"):
        for key, flow in hass.data[DATA_ALEXAMEDIA]["config_flows"].items():
            if key.startswith(email) and flow:
                _LOGGER.debug("Aborting flow %s %s", key, flow)
                flows_to_remove.append(key)
                try:
                    hass.config_entries.flow.async_abort(flow.get("flow_id"))
                except UnknownFlow:
                    pass
        for flow in flows_to_remove:
            hass.data[DATA_ALEXAMEDIA]["config_flows"].pop(flow)
    # Clean up hass.data
    if not hass.data[DATA_ALEXAMEDIA].get("accounts"):
        _LOGGER.debug("Removing accounts data and services")
        hass.data[DATA_ALEXAMEDIA].pop("accounts")
        alexa_services = hass.data[DATA_ALEXAMEDIA].get("services")
        if alexa_services:
            await alexa_services.unregister()
            hass.data[DATA_ALEXAMEDIA].pop("services")
    if hass.data[DATA_ALEXAMEDIA].get("config_flows") == {}:
        _LOGGER.debug("Removing config_flows data")
        async_dismiss_persistent_notification(
            hass, f"alexa_media_{slugify(email)}{slugify((entry.data['url'])[7:])}"
        )
        hass.data[DATA_ALEXAMEDIA].pop("config_flows")
    if not hass.data[DATA_ALEXAMEDIA]:
        _LOGGER.debug("Removing alexa_media data structure")
        if hass.data.get(DATA_ALEXAMEDIA):
            hass.data.pop(DATA_ALEXAMEDIA)
    else:
        _LOGGER.debug(
            "Unable to remove alexa_media data structure: %s",
            hass.data.get(DATA_ALEXAMEDIA),
        )
    _LOGGER.debug("Unloaded entry for %s", hide_email(email))
    return True


async def async_remove_entry(hass, entry) -> bool:
    """Handle removal of an entry."""
    email = entry.data["email"]
    obfuscated_email = hide_email(email)
    _LOGGER.debug("Removing config entry: %s", hide_email(email))
    login_obj = AlexaLogin(
        url="",
        email=email,
        password="",  # nosec
        outputpath=hass.config.path,
    )
    # Delete cookiefile
    cookiefile = hass.config.path(f".storage/{DOMAIN}.{email}.pickle")
    obfuscated_cookiefile = hass.config.path(
        f".storage/{DOMAIN}.{obfuscated_email}.pickle"
    )
    if callable(getattr(AlexaLogin, "delete_cookiefile", None)):
        try:
            await login_obj.delete_cookiefile()
            _LOGGER.debug("Cookiefile %s deleted.", obfuscated_cookiefile)
        except Exception as ex:
            _LOGGER.error(
                "delete_cookiefile() exception: %s;"
                " Manually delete cookiefile before re-adding the integration: %s",
                ex,
                obfuscated_cookiefile,
            )
    else:
        if os.path.exists(cookiefile):
            try:
                await alexapy_delete_cookie(cookiefile)
                _LOGGER.debug(
                    "Successfully deleted cookiefile: %s", obfuscated_cookiefile
                )
            except (OSError, EOFError, TypeError, AttributeError) as ex:
                _LOGGER.error(
                    "alexapy_delete_cookie() exception: %s;"
                    " Manually delete cookiefile before re-adding the integration: %s",
                    ex,
                    obfuscated_cookiefile,
                )
        else:
            _LOGGER.error("Cookiefile not found: %s", obfuscated_cookiefile)
    _LOGGER.debug("Config entry %s removed.", obfuscated_email)
    return True


async def close_connections(hass, email: str) -> None:
    """Clear open aiohttp connections for email."""
    if (
        email not in hass.data[DATA_ALEXAMEDIA]["accounts"]
        or "login_obj" not in hass.data[DATA_ALEXAMEDIA]["accounts"][email]
    ):
        return
    account_dict = hass.data[DATA_ALEXAMEDIA]["accounts"][email]
    login_obj = account_dict["login_obj"]
    await login_obj.save_cookiefile()
    await login_obj.close()
    _LOGGER.debug(
        "%s: Connection closed: %s", hide_email(email), login_obj.session.closed
    )


async def update_listener(hass, config_entry):
    """Update when config_entry options update."""
    account = config_entry.data
    email = account.get(CONF_EMAIL)
    reload_needed: bool = False
    for key, old_value in hass.data[DATA_ALEXAMEDIA]["accounts"][email][
        "options"
    ].items():
        new_value = config_entry.data.get(key)
        if new_value is not None and new_value != old_value:
            hass.data[DATA_ALEXAMEDIA]["accounts"][email]["options"][key] = new_value
            _LOGGER.debug(
                "Option %s changed from %s to %s",
                key,
                old_value,
                hass.data[DATA_ALEXAMEDIA]["accounts"][email]["options"][key],
            )
            reload_needed = True
    if reload_needed:
        await hass.config_entries.async_reload(config_entry.entry_id)
        _LOGGER.debug(
            "%s options reloaded",
            hass.data[DATA_ALEXAMEDIA]["accounts"][email],
        )


async def test_login_status(hass, config_entry, login) -> bool:
    """Test the login status and spawn requests for info."""

    _LOGGER.debug("Testing login status: %s", login.status)
    if login.status and login.status.get("login_successful"):
        return True
    account = config_entry.data
    _LOGGER.debug("Logging in: %s %s", obfuscate(account), in_progress_instances(hass))
    _LOGGER.debug("Login stats: %s", login.stats)
    message: str = (
        f"Reauthenticate {login.email} on the [Integrations](/config/integrations) page. "
    )
    if login.stats.get("login_timestamp") != datetime(1, 1, 1):
        elaspsed_time: str = str(datetime.now() - login.stats.get("login_timestamp"))
        api_calls: int = login.stats.get("api_calls")
        message += f"Relogin required after {elaspsed_time} and {api_calls} api calls."
    async_create_persistent_notification(
        hass,
        title="Alexa Media Reauthentication Required",
        message=message,
        notification_id=f"alexa_media_{slugify(login.email)}{slugify(login.url[7:])}",
    )
    flow = hass.data[DATA_ALEXAMEDIA]["config_flows"].get(
        f"{account[CONF_EMAIL]} - {account[CONF_URL]}"
    )
    if flow:
        if flow.get("flow_id") in in_progress_instances(hass):
            _LOGGER.debug("Existing config flow detected")
            return False
        _LOGGER.debug("Stopping orphaned config flow %s", flow.get("flow_id"))
        try:
            hass.config_entries.flow.async_abort(flow.get("flow_id"))
        except UnknownFlow:
            pass
        hass.data[DATA_ALEXAMEDIA]["config_flows"][
            f"{account[CONF_EMAIL]} - {account[CONF_URL]}"
        ] = None
    _LOGGER.debug("Creating new config flow to login")
    config_entry.async_start_reauth(
        hass,
        context={"source": SOURCE_REAUTH},
        data={
            CONF_EMAIL: account[CONF_EMAIL],
            CONF_PASSWORD: account[CONF_PASSWORD],
            CONF_URL: account[CONF_URL],
            CONF_DEBUG: account[CONF_DEBUG],
            CONF_INCLUDE_DEVICES: account[CONF_INCLUDE_DEVICES],
            CONF_EXCLUDE_DEVICES: account[CONF_EXCLUDE_DEVICES],
            CONF_SCAN_INTERVAL: (
                account[CONF_SCAN_INTERVAL].total_seconds()
                if isinstance(account[CONF_SCAN_INTERVAL], timedelta)
                else account[CONF_SCAN_INTERVAL]
            ),
            CONF_OTPSECRET: account.get(CONF_OTPSECRET, ""),
        },
    )
    try:
        flow_obj = config_entry.async_get_active_flows(hass, {SOURCE_REAUTH}).__next__()
        hass.data[DATA_ALEXAMEDIA]["config_flows"][
            f"{account[CONF_EMAIL]} - {account[CONF_URL]}"
        ] = flow_obj
    except StopIteration:
        _LOGGER.debug("A new config flow could not be created.")
    return False
