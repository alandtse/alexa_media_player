"""
Support to interface with Alexa Devices.

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
VERSION 1.0.0
"""
import logging

from datetime import timedelta

import voluptuous as vol

from homeassistant import util
from homeassistant.const import (
    CONF_EMAIL, CONF_PASSWORD, CONF_URL)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import track_utc_time_change
from homeassistant.helpers.discovery import load_platform
# from .config_flow import configured_instances

REQUIREMENTS = ['alexapy==0.1.0']

_CONFIGURING = []
_LOGGER = logging.getLogger(__name__)

MIN_TIME_BETWEEN_SCANS = timedelta(seconds=15)
MIN_TIME_BETWEEN_FORCED_SCANS = timedelta(seconds=1)

DOMAIN = "alexa_media"

ALEXA_COMPONENTS = [
    'media_player'
]

CONF_ACCOUNTS = 'accounts'
CONF_DEBUG = 'debug'
CONF_INCLUDE_DEVICES = 'include_devices'
CONF_EXCLUDE_DEVICES = 'exclude_devices'

ACCOUNT_CONFIG_SCHEMA = vol.Schema({
    vol.Required(CONF_EMAIL): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Required(CONF_URL): cv.string,
    vol.Optional(CONF_DEBUG, default=False): cv.boolean,
    vol.Optional(CONF_INCLUDE_DEVICES, default=[]):
        vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_EXCLUDE_DEVICES, default=[]):
        vol.All(cv.ensure_list, [cv.string]),
})

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Optional(CONF_ACCOUNTS):
            vol.All(cv.ensure_list, [ACCOUNT_CONFIG_SCHEMA]),
    }),
}, extra=vol.ALLOW_EXTRA)


def setup(hass, config, discovery_info=None):
    """Set up the Alexa domain."""
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
        hass.data[DOMAIN]['accounts'] = {}
    from alexapy import AlexaLogin

    config = config.get(DOMAIN)
    for account in config[CONF_ACCOUNTS]:
        # if account[CONF_EMAIL] in configured_instances(hass):
        #     continue

        email = account.get(CONF_EMAIL)
        password = account.get(CONF_PASSWORD)
        url = account.get(CONF_URL)

        login = AlexaLogin(url, email, password, hass.config.path,
                           account.get(CONF_DEBUG))

        testLoginStatus(hass, account, login,
                        setup_platform_callback)
    return True


async def setup_platform_callback(hass, config, login, callback_data):
    """Handle response from configurator.

    Args:
    callback_data (json): Returned data from configurator passed through
                          request_configuration and configuration_callback
    """
    _LOGGER.debug(("Status: {} got captcha: {} securitycode: {}"
                  " Claimsoption: {} VerificationCode: {}").format(
        login.status,
        callback_data.get('captcha'),
        callback_data.get('securitycode'),
        callback_data.get('claimsoption'),
        callback_data.get('verificationcode')))
    login.login(captcha=callback_data.get('captcha'),
                securitycode=callback_data.get('securitycode'),
                claimsoption=callback_data.get('claimsoption'),
                verificationcode=callback_data.get('verificationcode'))
    testLoginStatus(hass, config, login,
                    setup_platform_callback)


def request_configuration(hass, config, login, setup_platform_callback):
    """Request configuration steps from the user using the configurator."""
    configurator = hass.components.configurator

    async def configuration_callback(callback_data):
        """Handle the submitted configuration."""
        hass.async_add_job(setup_platform_callback, hass, config,
                           login, callback_data)
    status = login.status
    email = login.get_email()
    # Get Captcha
    if (status and 'captcha_image_url' in status and
            status['captcha_image_url'] is not None):
        config_id = configurator.request_config(
            "Alexa Media Player - Captcha - {}".format(email),
            configuration_callback,
            description=('Please enter the text for the captcha.'
                         ' Please enter anything if the image is missing.'
                         ),
            description_image=status['captcha_image_url'],
            submit_caption="Confirm",
            fields=[{'id': 'captcha', 'name': 'Captcha'}]
        )
    elif (status and 'securitycode_required' in status and
            status['securitycode_required']):  # Get 2FA code
        config_id = configurator.request_config(
            "Alexa Media Player - 2FA - {}".format(email),
            configuration_callback,
            description=('Please enter your Two-Factor Security code.'),
            submit_caption="Confirm",
            fields=[{'id': 'securitycode', 'name': 'Security Code'}]
        )
    elif (status and 'claimspicker_required' in status and
            status['claimspicker_required']):  # Get picker method
        options = status['claimspicker_message']
        config_id = configurator.request_config(
            "Alexa Media Player - Verification Method - {}".format(email),
            configuration_callback,
            description=('Please select the verification method. '
                         '(e.g., sms or email).<br />{}').format(
                         options
                         ),
            submit_caption="Confirm",
            fields=[{'id': 'claimsoption', 'name': 'Option'}]
        )
    elif (status and 'verificationcode_required' in status and
            status['verificationcode_required']):  # Get picker method
        config_id = configurator.request_config(
            "Alexa Media Player - Verification Code - {}".format(email),
            configuration_callback,
            description=('Please enter received verification code.'),
            submit_caption="Confirm",
            fields=[{'id': 'verificationcode', 'name': 'Verification Code'}]
        )
    else:  # Check login
        config_id = configurator.request_config(
            "Alexa Media Player - Begin - {}".format(email),
            configuration_callback,
            description=('Please hit confirm to begin login attempt.'),
            submit_caption="Confirm",
            fields=[]
        )
    _CONFIGURING.append(config_id)
    if (len(_CONFIGURING) > 0 and 'error_message' in status
            and status['error_message']):
        configurator.notify_errors(  # use sync to delay next pop
            _CONFIGURING[len(_CONFIGURING)-1], status['error_message'])
    if (len(_CONFIGURING) > 1):
        configurator.async_request_done(_CONFIGURING.pop(0))


def testLoginStatus(hass, config, login,
                    setup_platform_callback):
    """Test the login status and spawn requests for info."""
    if 'login_successful' in login.status and login.status['login_successful']:
        _LOGGER.debug("Setting up Alexa devices")
        (hass.data[DOMAIN]
                  ['accounts']
                  [login.get_email()]) = {
                    'login_obj': login,
                    'devices': {
                                'media_player': {}
                               }
                    }
        hass.async_add_job(setup_alexa, hass, config,
                           login)
        return
    elif ('captcha_required' in login.status and
          login.status['captcha_required']):
        _LOGGER.debug("Creating configurator to request captcha")
    elif ('securitycode_required' in login.status and
            login.status['securitycode_required']):
        _LOGGER.debug("Creating configurator to request 2FA")
    elif ('claimspicker_required' in login.status and
            login.status['claimspicker_required']):
        _LOGGER.debug("Creating configurator to select verification option")
    elif ('verificationcode_required' in login.status and
            login.status['verificationcode_required']):
        _LOGGER.debug("Creating configurator to enter verification code")
    elif ('login_failed' in login.status and
            login.status['login_failed']):
        _LOGGER.debug("Creating configurator to start new login attempt")
    hass.async_add_job(request_configuration, hass, config, login,
                       setup_platform_callback
                       )


def setup_alexa(hass, config, login_obj):
    """Set up a alexa api based on host parameter."""
    alexa_clients = (hass.data[DOMAIN]
                              ['accounts']
                              [login_obj.get_email()]
                              ['devices']['media_player'])

    # alexa_sessions = {}
    track_utc_time_change(hass, lambda now: update_devices(), second=30)
    include = config.get(CONF_INCLUDE_DEVICES)
    exclude = config.get(CONF_EXCLUDE_DEVICES)

    @util.Throttle(MIN_TIME_BETWEEN_SCANS, MIN_TIME_BETWEEN_FORCED_SCANS)
    def update_devices():
        """Update the devices objects."""
        from alexapy import AlexaAPI
        devices = AlexaAPI.get_devices(login_obj)
        bluetooth = AlexaAPI.get_bluetooth(login_obj)

        if ((devices is None or bluetooth is None)
                and len(_CONFIGURING) == 0):
            _LOGGER.debug("Alexa API disconnected; attempting to relogin")
            login_obj.login_with_cookie()
            testLoginStatus(hass, config, login_obj, setup_platform_callback)

        new_alexa_clients = []  # list of newly discovered device jsons
        available_client_ids = []  # list of known serial numbers
        for device in devices:
            if include and device['accountName'] not in include:
                continue
            elif exclude and device['accountName'] in exclude:
                continue

            for b_state in bluetooth['bluetoothStates']:
                if device['serialNumber'] == b_state['deviceSerialNumber']:
                    device['bluetooth_state'] = b_state

            available_client_ids.append(device['serialNumber'])
            (hass.data[DOMAIN]
                      ['accounts']
                      [login_obj.get_email()]
                      ['devices']
                      ['media_player']
                      [device['serialNumber']]) = device

            if device['serialNumber'] not in alexa_clients:
                new_alexa_clients.append(device)

        if new_alexa_clients:
            for component in ALEXA_COMPONENTS:
                load_platform(hass, component, DOMAIN, {}, config)

    update_devices()
    hass.data[DOMAIN]['update_devices'] = update_devices
    for component in ALEXA_COMPONENTS:
        load_platform(hass, component, DOMAIN, {}, config)

    # Clear configurator. We delay till here to avoid leaving a modal orphan
    global _CONFIGURING
    for config_id in _CONFIGURING:
        configurator = hass.components.configurator
        configurator.async_request_done(config_id)
    _CONFIGURING = []
    return True
