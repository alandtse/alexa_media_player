"""
Support to interface with Alexa Devices.
For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
VERSION 0.4
"""
import json
import logging

from datetime import timedelta

import requests
import voluptuous as vol

from homeassistant import util
from homeassistant.components.media_player import (
    MEDIA_TYPE_MUSIC, PLATFORM_SCHEMA,SUPPORT_NEXT_TRACK,
    SUPPORT_PAUSE, SUPPORT_PLAY, SUPPORT_PREVIOUS_TRACK,
    SUPPORT_STOP, SUPPORT_TURN_OFF, SUPPORT_VOLUME_MUTE,
    SUPPORT_VOLUME_SET, MediaPlayerDevice, DOMAIN,
    MEDIA_PLAYER_SCHEMA, SUPPORT_SELECT_SOURCE)
from homeassistant.const import (
    CONF_HOST, STATE_UNKNOWN, STATE_IDLE, STATE_OFF, 
    STATE_STANDBY, STATE_PAUSED, STATE_PLAYING)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import extract_entity_ids
from homeassistant.helpers.event import track_utc_time_change
from homeassistant.util.json import load_json, save_json
from homeassistant.util import dt as dt_util

SUPPORT_ALEXA = (SUPPORT_PAUSE | SUPPORT_PREVIOUS_TRACK |
                    SUPPORT_NEXT_TRACK | SUPPORT_STOP |
                    SUPPORT_VOLUME_SET | SUPPORT_PLAY |
                    SUPPORT_TURN_OFF | SUPPORT_VOLUME_MUTE |
                    SUPPORT_PAUSE | SUPPORT_SELECT_SOURCE)
_CONFIGURING = {}
_LOGGER = logging.getLogger(__name__)

MIN_TIME_BETWEEN_SCANS = timedelta(seconds=15)
MIN_TIME_BETWEEN_FORCED_SCANS = timedelta(seconds=1)

ALEXA_DATA = "alexa_media"

SERVICE_ALEXA_TTS = 'alexa_tts'

ATTR_MESSAGE = 'message'
ALEXA_TTS_SCHEMA = MEDIA_PLAYER_SCHEMA.extend({
    vol.Required(ATTR_MESSAGE): cv.string,
})


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_HOST): cv.string,
})

def setup_platform(hass, config, add_devices_callback, discovery_info=None):
    """Set up the Alexa platform."""
    if ALEXA_DATA not in hass.data:
        hass.data[ALEXA_DATA] = {}

    host = 'addon_9ff8aed5_alexaapi'
    if CONF_HOST in config:
        host = config.get(CONF_HOST)
    setup_alexa(host, hass, config, add_devices_callback)


def setup_alexa(host, hass, config, add_devices_callback):
    """Set up a alexa api based on host parameter."""
    alexa_clients = hass.data[ALEXA_DATA]
    alexa_sessions = {}
    track_utc_time_change(hass, lambda now: update_devices(), second=30)

    @util.Throttle(MIN_TIME_BETWEEN_SCANS, MIN_TIME_BETWEEN_FORCED_SCANS)
    def update_devices():
        """Update the devices objects."""

        devices = AlexaAPI.get_devices(host).json()['devices']

        new_alexa_clients = []
        available_client_ids = []
        for device in devices:

            available_client_ids.append(device['serialNumber'])

            if device['serialNumber'] not in alexa_clients:
                new_client = AlexaClient(config, host, device,
                                         update_devices)
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

    def __init__(self, config, host, device, update_devices):
        """Initialize the Alexa device."""
        # Class info
        self.alexa_api = AlexaAPI(host, self)

        self.update_devices = update_devices
        self.host = host
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
        self._media_position = None
        self._media_album_name = None
        self._media_artist = None
        self._player_state = None
        self._media_is_muted = None
        self._media_volume_level = None
        self._previous_volume = None
        self.refresh(device)

    def _clear_media_details(self):
        """Set all Media Items to None."""
        # General
        self._media_duration = None
        self._media_image_url = None
        self._media_title = None
        self._media_position = None
        self._media_album_name = None
        self._media_artist = None
        self._media_player_state = None
        self._media_is_muted = None
        self._media_volume_level = None

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
        self._bluetooth = self.alexa_api.get_bluetooth()

        session = self.alexa_api.get_state().json()

        self._clear_media_details()
        # update the session
        self._session = session
        if 'playerInfo' in self._session:
            self._session = self._session['playerInfo']
            if self._session['state'] is not None:
                self._media_player_state = self._session['state']
                self._media_position = self._session['progress']['mediaProgress']
                self._media_is_muted = self._session['volume']['muted']
                self._media_volume_level = self._session['volume']['volume'] / 100
                self._media_title = self._session['infoText']['title']
                self._media_artist = self._session['infoText']['subText1']
                self._media_album_name = self._session['infoText']['subText2']
                self._media_image_url = self._session['mainArt']['url']
                self._media_duration = self._session['progress']['mediaLength']

    @property
    def source(self):
        """Return the current input source."""
        source = 'Local Speaker'
        if self._bluetooth['pairedDeviceList'] is not None:
            for device in self._bluetooth['pairedDeviceList']:
                if device['connected'] == True:
                    return device['friendlyName']
        return source
    @property
    def source_list(self):
        """List of available input sources."""
        sources = []
        if self._bluetooth['pairedDeviceList'] is not None:
            for devices in self._bluetooth['pairedDeviceList']:
                sources.append(devices['friendlyName'])
        return ['Local Speaker'] + sources

    def select_source(self, source):
        """Select input source."""
        if self._bluetooth['pairedDeviceList'] is not None:
            for devices in self._bluetooth['pairedDeviceList']:
                if devices['friendlyName'] == source:
                    self.alexa_api.set_bluetooth(devices['address'])

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
        self._media_volume_level = volume

    @property
    def volume_level(self):
        """Return the volume level of the client (0..1)."""
        return self._media_volume_level

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

    def play_media(self, media_type, media_id, **kwargs):
        """Play Media"""
        if media_type == 'TTS':
            self.send_tts(media_id)

    def send_tts(self, message):
        """Send TTS to Device NOTE: Does not work on WHA Groups"""
        self.alexa_api.send_tts(message)

    @property
    def device_state_attributes(self):
        """Return the scene state attributes."""
        attr = {
            'available': self._available,
        }
        return attr

class AlexaAPI():
    def __init__(self, host, device):
        self._host = host 
        self._device = device

    def _post_request(self, uri, data):
        try:
            requests.post('http://' + self._host + ':8091/' + uri, data = data)
        except:
            _LOGGER.error("An error occured accessing the API")

    def _get_request(self, uri, data=None):
        try:
            return requests.post('http://' + self._host + ':8091/' + uri, data = data)
        except:
            _LOGGER.error("An error occured accessing the API")
            return None

    def send_tts(self, message):
        self._post_request('alexa-tts',
                           data={'deviceSerialNumber': self._device.unique_id, 
                                'tts': message})

    def previous(self):
        self._post_request('alexa-setMedia',
                           data={'deviceSerialNumber': self._device.unique_id, 
                                'command': 'PreviousCommand'})
    def next(self):
        self._post_request('alexa-setMedia',
                           data={'deviceSerialNumber': self._device.unique_id, 
                                'command': 'NextCommand'})

    def pause(self):
        self._post_request('alexa-setMedia',
                           data={'deviceSerialNumber': self._device.unique_id, 
                                'command': 'PauseCommand'})

    def play(self):
        self._post_request('alexa-setMedia',
                           data={'deviceSerialNumber': self._device.unique_id, 
                                'command': 'PlayCommand'})

    def set_volume(self, volume):
        self._post_request('alexa-setMedia',
                           data={'deviceSerialNumber': self._device.unique_id,
                                 'volume': volume*100 })

    def get_state(self):
        response = self._get_request('alexa-getState',
                        data={'deviceSerialNumber': self._device.unique_id})
        return response

    def get_bluetooth(self):
        response = self._get_request('alexa-getBluetooth').json()
        for bluetooth_state in response['bluetoothStates']:
            if self._device.unique_id == bluetooth_state['deviceSerialNumber']:
                return bluetooth_state

    def set_bluetooth(self, mac):
        self._post_request('alexa-setBluetooth',
                           data={'deviceSerialNumber': self._device.unique_id,
                                 'mac': mac})

    @staticmethod
    def get_devices(host):
        try:
            response = requests.post('http://' + host + ':8091/alexa-getDevices')
            return response
        except:
            _LOGGER.error("An error occured accessing the API")
            return None

