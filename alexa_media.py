"""
Support to interface with Alexa Devices.

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
VERSION 1.0.0
"""
import logging

from datetime import timedelta

import requests
import voluptuous as vol

from homeassistant import util
from homeassistant.const import (
    CONF_EMAIL, CONF_PASSWORD, CONF_URL)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import track_utc_time_change
from homeassistant.helpers.discovery import load_platform
# from .config_flow import configured_instances

_CONFIGURING = []
_LOGGER = logging.getLogger(__name__)

REQUIREMENTS = ['beautifulsoup4==4.6.0', 'simplejson==3.16.0']

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


class AlexaLogin():
    """Class to handle login connection to Alexa. This class will not reconnect.

    Args:
    url (string): Localized Amazon domain (e.g., amazon.com)
    email (string): Amazon login account
    password (string): Password for Amazon login account
    outputpath (string): Local path with write access for storing files
    debug (boolean): Enable additional debugging including debug file creation
    """

    def __init__(self, url, email, password, outputpath, debug=False):
        """Set up initial connection and log in."""
        ALEXA_DATA = "alexa_media"
        self._url = url
        self._email = email
        self._password = password
        self._session = None
        self._data = None
        self.status = {}
        self._cookiefile = outputpath("{}.{}.pickle".format(ALEXA_DATA, email))
        self._debugpost = outputpath("{}{}post.html".format(ALEXA_DATA, email))
        self._debugget = outputpath("{}{}get.html".format(ALEXA_DATA, email))
        self._lastreq = None
        self._debug = debug

        self.login_with_cookie()

    def get_email(self):
        """Return email for this Login."""
        return self._email

    def login_with_cookie(self):
        """Attempt to login after loading cookie."""
        import pickle
        cookies = None

        if (self._cookiefile):
            try:
                _LOGGER.debug(
                    "Trying cookie from file {}".format(
                        self._cookiefile))
                with open(self._cookiefile, 'rb') as myfile:
                    cookies = pickle.load(myfile)
                    _LOGGER.debug("cookie loaded: {}".format(cookies))
            except Exception as ex:
                template = ("An exception of type {0} occurred."
                            " Arguments:\n{1!r}")
                message = template.format(type(ex).__name__, ex.args)
                _LOGGER.debug(
                    "Error loading pickled cookie from {}: {}".format(
                        self._cookiefile, message))

        self.login(cookies=cookies)

    def reset_login(self):
        """Remove data related to existing login."""
        self._session = None
        self._data = None
        self._lastreq = None
        self.status = {}
        import os
        if ((self._cookiefile) and os.path.exists(self._cookiefile)):
            try:
                _LOGGER.debug(
                    "Trying to delete cookie file {}".format(
                        self._cookiefile))
                os.remove(self._cookiefile)
            except Exception as ex:
                template = ("An exception of type {0} occurred."
                            " Arguments:\n{1!r}")
                message = template.format(type(ex).__name__, ex.args)
                _LOGGER.debug(
                    "Error deleting cookie {}: {}".format(
                        self._cookiefile, message))

    def get_inputs(self, soup, searchfield={'name': 'signIn'}):
        """Parse soup for form with searchfield."""
        data = {}
        form = soup.find('form', searchfield)
        for field in form.find_all('input'):
            try:
                data[field['name']] = ""
                data[field['name']] = field['value']
            except:  # noqa: E722 pylint: disable=bare-except
                pass
        return data

    def test_loggedin(self, cookies=None):
        """Function that will test the connection is logged in.

        Attempts to get authenticaton and compares to expected login email
        Returns false if unsuccesful getting json or the emails don't match
        """
        if self._session is None:
            '''initiate session'''

            self._session = requests.Session()

            '''define session headers'''
            self._session.headers = {
                'User-Agent': ('Mozilla/5.0 (Windows NT 6.3; Win64; x64) '
                               'AppleWebKit/537.36 (KHTML, like Gecko) '
                               'Chrome/68.0.3440.106 Safari/537.36'),
                'Accept': ('text/html,application/xhtml+xml, '
                           'application/xml;q=0.9,*/*;q=0.8'),
                'Accept-Language': '*'
            }
            self._session.cookies = cookies

        get_resp = self._session.get('https://alexa.' + self._url +
                                     '/api/bootstrap')
        # with open(self._debugget, mode='wb') as localfile:
        #     localfile.write(get_resp.content)

        try:
            from json.decoder import JSONDecodeError
            from simplejson import JSONDecodeError as SimpleJSONDecodeError
            # Need to catch both as Python 3.5 appears to use simplejson
        except ImportError:
            JSONDecodeError = ValueError
        try:
            email = get_resp.json()['authentication']['customerEmail']
        except (JSONDecodeError, SimpleJSONDecodeError) as ex:
            # ValueError is necessary for Python 3.5 for some reason
            template = ("An exception of type {0} occurred."
                        " Arguments:\n{1!r}")
            message = template.format(type(ex).__name__, ex.args)
            _LOGGER.debug("Not logged in: ", message)
            return False
        if email.lower() == self._email.lower():
            _LOGGER.debug("Logged in as {}".format(email))
            return True
        else:
            _LOGGER.debug("Not logged in due to email mismatch")
            self.reset_login()
            return False

    def login(self, cookies=None, captcha=None, securitycode=None,
              claimsoption=None, verificationcode=None):
        """Login to Amazon."""
        from bs4 import BeautifulSoup
        import pickle

        if (cookies is not None and self.test_loggedin(cookies)):
            _LOGGER.debug("Using cookies to log in")
            self.status = {}
            self.status['login_successful'] = True
            _LOGGER.debug("Log in successful with cookies")
            return
        else:
            _LOGGER.debug("No valid cookies for log in; using credentials")
        #  site = 'https://www.' + self._url + '/gp/sign-in.html'
        #  use alexa site instead
        site = 'https://alexa.' + self._url + '/api/devices-v2/device'
        if self._session is None:
            '''initiate session'''

            self._session = requests.Session()

            '''define session headers'''
            self._session.headers = {
                'User-Agent': ('Mozilla/5.0 (Windows NT 6.3; Win64; x64) '
                               'AppleWebKit/537.36 (KHTML, like Gecko) '
                               'Chrome/68.0.3440.106 Safari/537.36'),
                'Accept': ('text/html,application/xhtml+xml, '
                           'application/xml;q=0.9,*/*;q=0.8'),
                'Accept-Language': '*'
            }

        if self._lastreq is not None:
            site = self._lastreq.url
            _LOGGER.debug("Loaded last request to {} ".format(site))
            html = self._lastreq.text
            '''get BeautifulSoup object of the html of the login page'''
            if self._debug:
                with open(self._debugget, mode='wb') as localfile:
                    localfile.write(self._lastreq.content)

            soup = BeautifulSoup(html, 'html.parser')
            site = soup.find('form').get('action')
            if site is None:
                site = self._lastreq.url
            elif site == 'verify':
                import re
                site = re.search(r'(.+)/(.*)',
                                 self._lastreq.url).groups()[0] + "/verify"

        if self._data is None:
            resp = self._session.get(site)
            self._lastreq = resp
            if resp.history:
                _LOGGER.debug("Get to {} was redirected to {}".format(
                    site,
                    resp.url))
                self._session.headers['Referer'] = resp.url
            else:
                _LOGGER.debug("Get to {} was not redirected".format(site))
                self._session.headers['Referer'] = site

            html = resp.text
            '''get BeautifulSoup object of the html of the login page'''
            if self._debug:
                with open(self._debugget, mode='wb') as localfile:
                    localfile.write(resp.content)

            soup = BeautifulSoup(html, 'html.parser')
            '''scrape login page to get all the inputs required for login'''
            self._data = self.get_inputs(soup)
            site = soup.find('form', {'name': 'signIn'}).get('action')

        # _LOGGER.debug("Init Form Data: {}".format(self._data))

        '''add username and password to the data for post request'''
        '''check if there is an input field'''
        if "email" in self._data:
            self._data['email'] = self._email.encode('utf-8')
        if "password" in self._data:
            self._data['password'] = self._password.encode('utf-8')
        if "rememberMe" in self._data:
            self._data['rememberMe'] = "true".encode('utf-8')

        status = {}
        _LOGGER.debug(("Preparing post to {} Captcha: {}"
                       " SecurityCode: {} Claimsoption: {} "
                       "VerificationCode: {}").format(
            site,
            captcha,
            securitycode,
            claimsoption,
            verificationcode
            ))
        if (captcha is not None and 'guess' in self._data):
            self._data['guess'] = captcha.encode('utf-8')
        if (securitycode is not None and 'otpCode' in self._data):
            self._data['otpCode'] = securitycode.encode('utf-8')
            self._data['rememberDevice'] = ""
        if (claimsoption is not None and 'option' in self._data):
            self._data['option'] = claimsoption.encode('utf-8')
        if (verificationcode is not None and 'code' in self._data):
            self._data['code'] = verificationcode.encode('utf-8')
        self._session.headers['Content-Type'] = ("application/x-www-form-"
                                                 "urlencoded; charset=utf-8")
        self._data.pop('', None)

        if self._debug:
            _LOGGER.debug("Cookies: {}".format(self._session.cookies))
            _LOGGER.debug("Submit Form Data: {}".format(self._data))
            _LOGGER.debug("Header: {}".format(self._session.headers))

        # submit post request with username/password and other needed info
        post_resp = self._session.post(site, data=self._data)
        self._session.headers['Referer'] = site

        self._lastreq = post_resp
        if self._debug:
            with open(self._debugpost, mode='wb') as localfile:
                localfile.write(post_resp.content)

        post_soup = BeautifulSoup(post_resp.content, 'html.parser')

        login_tag = post_soup.find('form', {'name': 'signIn'})
        captcha_tag = post_soup.find(id="auth-captcha-image")

        # another login required and no captcha request? try once more.
        # This is a necessary hack as the first attempt always fails.
        # TODO: Figure out how to remove this hack

        if (login_tag is not None and captcha_tag is None):
            login_url = login_tag.get("action")
            _LOGGER.debug("Performing second login to: {}".format(
                login_url))
            post_resp = self._session.post(login_url,
                                           data=self._data)
            if self._debug:
                with open(self._debugpost, mode='wb') as localfile:
                    localfile.write(post_resp.content)
            post_soup = BeautifulSoup(post_resp.content, 'html.parser')
            login_tag = post_soup.find('form', {'name': 'signIn'})
            captcha_tag = post_soup.find(id="auth-captcha-image")

        securitycode_tag = post_soup.find(id="auth-mfa-otpcode")
        errorbox = (post_soup.find(id="auth-error-message-box")
                    if post_soup.find(id="auth-error-message-box") else
                    post_soup.find(id="auth-warning-message-box"))
        claimspicker_tag = post_soup.find('form', {'name': 'claimspicker'})
        verificationcode_tag = post_soup.find('form', {'action': 'verify'})

        # pull out Amazon error message

        if errorbox:
            error_message = errorbox.find('h4').string
            for li in errorbox.findAll('li'):
                error_message += li.find('span').string
            _LOGGER.debug("Error message: {}".format(error_message))
            status['error_message'] = error_message

        if captcha_tag is not None:
            _LOGGER.debug("Captcha requested")
            status['captcha_required'] = True
            status['captcha_image_url'] = captcha_tag.get('src')
            self._data = self.get_inputs(post_soup)

        elif securitycode_tag is not None:
            _LOGGER.debug("2FA requested")
            status['securitycode_required'] = True
            self._data = self.get_inputs(post_soup, {'id': 'auth-mfa-form'})

        elif claimspicker_tag is not None:
            claims_message = ""
            options_message = ""
            for div in claimspicker_tag.findAll('div', 'a-row'):
                claims_message += "{}\n".format(div.string)
            for label in claimspicker_tag.findAll('label'):
                value = (label.find('input')['value']) if label.find(
                    'input') else ""
                message = (label.find('span').string) if label.find(
                    'span') else ""
                valuemessage = ("Option: {} = `{}`.\n".format(
                    value, message)) if value != "" else ""
                options_message += valuemessage
            _LOGGER.debug("Verification method requested: {}".format(
                claims_message, options_message))
            status['claimspicker_required'] = True
            status['claimspicker_message'] = options_message
            self._data = self.get_inputs(post_soup, {'name': 'claimspicker'})
        elif verificationcode_tag is not None:
            _LOGGER.debug("Verification code requested:")
            status['verificationcode_required'] = True
            self._data = self.get_inputs(post_soup, {'action': 'verify'})
        elif login_tag is not None:
            login_url = login_tag.get("action")
            _LOGGER.debug("Another login requested to: {}".format(
                login_url))
            status['login_failed'] = True

        else:
            _LOGGER.debug("Captcha/2FA not requested; confirming login.")
            if self.test_loggedin():
                _LOGGER.debug("Login confirmed; saving cookie to {}".format(
                        self._cookiefile))
                status['login_successful'] = True
                with open(self._cookiefile, 'wb') as myfile:
                    try:
                        pickle.dump(self._session.cookies, myfile)
                    except Exception as ex:
                        template = ("An exception of type {0} occurred."
                                    " Arguments:\n{1!r}")
                        message = template.format(type(ex).__name__, ex.args)
                        _LOGGER.debug(
                            "Error saving pickled cookie to {}: {}".format(
                                self._cookiefile,
                                message))
            else:
                _LOGGER.debug("Login failed; check credentials")
                status['login_failed'] = True

        self.status = status


class AlexaAPI():
    """Class for accessing a specific Alexa device using API.

    Args:
    device (AlexaClient): Instance of an AlexaClient to access
    login (AlexaLogin): Successfully logged in AlexaLogin
    """

    def __init__(self, device, login):
        """Initialize Alexa device."""
        self._device = device
        self._session = login._session
        self._url = 'https://alexa.' + login._url

        csrf = self._session.cookies.get_dict()['csrf']
        self._session.headers['csrf'] = csrf

    def _catchAllExceptions(func):
        import functools

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as ex:
                template = ("An exception of type {0} occurred."
                            " Arguments:\n{1!r}")
                message = template.format(type(ex).__name__, ex.args)
                _LOGGER.error(("An error occured accessing AlexaAPI: "
                               "{}").format(message))
                return None
        return wrapper

    @_catchAllExceptions
    def _post_request(self, uri, data):
        self._session.post(self._url + uri, json=data)

    @_catchAllExceptions
    def _get_request(self, uri, data=None):
        return self._session.get(self._url + uri, json=data)

    @_catchAllExceptions
    def get_last_device_serial(self):
        """Identify the last device's serial number."""
        response = self._get_request('/api/activities?'
                                     'startTime=&size=1&offset=1')
        last_activity = response.json()['activities'][0]
        # Ignore discarded activity records
        if (last_activity['activityStatus'][0]
                != 'DISCARDED_NON_DEVICE_DIRECTED_INTENT'):
            return last_activity['sourceDeviceIds'][0]['serialNumber']
        else:
            return None

    def play_music(self, provider_id, search_phrase, customer_id=None):
        """Play Music based on search."""
        data = {
            "behaviorId": "PREVIEW",
            "sequenceJson": "{\"@type\": \
            \"com.amazon.alexa.behaviors.model.Sequence\", \
            \"startNode\":{\"@type\": \
            \"com.amazon.alexa.behaviors.model.OpaquePayloadOperationNode\", \
            \"type\":\"Alexa.Music.PlaySearchPhrase\",\"operationPayload\": \
            {\"deviceType\":\"" + self._device._device_type + "\", \
            \"deviceSerialNumber\":\"" + self._device.unique_id +
            "\",\"locale\":\"en-US\", \
            \"customerId\":\"" + (customer_id
                                  if customer_id is not None
                                  else self._device_owner_customer_id) +
            "\", \"searchPhrase\": \"" + search_phrase + "\", \
             \"sanitizedSearchPhrase\": \"" + search_phrase + "\", \
             \"musicProviderId\": \"" + provider_id + "\"}}}",
            "status": "ENABLED"
        }

        self._post_request('/api/behaviors/preview',
                           data=data)

    def send_tts(self, message, customer_id=None):
        """Send message for TTS at speaker."""
        data = {
            "behaviorId": "PREVIEW",
            "sequenceJson": "{\"@type\": \
            \"com.amazon.alexa.behaviors.model.Sequence\", \
            \"startNode\":{\"@type\": \
            \"com.amazon.alexa.behaviors.model.OpaquePayloadOperationNode\", \
            \"type\":\"Alexa.Speak\",\"operationPayload\": \
            {\"deviceType\":\"" + self._device._device_type + "\", \
            \"deviceSerialNumber\":\"" + self._device.unique_id +
            "\",\"locale\":\"en-US\", \
            \"customerId\":\"" + (customer_id
                                  if customer_id is not None
                                  else self._device_owner_customer_id) +
            "\", \"textToSpeak\": \"" + message + "\"}}}",
            "status": "ENABLED"
        }
        self._post_request('/api/behaviors/preview',
                           data=data)

    def set_media(self, data):
        """Select the media player."""
        self._post_request('/api/np/command?deviceSerialNumber=' +
                           self._device.unique_id + '&deviceType=' +
                           self._device._device_type, data=data)

    def previous(self):
        """Play previous."""
        self.set_media({"type": "PreviousCommand"})

    def next(self):
        """Play next."""
        self.set_media({"type": "NextCommand"})

    def pause(self):
        """Pause."""
        self.set_media({"type": "PauseCommand"})

    def play(self):
        """Play."""
        self.set_media({"type": "PlayCommand"})

    def set_volume(self, volume):
        """Set volume."""
        self.set_media({"type": "VolumeLevelCommand",
                        "volumeLevel": volume*100})

    @_catchAllExceptions
    def get_state(self):
        """Get playing state."""
        response = self._get_request('/api/np/player?deviceSerialNumber=' +
                                     self._device.unique_id +
                                     '&deviceType=' +
                                     self._device._device_type +
                                     '&screenWidth=2560')
        return response.json()

    @staticmethod
    @_catchAllExceptions
    def get_bluetooth(login):
        """Get paired bluetooth devices."""
        session = login._session
        url = login._url
        response = session.get('https://alexa.' + url +
                               '/api/bluetooth?cached=false')
        return response.json()

    def set_bluetooth(self, mac):
        """Pair with bluetooth device with mac address."""
        self._post_request('/api/bluetooth/pair-sink/' +
                           self._device._device_type + '/' +
                           self._device.unique_id,
                           data={"bluetoothDeviceAddress": mac})

    def disconnect_bluetooth(self):
        """Disconnect all bluetooth devices."""
        self._post_request('/api/bluetooth/disconnect-sink/' +
                           self._device._device_type + '/' +
                           self._device.unique_id, data=None)

    @staticmethod
    @_catchAllExceptions
    def get_devices(login):
        """Identify all Alexa devices."""
        session = login._session
        url = login._url
        response = session.get('https://alexa.' + url +
                               '/api/devices-v2/device')
        return response.json()['devices']

    @staticmethod
    @_catchAllExceptions
    def get_authentication(login):
        """Get authentication json."""
        session = login._session
        url = login._url
        response = session.get('https://alexa.' + url +
                               '/api/bootstrap')
        return response.json()['authentication']
