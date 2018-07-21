"""
Support to interface with Alexa Devices.
For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
VERSION 0.7.1
"""
import json
import logging

from datetime import timedelta

import requests
import voluptuous as vol
from bs4 import BeautifulSoup

from homeassistant import util
from homeassistant.components.media_player import (
    MEDIA_TYPE_MUSIC, PLATFORM_SCHEMA,SUPPORT_NEXT_TRACK,
    SUPPORT_PAUSE, SUPPORT_PLAY, SUPPORT_PREVIOUS_TRACK,
    SUPPORT_STOP, SUPPORT_TURN_OFF, SUPPORT_VOLUME_MUTE,
    SUPPORT_PLAY_MEDIA, SUPPORT_VOLUME_SET, 
    MediaPlayerDevice, DOMAIN, MEDIA_PLAYER_SCHEMA, 
    SUPPORT_SELECT_SOURCE)
from homeassistant.const import (
    CONF_EMAIL, CONF_PASSWORD, CONF_URL, STATE_UNKNOWN, 
    STATE_IDLE, STATE_OFF, STATE_STANDBY, STATE_PAUSED, 
    STATE_PLAYING)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import extract_entity_ids
from homeassistant.helpers.event import track_utc_time_change
from homeassistant.util.json import load_json, save_json
from homeassistant.util import dt as dt_util

SUPPORT_ALEXA = (SUPPORT_PAUSE | SUPPORT_PREVIOUS_TRACK |
                    SUPPORT_NEXT_TRACK | SUPPORT_STOP |
                    SUPPORT_VOLUME_SET | SUPPORT_PLAY |
                    SUPPORT_PLAY_MEDIA | SUPPORT_TURN_OFF | 
                    SUPPORT_VOLUME_MUTE | SUPPORT_PAUSE | 
                    SUPPORT_SELECT_SOURCE)
_CONFIGURING = {}
_LOGGER = logging.getLogger(__name__)

REQUIREMENTS = ['beautifulsoup4==4.6.0']

MIN_TIME_BETWEEN_SCANS = timedelta(seconds=15)
MIN_TIME_BETWEEN_FORCED_SCANS = timedelta(seconds=1)

ALEXA_DATA = "alexa_media"

SERVICE_ALEXA_TTS = 'alexa_tts'

ATTR_MESSAGE = 'message'
ALEXA_TTS_SCHEMA = MEDIA_PLAYER_SCHEMA.extend({
    vol.Required(ATTR_MESSAGE): cv.string,
})


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_EMAIL): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Required(CONF_URL): cv.string,
})

def request_configuration(hass, config, setup_platform_callback, 
                          captcha_url=None):
    """Request configuration steps from the user."""
    configurator = hass.components.configurator

    async def configuration_callback(callback_data):
        """Handle the submitted configuration."""
        def done():
            configurator.request_done(instance)

        hass.async_add_job(done)
        hass.async_add_job(setup_platform_callback, callback_data)

    instance = configurator.request_config(
        "Alexa Media Player", configuration_callback,
        description='Please enter the text for the above captcha.',
        description_image=captcha_url,
        submit_caption="Confirm",
        fields=[{'id': 'captcha', 'name': 'Captca'}]
    )

def setup_platform(hass, config, add_devices_callback, 
                   discovery_info=None):
    """Set up the Alexa platform."""
    if ALEXA_DATA not in hass.data:
        hass.data[ALEXA_DATA] = {}

    email =  config.get(CONF_EMAIL)
    password = config.get(CONF_PASSWORD)
    url = config.get(CONF_URL)

    login = AlexaLogin(url, email, password)

    async def setup_platform_callback(callback_data):
        login.login(captcha=callback_data.get('captcha'))

        if 'login_successful' in login.status:
            hass.async_add_job(setup_alexa, hass, config, 
                               add_devices_callback, login)
        else:
            login.reset_login()
            login.login()
            hass.async_add_job(request_configuration, hass, config,
                               setup_platform_callback,
                               login.status['captcha_image_url'])

    if 'captcha_required' in login.status:
        hass.async_add_job(request_configuration, hass, config,
                           setup_platform_callback,
                           login.status['captcha_image_url'])


def setup_alexa(hass, config, add_devices_callback, login_obj):
    """Set up a alexa api based on host parameter."""
    alexa_clients = hass.data[ALEXA_DATA]
    alexa_sessions = {}
    track_utc_time_change(hass, lambda now: update_devices(), second=30)

    url = config.get(CONF_URL)

    @util.Throttle(MIN_TIME_BETWEEN_SCANS, MIN_TIME_BETWEEN_FORCED_SCANS)
    def update_devices():
        """Update the devices objects."""

        devices = AlexaAPI.get_devices(url, login_obj._session)
        devices = devices.json()['devices']
        bluetooth = AlexaAPI.get_bluetooth(url, login_obj._session).json()

        new_alexa_clients = []
        available_client_ids = []
        for device in devices:

            for b_state in bluetooth['bluetoothStates']:
                if device['serialNumber'] == b_state['deviceSerialNumber']:
                    device['bluetooth_state'] = b_state

            available_client_ids.append(device['serialNumber'])

            if device['serialNumber'] not in alexa_clients:
                new_client = AlexaClient(config, login_obj._session, device,
                                         update_devices, url)
                alexa_clients[device['serialNumber']] = new_client
                new_alexa_clients.append(new_client)
            else:
                alexa_clients[device['serialNumber']].refresh(device)


        if new_alexa_clients:
            def tts_handler(call):
                for alexa in service_to_entities(call):
                    if call.service == SERVICE_ALEXA_TTS:
                        message = call.data.get(ATTR_MESSAGE)
                        alexa.send_tts(message)

            def service_to_entities(call):
                """Return the known devices that a service call mentions."""
                entity_ids = extract_entity_ids(hass, call)
                if entity_ids:
                    entities = [entity for entity in new_alexa_clients
                                if entity.entity_id in entity_ids]
                else:
                    entities = rokus

                return entities

            hass.services.register(DOMAIN, SERVICE_ALEXA_TTS, tts_handler,
                                   schema=ALEXA_TTS_SCHEMA)
            add_devices_callback(new_alexa_clients)

    update_devices()


class AlexaClient(MediaPlayerDevice):
    """Representation of a Alexa device."""

    def __init__(self, config, session, device, update_devices, url):
        """Initialize the Alexa device."""
        # Class info
        self.alexa_api = AlexaAPI(self, session, url)

        self.update_devices = update_devices
        # Device info
        self._device = None
        self._device_name = None
        self._device_serial_number = None
        self._device_type = None
        self._device_family = None
        self._device_owner_customer_id = None
        self._software_version = None
        self._available = None
        self._capabilities = []
        # Media
        self._session = None
        self._media_duration = None
        self._media_image_url = None
        self._media_title = None
        self._media_pos = None
        self._media_album_name = None
        self._media_artist = None
        self._player_state = None
        self._media_is_muted = None
        self._media_vol_level = None
        self._previous_volume = None
        self._source = None
        self._source_list = []
        self.refresh(device)

    def _clear_media_details(self):
        """Set all Media Items to None."""
        # General
        self._media_duration = None
        self._media_image_url = None
        self._media_title = None
        self._media_pos = None
        self._media_album_name = None
        self._media_artist = None
        self._media_player_state = None
        self._media_is_muted = None
        self._media_vol_level = None

    def refresh(self, device):
        """Refresh key device data."""
        self._device = device
        self._device_name = device['accountName']
        self._device_family = device['deviceFamily']
        self._device_type = device['deviceType']
        self._device_serial_number = device['serialNumber']
        self._device_owner_customer_id = device['deviceOwnerCustomerId']
        self._software_version = device['softwareVersion']
        self._available = device['online']
        self._capabilities = device['capabilities']
        self._bluetooth_state = device['bluetooth_state']
        self._source = self._get_source()
        self._source_list = self._get_source_list()
        session = self.alexa_api.get_state().json()

        self._clear_media_details()
        # update the session
        self._session = session
        if 'playerInfo' in self._session:
            self._session = self._session['playerInfo']
            if self._session['state'] is not None:
                self._media_player_state = self._session['state']
                self._media_pos = self._session['progress']['mediaProgress']
                self._media_is_muted = self._session['volume']['muted']
                self._media_vol_level = self._session['volume']['volume'] / 100
                self._media_title = self._session['infoText']['title']
                self._media_artist = self._session['infoText']['subText1']
                self._media_album_name = self._session['infoText']['subText2']
                self._media_image_url = self._session['mainArt']['url']
                self._media_duration = self._session['progress']['mediaLength']

    @property
    def source(self):
        """Return the current input source."""
        return self._source

    @property
    def source_list(self):
        """List of available input sources."""
        return self._source_list

    def select_source(self, source):
        """Select input source."""
        if source == 'Local Speaker':
            self.alexa_api.disconnect_bluetooth()
            self._source = 'Local Speaker'
        elif self._bluetooth_state['pairedDeviceList'] is not None:
            for devices in self._bluetooth_state['pairedDeviceList']:
                if devices['friendlyName'] == source:
                    self.alexa_api.set_bluetooth(devices['address'])
                    self._source = source


    def _get_source(self):
        source = 'Local Speaker'
        if self._bluetooth_state['pairedDeviceList'] is not None:
            for device in self._bluetooth_state['pairedDeviceList']:
                if device['connected'] == True:
                    return device['friendlyName']
        return source

    def _get_source_list(self):
        sources = []
        if self._bluetooth_state['pairedDeviceList'] is not None:
            for devices in self._bluetooth_state['pairedDeviceList']:
                sources.append(devices['friendlyName'])
        return ['Local Speaker'] + sources

    @property
    def available(self):
        """Return the availability of the client."""
        return self._available
    @property
    def unique_id(self):
        """Return the id of this Alexa client."""
        return self.device_serial_number

    @property
    def name(self):
        """Return the name of the device."""
        return self._device_name

    @property
    def device_serial_number(self):
        """Return the machine identifier of the device."""
        return self._device_serial_number

    @property
    def device(self):
        """Return the device, if any."""
        return self._device

    @property
    def session(self):
        """Return the session, if any."""
        return self._session

    @property
    def state(self):
        """Return the state of the device."""
        if self._media_player_state == 'PLAYING':
            return STATE_PLAYING
        elif self._media_player_state == 'PAUSED':
            return STATE_PAUSED
        elif self._media_player_state == 'IDLE':
            return STATE_IDLE
        return STATE_STANDBY

    def update(self):
        """Get the latest details."""
        self.update_devices(no_throttle=True)

    @property
    def media_content_type(self):
        """Return the content type of current playing media."""
        if self.state in [STATE_PLAYING, STATE_PAUSED]:
            return MEDIA_TYPE_MUSIC
        return STATE_STANDBY

    @property
    def media_artist(self):
        """Return the artist of current playing media, music track only."""
        return self._media_artist

    @property
    def media_album_name(self):
        """Return the album name of current playing media, music track only."""
        return self._media_album_name

    @property
    def media_duration(self):
        """Return the duration of current playing media in seconds."""
        return self._media_duration

    @property
    def media_image_url(self):
        """Return the image URL of current playing media."""
        return self._media_image_url

    @property
    def media_title(self):
        """Return the title of current playing media."""
        return self._media_title

    @property
    def device_family(self):
        """Return the make of the device (ex. Echo, Other)."""
        return self._device_family

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        return SUPPORT_ALEXA

    def set_volume_level(self, volume):
        """Set volume level, range 0..1."""
        if not (self.state in [STATE_PLAYING, STATE_PAUSED]
                and self.available):
            return
        self.alexa_api.set_volume(volume)
        self._media_vol_level = volume

    @property
    def volume_level(self):
        """Return the volume level of the client (0..1)."""
        return self._media_vol_level

    @property
    def is_volume_muted(self):
        """Return boolean if volume is currently muted."""
        if self.volume_level == 0:
            return True
        return False

    def mute_volume(self, mute):
        """Mute the volume.
        Since we can't actually mute, we'll:
        - On mute, store volume and set volume to 0
        - On unmute, set volume to previously stored volume
        """
        if not (self.state == STATE_PLAYING and self.available):
            return

        self._media_is_muted = mute
        if mute:
            self._previous_volume = self.volume_level
            self.alexa_api.set_volume(0)
        else:
            if self._previous_volume is not None:
                self.alexa_api.set_volume(self._previous_volume)
            else:
                self.alexa_api.set_volume(50)

    def media_play(self):
        """Send play command."""
        if not (self.state in [STATE_PLAYING, STATE_PAUSED]
                and self.available):
            return
        self.alexa_api.play()

    def media_pause(self):
        """Send pause command."""
        if not (self.state in [STATE_PLAYING, STATE_PAUSED]
                and self.available):
            return
        self.alexa_api.pause()

    def turn_off(self):
        """Turn the client off."""
        # Fake it since we can't turn the client off
        self.media_pause()

    def media_next_track(self):
        """Send next track command."""
        if not (self.state in [STATE_PLAYING, STATE_PAUSED]
                and self.available):
            return
        self.alexa_api.next()

    def media_previous_track(self):
        """Send previous track command."""
        if not (self.state in [STATE_PLAYING, STATE_PAUSED]
                and self.available):
            return
        self.alexa_api.previous()


    def send_tts(self, message):
        """Send TTS to Device NOTE: Does not work on WHA Groups"""
        self.alexa_api.send_tts(message)

    def play_media(self, media_type, media_id, **kwargs):
        """Send the play_media command to the media player."""
        if media_type == "music":
            self.alexa_api.send_tts("Sorry, text to speech can only be called " +
                                    " with the media player alexa tts service")
        else:
            self.alexa_api.play_music(media_type, media_id)

    @property
    def device_state_attributes(self):
        """Return the scene state attributes."""
        attr = {
            'available': self._available,
        }
        return attr


class AlexaLogin():
    def __init__(self, url, email, password):
        self._url = url
        self._email = email
        self._password = password
        self._session = None
        self._data = None
        self.status = None

        self.login()

    def reset_login(self):
        self._session = None
        self._data = None
        self.status = None

    def get_inputs(self, soup):
        data = {}
        form = soup.find('form', {'name': 'signIn'})
        for field in form.find_all('input'):
            try:
                data[field['name']] = field['value']
            except:
                pass
        return data

    def login(self, cookies=None, captcha=None):

        if self._session is None:
            site = 'https://www.' + self._url + '/gp/sign-in.html'

            '''initiate session'''
            self._session = requests.Session()

            '''define session headers'''
            self._session.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) \
            AppleWebKit/537.36 (KHTML, like Gecko) \
            Chrome/44.0.2403.61 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml, \
            application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': site
            }

        if self._data is None:
            resp = self._session.get(site)
            html = resp.text
            '''get BeautifulSoup object of the html of the login page'''
            soup = BeautifulSoup(html , 'lxml')
            '''scrape login page to get all the needed inputs required for login'''
            self._data = self.get_inputs(soup)

        status = {}

        '''add username and password to the data for post request'''
        self._data[u'email'] = self._email
        self._data[u'password'] = self._password

        if captcha is not None:
            self._data[u'guess'] = captcha

        '''submit post request with username/password and other needed info'''
        post_resp = self._session.post('https://www.' + self._url +
                    '/ap/signin', data = self._data)

        post_soup = BeautifulSoup(post_resp.content , 'lxml')
        captcha_tag = post_soup.find(id="auth-captcha-image")
        if captcha_tag is not None:
            status['captcha_required'] = True
            status['captcha_image_url'] = captcha_tag.get('src')
            self._data = self.get_inputs(post_soup)

        else:
            '''attempt to get device list, if unsuccessful login failed'''
            post_resp = self._session.get('https://alexa.' + self._url +
                        '/api/devices-v2/device')

            if 'devices' in post_resp.text:
                status['login_successful'] = True
            else:
                status['login_failed'] = True

        self.status = status


class AlexaAPI():
    def __init__(self, device, session, url):
        self._device = device
        self._session = session
        self._url = 'https://alexa.' + url

        csrf = self._session.cookies.get_dict()['csrf']
        self._session.headers['csrf'] = csrf

    def _post_request(self, uri, data):
        try:
            self._session.post(self._url + uri, json = data)
        except:
            _LOGGER.error("An error occured accessing the API")

    def _get_request(self, uri, data=None):
        try:
            return self._session.get(self._url + uri, json = data)
        except:
            _LOGGER.error("An error occured accessing the API")
            return None

    def play_music(self, provider_id, search_phrase):
        data = {
            "behaviorId":"PREVIEW",
            "sequenceJson":"{\"@type\": \
            \"com.amazon.alexa.behaviors.model.Sequence\", \
            \"startNode\":{\"@type\": \
            \"com.amazon.alexa.behaviors.model.OpaquePayloadOperationNode\", \
            \"type\":\"Alexa.Music.PlaySearchPhrase\",\"operationPayload\": \
            {\"deviceType\":\"" + self._device._device_type + "\", \
            \"deviceSerialNumber\":\"" + self._device.unique_id + 
            "\",\"locale\":\"en-US\", \
            \"customerId\":\"" + self._device._device_owner_customer_id + 
            "\", \"searchPhrase\": \"" + search_phrase + "\", \
             \"sanitizedSearchPhrase\": \"" + search_phrase + "\", \
             \"musicProviderId\": \"" + provider_id + "\"}}}",
            "status":"ENABLED"
        }
        self._post_request('/api/behaviors/preview',
                           data=data)

    def send_tts(self, message):
        data = {
            "behaviorId":"PREVIEW",
            "sequenceJson":"{\"@type\": \
            \"com.amazon.alexa.behaviors.model.Sequence\", \
            \"startNode\":{\"@type\": \
            \"com.amazon.alexa.behaviors.model.OpaquePayloadOperationNode\", \
            \"type\":\"Alexa.Speak\",\"operationPayload\": \
            {\"deviceType\":\"" + self._device._device_type + "\", \
            \"deviceSerialNumber\":\"" + self._device.unique_id + 
            "\",\"locale\":\"en-US\", \
            \"customerId\":\"" + self._device._device_owner_customer_id + 
            "\", \"textToSpeak\": \"" + message + "\"}}}",
            "status":"ENABLED"
        }
        self._post_request('/api/behaviors/preview',
                           data=data)

    def set_media(self, data):
        self._post_request('/api/np/command?deviceSerialNumber=' +
                           self._device.unique_id + '&deviceType=' + 
                           self._device._device_type, data=data)
    def previous(self):
        self.set_media({"type": "PreviousCommand"})

    def next(self):
        self.set_media({"type": "NextCommand"})

    def pause(self):
        self.set_media({"type": "PauseCommand"})

    def play(self):
        self.set_media({"type": "PlayCommand"})

    def set_volume(self, volume):
            self.set_media({"type":"VolumeLevelCommand", 
                            "volumeLevel": volume*100})

    def get_state(self):
        response = self._get_request('/api/np/player?deviceSerialNumber=' +
            self._device.unique_id + '&deviceType=' +
            self._device._device_type + '&screenWidth=2560')
        return response

    @staticmethod
    def get_bluetooth(url, session):
        try:

            response = session.get('https://alexa.' + url + 
                                   '/api/bluetooth?cached=false')
            return response
        except:
            _LOGGER.error("An error occured accessing the API")
            return None

    def set_bluetooth(self, mac):
        self._post_request('/api/bluetooth/pair-sink/' +
                            self._device._device_type + '/' +
                            self._device.unique_id,
                            data={"bluetoothDeviceAddress": mac})

    def disconnect_bluetooth(self):
        self._post_request('/api/bluetooth/disconnect-sink/' +
                            self._device._device_type + '/' +
                            self._device.unique_id, data=None)

    @staticmethod
    def get_devices(url, session):
        try:
            response = session.get('https://alexa.' + url +
                                   '/api/devices-v2/device')
            return response
        except:
            _LOGGER.error("An error occured accessing the API")
            return None

