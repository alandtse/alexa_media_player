#!/usr/bin/env python
# -*- coding: utf-8 -*-
#  SPDX-License-Identifier: Apache-2.0
"""
Support to interface with Alexa Devices.

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""
import logging
from typing import Optional, Text

import voluptuous as vol

from alexapy import WebsocketEchoClient
from homeassistant import util
from homeassistant.const import (CONF_EMAIL, CONF_NAME, CONF_PASSWORD,
                                 CONF_SCAN_INTERVAL, CONF_URL,
                                 EVENT_HOMEASSISTANT_STOP)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.event import async_call_later

from .const import (ALEXA_COMPONENTS, ATTR_EMAIL, CONF_ACCOUNTS, CONF_DEBUG,
                    CONF_EXCLUDE_DEVICES, CONF_INCLUDE_DEVICES,
                    DATA_ALEXAMEDIA, DOMAIN, MIN_TIME_BETWEEN_FORCED_SCANS,
                    MIN_TIME_BETWEEN_SCANS, SCAN_INTERVAL,
                    SERVICE_UPDATE_LAST_CALLED, STARTUP, __version__)

# from .config_flow import configured_instances

_LOGGER = logging.getLogger(__name__)


ACCOUNT_CONFIG_SCHEMA = vol.Schema({
    vol.Required(CONF_EMAIL): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Required(CONF_URL): cv.string,
    vol.Optional(CONF_DEBUG, default=False): cv.boolean,
    vol.Optional(CONF_INCLUDE_DEVICES, default=[]):
        vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_EXCLUDE_DEVICES, default=[]):
        vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_SCAN_INTERVAL, default=SCAN_INTERVAL):
    cv.time_period,
})

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Optional(CONF_ACCOUNTS):
            vol.All(cv.ensure_list, [ACCOUNT_CONFIG_SCHEMA]),
    }),
}, extra=vol.ALLOW_EXTRA)

LAST_CALL_UPDATE_SCHEMA = vol.Schema({
    vol.Optional(ATTR_EMAIL, default=[]):
        vol.All(cv.ensure_list, [cv.string]),
})


def hide_email(email):
    """Obfuscate email."""
    part = email.split('@')
    return "{}{}{}@{}{}{}".format(part[0][0],
                                  "*" * (len(part[0]) - 2),
                                  part[0][-1],
                                  part[1][0],
                                  "*" * (len(part[1]) - 2),
                                  part[1][-1]
)


def hide_serial(item):
    """Obfuscate serial."""
    if item is None:
        return ""
    if isinstance(item, dict):
        response = item.copy()
        for key, value in item.items():
            if (isinstance(value, dict) or isinstance(value, list) or
                    key in ['deviceSerialNumber', 'serialNumber',
                            'destinationUserId']):
                response[key] = hide_serial(value)
    elif isinstance(item, str):
        response = "{}{}{}".format(item[0],
                                   "*" * (len(item) - 4),
                                   item[-3:])
    elif isinstance(item, list):
        response = []
        for list_item in item:
            if isinstance(list_item, dict):
                response.append(hide_serial(list_item))
            else:
                response.append(list_item)
    return response


async def async_setup(hass, config, discovery_info=None):
    """Set up the Alexa domain."""
    async def close_alexa_media(event) -> None:
        """Clean up Alexa connections."""
        _LOGGER.debug("Received shutdown request: %s", event)
        for email, account_dict in (hass.data
                                    [DATA_ALEXAMEDIA]['accounts'].items()):
            login_obj = account_dict['login_obj']
            if not login_obj._session.closed:
                if login_obj._session._connector_owner:
                    await login_obj._session._connector.close()
                login_obj._session._connector = None
            _LOGGER.debug("%s: Connection closed: %s",
                          hide_email(email),
                          login_obj._session.closed)
    if DATA_ALEXAMEDIA not in hass.data:
        hass.data[DATA_ALEXAMEDIA] = {}
        hass.data[DATA_ALEXAMEDIA]['accounts'] = {}
    from alexapy import AlexaLogin, __version__ as alexapy_version
    _LOGGER.info(STARTUP)
    _LOGGER.info("Loaded alexapy==%s", alexapy_version)
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, close_alexa_media)
    domainconfig = config.get(DOMAIN)
    for account in domainconfig[CONF_ACCOUNTS]:
        # if account[CONF_EMAIL] in configured_instances(hass):
        #     continue

        email = account.get(CONF_EMAIL)
        password = account.get(CONF_PASSWORD)
        url = account.get(CONF_URL)
        hass.data[DATA_ALEXAMEDIA]['accounts'][email] = {"config": []}
        login = AlexaLogin(url, email, password, hass.config.path,
                           account.get(CONF_DEBUG))
        (hass.data[DATA_ALEXAMEDIA]['accounts'][email]['login_obj']) = login
        await login.login_with_cookie()
        await test_login_status(hass, account, login,
                                setup_platform_callback)
    return True


async def setup_platform_callback(hass, config, login, callback_data):
    """Handle response from configurator.

    Args:
    callback_data (json): Returned data from configurator passed through
                          request_configuration and configuration_callback
    """
    _LOGGER.debug(("Configurator closed for Status: %s\n"
                   " got captcha: %s securitycode: %s"
                   " Claimsoption: %s AuthSelectOption: %s "
                   " VerificationCode: %s"),
                  login.status,
                  callback_data.get('captcha'),
                  callback_data.get('securitycode'),
                  callback_data.get('claimsoption'),
                  callback_data.get('authselectoption'),
                  callback_data.get('verificationcode'))
    await login.login(data=callback_data)
    await test_login_status(hass, config, login,
                            setup_platform_callback)


async def request_configuration(hass, config, login, setup_platform_callback):
    """Request configuration steps from the user using the configurator."""
    async def configuration_callback(callback_data):
        """Handle the submitted configuration."""
        await hass.async_add_job(setup_platform_callback, hass, config,
                                 login, callback_data)

    configurator = hass.components.configurator
    status = login.status
    email = login.email
    # links = ""
    footer = ""
    if 'error_message' in status and status['error_message']:
        footer = ('\n<b>NOTE: Actual Amazon error message in red below. '
                  'Remember password will be provided automatically'
                  ' and Amazon error message normally appears first!</b>')
    # if login.links:
    #     links = '\n\nGo to link with link# (e.g. link0)\n' + login.links
    # Get Captcha
    if (status and 'captcha_image_url' in status and
            status['captcha_image_url'] is not None):
        config_id = configurator.async_request_config(
            "Alexa Media Player - Captcha - {}".format(email),
            configuration_callback,
            description=('Please enter the text for the captcha.'
                         ' Please hit confirm to reload image.'
                         # + links
                         + footer
                         ),
            description_image=status['captcha_image_url'],
            submit_caption="Confirm",
            fields=[{'id': 'captcha', 'name': 'Captcha'}]
        )
    elif (status and 'securitycode_required' in status and
          status['securitycode_required']):  # Get 2FA code
        config_id = configurator.async_request_config(
            "Alexa Media Player - 2FA - {}".format(email),
            configuration_callback,
            description=('Please enter your Two-Factor Security code.'
                         # + links
                         + footer),
            submit_caption="Confirm",
            fields=[{'id': 'securitycode', 'name': 'Security Code'}]
        )
    elif (status and 'claimspicker_required' in status and
          status['claimspicker_required']):  # Get picker method
        options = status['claimspicker_message']
        if options:
            config_id = configurator.async_request_config(
                "Alexa Media Player - Verification Method - {}".format(email),
                configuration_callback,
                description=('Please select the verification method. '
                             '(e.g., `sms` or `email`).\n{}'.format(options)
                             # + links
                             + footer),
                submit_caption="Confirm",
                fields=[{'id': 'claimsoption', 'name': 'Option'}]
            )
        else:
            await configuration_callback({})
    elif (status and 'authselect_required' in status and
          status['authselect_required']):  # Get picker method
        options = status['authselect_message']
        if options:
            config_id = configurator.async_request_config(
                "Alexa Media Player - OTP Method - {}".format(email),
                configuration_callback,
                description=('Please select the OTP method. '
                             '(e.g., `0`, `1`).<br />{}'.format(options)
                             # + links
                             + footer),
                submit_caption="Confirm",
                fields=[{'id': 'authselectoption', 'name': 'Option'}]
            )
        else:
            await configuration_callback({})
    elif (status and 'verificationcode_required' in status and
          status['verificationcode_required']):  # Get picker method
        config_id = configurator.request_config(
            "Alexa Media Player - Verification Code - {}".format(email),
            configuration_callback,
            description=('Please enter received verification code.'
                         # + links
                         + footer),
            submit_caption="Confirm",
            fields=[{'id': 'verificationcode', 'name': 'Verification Code'}]
        )
    else:  # Check login
        config_id = configurator.async_request_config(
            "Alexa Media Player - Begin - {}".format(email),
            configuration_callback,
            description=('Please hit confirm to begin login attempt.'),
            submit_caption="Confirm",
            fields=[]
        )
    hass.data[DATA_ALEXAMEDIA]['accounts'][email]['config'].append(config_id)
    if 'error_message' in status and status['error_message']:
        configurator.async_notify_errors(
            config_id,
            status['error_message'])
    if len(hass.data[DATA_ALEXAMEDIA]['accounts'][email]['config']) > 1:
        configurator.async_request_done(
            (hass.data[DATA_ALEXAMEDIA]['accounts'][email]['config']).pop(0))


async def test_login_status(hass, config, login,
                            setup_platform_callback) -> None:
    """Test the login status and spawn requests for info."""
    _LOGGER.debug("Testing login status: %s", login.status)
    if 'login_successful' in login.status and login.status['login_successful']:
        _LOGGER.debug("Setting up Alexa devices for %s",
                      hide_email(login.email))
        await hass.async_add_job(setup_alexa, hass, config,
                                 login)
        return
    if ('captcha_required' in login.status and
            login.status['captcha_required']):
        _LOGGER.debug("Creating configurator to request captcha")
    elif ('securitycode_required' in login.status and
          login.status['securitycode_required']):
        _LOGGER.debug("Creating configurator to request 2FA")
    elif ('claimspicker_required' in login.status and
          login.status['claimspicker_required']):
        _LOGGER.debug("Creating configurator to select verification option")
    elif ('authselect_required' in login.status and
          login.status['authselect_required']):
        _LOGGER.debug("Creating configurator to select OTA option")
    elif ('verificationcode_required' in login.status and
          login.status['verificationcode_required']):
        _LOGGER.debug("Creating configurator to enter verification code")
    elif ('login_failed' in login.status and
          login.status['login_failed']):
        _LOGGER.debug("Creating configurator to start new login attempt")
    await hass.async_add_job(request_configuration, hass, config, login,
                             setup_platform_callback)


async def setup_alexa(hass, config, login_obj):
    """Set up a alexa api based on host parameter."""
    @util.Throttle(MIN_TIME_BETWEEN_SCANS, MIN_TIME_BETWEEN_FORCED_SCANS)
    async def update_devices(login_obj):
        """Ping Alexa API to identify all devices, bluetooth, and last called device.

        This will add new devices and services when discovered. By default this
        runs every SCAN_INTERVAL seconds unless another method calls it. if
        websockets is connected, it will return immediately unless
        'new_devices' has been set to True.
        While throttled at MIN_TIME_BETWEEN_SCANS, care should be taken to
        reduce the number of runs to avoid flooding. Slow changing states
        should be checked here instead of in spawned components like
        media_player since this object is one per account.
        Each AlexaAPI call generally results in two webpage requests.
        """
        from alexapy import AlexaAPI
        email: Text = login_obj.email
        existing_serials = (hass.data[DATA_ALEXAMEDIA]
                            ['accounts']
                            [email]
                            ['entities']
                            ['media_player'].keys() if 'entities' in (
                                hass.data[DATA_ALEXAMEDIA]
                                ['accounts']
                                [email])
                            else [])
        existing_entities = (hass.data[DATA_ALEXAMEDIA]
                             ['accounts']
                             [email]
                             ['entities']
                             ['media_player'].values())
        if ('websocket' in hass.data[DATA_ALEXAMEDIA]['accounts'][email]
            and hass.data[DATA_ALEXAMEDIA]['accounts'][email]['websocket']
                and not (hass.data[DATA_ALEXAMEDIA]
                         ['accounts'][email]['new_devices'])):
            return
        hass.data[DATA_ALEXAMEDIA]['accounts'][email]['new_devices'] = False
        devices = await AlexaAPI.get_devices(login_obj)
        bluetooth = await AlexaAPI.get_bluetooth(login_obj)
        preferences = await AlexaAPI.get_device_preferences(login_obj)
        dnd = await AlexaAPI.get_dnd_state(login_obj)
        _LOGGER.debug("%s: Found %s devices, %s bluetooth",
                      hide_email(email),
                      len(devices) if devices is not None else '',
                      len(bluetooth) if bluetooth is not None else '')
        if ((devices is None or bluetooth is None)
                and not (hass.data[DATA_ALEXAMEDIA]
                         ['accounts'][email]['config'])):
            _LOGGER.debug("%s: Alexa API disconnected; attempting to relogin",
                          hide_email(email))
            await login_obj.login()
            await test_login_status(hass,
                                    config, login_obj, setup_platform_callback)
            return

        new_alexa_clients = []  # list of newly discovered device names
        exclude_filter = []
        include_filter = []
        for device in devices:
            if include and device['accountName'] not in include:
                include_filter.append(device['accountName'])
                if 'appDeviceList' in device:
                    for app in device['appDeviceList']:
                        (hass.data[DATA_ALEXAMEDIA]
                         ['accounts']
                         [email]
                         ['excluded']
                         [app['serialNumber']]) = device
                (hass.data[DATA_ALEXAMEDIA]
                 ['accounts']
                 [email]
                 ['excluded']
                 [device['serialNumber']]) = device
                continue
            elif exclude and device['accountName'] in exclude:
                exclude_filter.append(device['accountName'])
                if 'appDeviceList' in device:
                    for app in device['appDeviceList']:
                        (hass.data[DATA_ALEXAMEDIA]
                         ['accounts']
                         [email]
                         ['excluded']
                         [app['serialNumber']]) = device
                (hass.data[DATA_ALEXAMEDIA]
                 ['accounts']
                 [email]
                 ['excluded']
                 [device['serialNumber']]) = device
                continue

            if 'bluetoothStates' in bluetooth:
                for b_state in bluetooth['bluetoothStates']:
                    if device['serialNumber'] == b_state['deviceSerialNumber']:
                        device['bluetooth_state'] = b_state

            if 'devicePreferences' in preferences:
                for dev in preferences['devicePreferences']:
                    if dev['deviceSerialNumber'] == device['serialNumber']:
                        device['locale'] = dev['locale']
                        _LOGGER.debug("Locale %s found for %s",
                                      device['locale'],
                                      hide_serial(device['serialNumber']))

            if 'doNotDisturbDeviceStatusList' in dnd:
                for dev in dnd['doNotDisturbDeviceStatusList']:
                    if dev['deviceSerialNumber'] == device['serialNumber']:
                        device['dnd'] = dev['enabled']
                        _LOGGER.debug("DND %s found for %s",
                                      device['dnd'],
                                      hide_serial(device['serialNumber']))

            (hass.data[DATA_ALEXAMEDIA]
             ['accounts']
             [email]
             ['devices']
             ['media_player']
             [device['serialNumber']]) = device

            if device['serialNumber'] not in existing_serials:
                new_alexa_clients.append(device['accountName'])
        _LOGGER.debug("%s: Existing: %s New: %s;"
                      " Filtered out by not being in include: %s "
                      "or in exclude: %s",
                      hide_email(email),
                      list(existing_entities),
                      new_alexa_clients,
                      include_filter,
                      exclude_filter)

        if new_alexa_clients:
            cleaned_config = config.copy()
            cleaned_config.pop(CONF_SCAN_INTERVAL, None)
            # CONF_SCAN_INTERVAL causes a json error in the recorder because it
            # is a timedelta object.
            cleaned_config.pop(CONF_PASSWORD, None)
            # CONF_PASSWORD contains sensitive info which is no longer needed
            for component in ALEXA_COMPONENTS:
                hass.async_create_task(
                    async_load_platform(hass,
                                        component,
                                        DOMAIN,
                                        {CONF_NAME: DOMAIN,
                                         "config": cleaned_config},
                                        config))

        # Process last_called data to fire events
        await update_last_called(login_obj)
        scan_interval = config.get(CONF_SCAN_INTERVAL)
        async_call_later(hass, scan_interval.total_seconds(), lambda _:
                         hass.async_create_task(
                            update_devices(login_obj,
                                           no_throttle=True)))

    async def update_last_called(login_obj, last_called=None):
        """Update the last called device for the login_obj.

        This will store the last_called in hass.data and also fire an event
        to notify listeners.
        """
        from alexapy import AlexaAPI
        if last_called:
            last_called = last_called
        else:
            last_called = await AlexaAPI.get_last_device_serial(login_obj)
        _LOGGER.debug("%s: Updated last_called: %s",
                      hide_email(email),
                      hide_serial(last_called))
        stored_data = hass.data[DATA_ALEXAMEDIA]['accounts'][email]
        if (('last_called' in stored_data and
             last_called != stored_data['last_called']) or
                ('last_called' not in stored_data and
                 last_called is not None)):
            _LOGGER.debug("%s: last_called changed: %s to %s",
                          hide_email(email),
                          hide_serial(stored_data['last_called'] if
                                      'last_called' in stored_data else None),
                          hide_serial(last_called))
            hass.bus.async_fire(
                ('{}_{}'.format(DOMAIN,
                                hide_email(email)))[0:32],
                {'last_called_change': last_called})
        (hass.data[DATA_ALEXAMEDIA]
         ['accounts']
         [email]
         ['last_called']) = last_called

    async def update_bluetooth_state(login_obj, device_serial):
        """Update the bluetooth state on ws bluetooth event."""
        from alexapy import AlexaAPI
        bluetooth = await AlexaAPI.get_bluetooth(login_obj)
        device = (hass.data[DATA_ALEXAMEDIA]
                  ['accounts']
                  [email]
                  ['devices']
                  ['media_player']
                  [device_serial])

        if 'bluetoothStates' in bluetooth:
            for b_state in bluetooth['bluetoothStates']:
                if device_serial == b_state['deviceSerialNumber']:
                    # _LOGGER.debug("%s: setting value for: %s to %s",
                    #               hide_email(email),
                    #               hide_serial(device_serial),
                    #               hide_serial(b_state))
                    device['bluetooth_state'] = b_state
                    return device['bluetooth_state']
        _LOGGER.debug("%s: get_bluetooth for: %s failed with %s",
                      hide_email(email),
                      hide_serial(device_serial),
                      hide_serial(bluetooth))
        return None

    async def last_call_handler(call):
        """Handle last call service request.

        Args:
        call.ATTR_EMAIL: List of case-sensitive Alexa email addresses. If None
                         all accounts are updated.
        """
        requested_emails = call.data.get(ATTR_EMAIL)
        _LOGGER.debug("Service update_last_called for: %s", requested_emails)
        for email, account_dict in (hass.data
                                    [DATA_ALEXAMEDIA]['accounts'].items()):
            if requested_emails and email not in requested_emails:
                continue
            login_obj = account_dict['login_obj']
            await update_last_called(login_obj)

    async def ws_connect() -> WebsocketEchoClient:
        """Open WebSocket connection.

        This will only attempt one login before failing.
        """
        websocket: Optional[WebsocketEchoClient] = None
        try:
            websocket = WebsocketEchoClient(login_obj,
                                            ws_handler,
                                            ws_open_handler,
                                            ws_close_handler,
                                            ws_error_handler)
            _LOGGER.debug("%s: Websocket created: %s", hide_email(email),
                          websocket)
            await websocket.async_run()
        except BaseException as exception_:
            _LOGGER.debug("%s: Websocket creation failed: %s",
                          hide_email(email),
                          exception_)
        return websocket

    async def ws_handler(message_obj):
        """Handle websocket messages.

        This allows push notifications from Alexa to update last_called
        and media state.
        """
        command = (message_obj.json_payload['command']
                   if isinstance(message_obj.json_payload, dict) and
                   'command' in message_obj.json_payload
                   else None)
        json_payload = (message_obj.json_payload['payload']
                        if isinstance(message_obj.json_payload, dict) and
                        'payload' in message_obj.json_payload
                        else None)
        existing_serials = (hass.data[DATA_ALEXAMEDIA]
                            ['accounts']
                            [email]
                            ['entities']
                            ['media_player'].keys() if 'entities' in (
                                hass.data[DATA_ALEXAMEDIA]
                                ['accounts']
                                [email])
                            else [])
        if command and json_payload:
            _LOGGER.debug("%s: Received websocket command: %s : %s",
                          hide_email(email),
                          command, hide_serial(json_payload))
            serial = None
            if command == 'PUSH_ACTIVITY':
                #  Last_Alexa Updated
                if (json_payload
                        ['key']
                        ['entryId']).find('#') != -1:
                    serial = (json_payload
                              ['key']
                              ['entryId']).split('#')[2]
                    last_called = {
                        'serialNumber': serial,
                        'timestamp': json_payload['timestamp']
                    }
                if (serial and serial in existing_serials):
                    await update_last_called(login_obj,
                                             last_called)
                hass.bus.async_fire(
                    ('{}_{}'.format(DOMAIN,
                                    hide_email(email)))[0:32],
                    {'push_activity': json_payload})
            elif command == 'PUSH_AUDIO_PLAYER_STATE':
                # Player update
                serial = (json_payload['dopplerId']['deviceSerialNumber'])
                if (serial and serial in existing_serials):
                    _LOGGER.debug("Updating media_player: %s",
                                  hide_serial(json_payload))
                    hass.bus.async_fire(
                        ('{}_{}'.format(DOMAIN,
                                        hide_email(email)))[0:32],
                        {'player_state': json_payload})
            elif command == 'PUSH_VOLUME_CHANGE':
                # Player volume update
                serial = (json_payload['dopplerId']['deviceSerialNumber'])
                if (serial and serial in existing_serials):
                    _LOGGER.debug("Updating media_player volume: %s",
                                  hide_serial(json_payload))
                    hass.bus.async_fire(
                        ('{}_{}'.format(DOMAIN,
                                        hide_email(email)))[0:32],
                        {'player_state': json_payload})
            elif command == 'PUSH_DOPPLER_CONNECTION_CHANGE':
                # Player availability update
                serial = (json_payload['dopplerId']['deviceSerialNumber'])
                if (serial and serial in existing_serials):
                    _LOGGER.debug("Updating media_player availability %s",
                                  hide_serial(json_payload))
                    hass.bus.async_fire(
                        ('{}_{}'.format(DOMAIN,
                                        hide_email(email)))[0:32],
                        {'player_state': json_payload})
            elif command == 'PUSH_BLUETOOTH_STATE_CHANGE':
                # Player bluetooth update
                serial = (json_payload['dopplerId']['deviceSerialNumber'])
                bt_event = json_payload['bluetoothEvent']
                bt_success = json_payload['bluetoothEventSuccess']
                if (serial and serial in existing_serials and
                    bt_success and bt_event and bt_event in [
                        'DEVICE_CONNECTED',
                        'DEVICE_DISCONNECTED']):
                    _LOGGER.debug("Updating media_player bluetooth %s",
                                  hide_serial(json_payload))
                    bluetooth_state = await update_bluetooth_state(login_obj,
                                                                   serial)
                    # _LOGGER.debug("bluetooth_state %s",
                    #               hide_serial(bluetooth_state))
                    if bluetooth_state:
                        hass.bus.async_fire(
                            ('{}_{}'.format(DOMAIN,
                                            hide_email(email)))[0:32],
                            {'bluetooth_change': bluetooth_state})
            elif command == 'PUSH_MEDIA_QUEUE_CHANGE':
                # Player availability update
                serial = (json_payload['dopplerId']['deviceSerialNumber'])
                if (serial and serial in existing_serials):
                    _LOGGER.debug("Updating media_player queue %s",
                                  hide_serial(json_payload))
                    hass.bus.async_fire(
                        ('{}_{}'.format(DOMAIN,
                                        hide_email(email)))[0:32],
                        {'queue_state': json_payload})
            if (serial and serial not in existing_serials
                    and serial not in (hass.data[DATA_ALEXAMEDIA]
                                       ['accounts']
                                       [email]
                                       ['excluded'].keys())):
                _LOGGER.debug("Discovered new media_player %s", serial)
                (hass.data[DATA_ALEXAMEDIA]
                 ['accounts'][email]['new_devices']) = True
                await update_devices(login_obj, no_throttle=True)

    async def ws_open_handler():
        """Handle websocket open."""
        email: Text = login_obj.email
        _LOGGER.debug("%s: Websocket succesfully connected",
                      hide_email(email))
        (hass.data[DATA_ALEXAMEDIA]
         ['accounts'][email]['websocketerror']) = 0  # set errors to 0

    async def ws_close_handler():
        """Handle websocket close.

        This should attempt to reconnect up to 5 times
        """
        from asyncio import sleep
        email: Text = login_obj.email
        errors: int = (hass.data
                       [DATA_ALEXAMEDIA]['accounts'][email]['websocketerror'])
        delay: int = 5 * 2 ** errors
        if (errors < 5):
            _LOGGER.debug("%s: Websocket closed; reconnect #%i in %is",
                          hide_email(email),
                          errors,
                          delay)
            await sleep(delay)
            if (not (hass.data
                     [DATA_ALEXAMEDIA]['accounts'][email]['websocket'])):
                (hass.data[DATA_ALEXAMEDIA]['accounts']
                 [email]['websocket']) = await ws_connect()
        else:
            _LOGGER.debug("%s: Websocket closed; retries exceeded; polling",
                          hide_email(email))
            (hass.data[DATA_ALEXAMEDIA]['accounts']
             [email]['websocket']) = None
            await update_devices(login_obj, no_throttle=True)

    async def ws_error_handler(message):
        """Handle websocket error.

        This currently logs the error.  In the future, this should invalidate
        the websocket and determine if a reconnect should be done. By
        specification, websockets will issue a close after every error.
        """
        email = login_obj.email
        errors = (hass.data[DATA_ALEXAMEDIA]
                  ['accounts'][email]['websocketerror'])
        _LOGGER.debug("%s: Received websocket error #%i %s",
                      hide_email(email),
                      errors,
                      message)
        (hass.data[DATA_ALEXAMEDIA]['accounts'][email]['websocket']) = None
        (hass.data[DATA_ALEXAMEDIA]
         ['accounts'][email]['websocketerror']) = errors + 1
    include = config.get(CONF_INCLUDE_DEVICES)
    exclude = config.get(CONF_EXCLUDE_DEVICES)
    scan_interval: int = config.get(CONF_SCAN_INTERVAL)
    email: Text = login_obj.email
    if 'devices' not in hass.data[DATA_ALEXAMEDIA]['accounts'][email]:
        (hass.data[DATA_ALEXAMEDIA]['accounts'][email]
         ['devices']) = {'media_player': {}}
    if 'excluded' not in hass.data[DATA_ALEXAMEDIA]['accounts'][email]:
        (hass.data[DATA_ALEXAMEDIA]['accounts'][email]
         ['excluded']) = {}
    if 'entities' not in hass.data[DATA_ALEXAMEDIA]['accounts'][email]:
        (hass.data[DATA_ALEXAMEDIA]['accounts'][email]
         ['entities']) = {'media_player': {}}
        (hass.data[DATA_ALEXAMEDIA]
         ['accounts'][email]['new_devices']) = True  # force initial update
    (hass.data[DATA_ALEXAMEDIA]['accounts'][email]['websocket']) = \
        await ws_connect()
    await update_devices(login_obj, no_throttle=True)
    hass.services.async_register(DOMAIN, SERVICE_UPDATE_LAST_CALLED,
                                 last_call_handler,
                                 schema=LAST_CALL_UPDATE_SCHEMA)

    # Clear configurator. We delay till here to avoid leaving a modal orphan
    for config_id in hass.data[DATA_ALEXAMEDIA]['accounts'][email]['config']:
        configurator = hass.components.configurator
        configurator.async_request_done(config_id)
    hass.data[DATA_ALEXAMEDIA]['accounts'][email]['config'] = []
    return True
