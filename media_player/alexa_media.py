"""
Support to interface with Alexa Devices.

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
VERSION 1.0.0
"""
import logging

import voluptuous as vol

from homeassistant.components.media_player import (
    MEDIA_TYPE_MUSIC, SUPPORT_NEXT_TRACK,
    SUPPORT_PAUSE, SUPPORT_PLAY, SUPPORT_PREVIOUS_TRACK,
    SUPPORT_STOP, SUPPORT_TURN_OFF, SUPPORT_VOLUME_MUTE,
    SUPPORT_PLAY_MEDIA, SUPPORT_VOLUME_SET, DOMAIN,
    MediaPlayerDevice, MEDIA_PLAYER_SCHEMA,
    SUPPORT_SELECT_SOURCE)
from homeassistant.const import (
    STATE_IDLE, STATE_STANDBY, STATE_PAUSED,
    STATE_PLAYING)
from homeassistant.components.alexa_media import DOMAIN as ALEXA_DOMAIN
from homeassistant.components.alexa_media import AlexaAPI as AlexaAPI
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import extract_entity_ids


SUPPORT_ALEXA = (SUPPORT_PAUSE | SUPPORT_PREVIOUS_TRACK |
                 SUPPORT_NEXT_TRACK | SUPPORT_STOP |
                 SUPPORT_VOLUME_SET | SUPPORT_PLAY |
                 SUPPORT_PLAY_MEDIA | SUPPORT_TURN_OFF |
                 SUPPORT_VOLUME_MUTE | SUPPORT_PAUSE |
                 SUPPORT_SELECT_SOURCE)
_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ['alexa_media']

SERVICE_ALEXA_TTS = 'alexa_tts'
ATTR_MESSAGE = 'message'
ALEXA_TTS_SCHEMA = MEDIA_PLAYER_SCHEMA.extend({
    vol.Required(ATTR_MESSAGE): cv.string,
})


def setup_platform(hass, config, add_devices_callback,
                   discovery_info=None):
    """Set up the Alexa media player platform."""
    def tts_handler(call):
        for alexa in service_to_entities(call):
            if call.service == SERVICE_ALEXA_TTS:
                message = call.data.get(ATTR_MESSAGE)
                alexa.send_tts(message)

    def service_to_entities(call):
        """Return the known devices that a service call mentions."""
        entity_ids = extract_entity_ids(hass, call)
        if entity_ids:
            entities = [entity for entity in devices
                        if entity.entity_id in entity_ids]
        else:
            entities = None

        return entities
    for account, account_dict in hass.data[ALEXA_DOMAIN]['accounts'].items():
        devices = [
            AlexaClient(
                device,
                account_dict['login_obj'],
                hass.data[ALEXA_DOMAIN]['update_devices'])
            for key, device in
            account_dict['devices']['media_player'].items()]
        add_devices_callback(devices, True)

    hass.services.register(DOMAIN, SERVICE_ALEXA_TTS, tts_handler,
                           schema=ALEXA_TTS_SCHEMA)


class AlexaClient(MediaPlayerDevice):
    """Representation of a Alexa device."""

    def __init__(self, device, login, update_devices):
        """Initialize the Alexa device."""
        # Class info
        self.alexa_api = AlexaAPI(self, login)
        self.auth = AlexaAPI.get_authentication(login)
        self.alexa_api_session = login._session

        # Logged in info
        self._authenticated = None
        self._can_access_prime_music = None
        self._customer_email = None
        self._customer_id = None
        self._customer_name = None
        self._set_authentication_details(self.auth)

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
        # Last Device
        self._last_called = None

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

    def _set_authentication_details(self, auth):
        """Set Authentication based off auth."""
        self._authenticated = auth['authenticated']
        self._can_access_prime_music = auth['canAccessPrimeMusicContent']
        self._customer_email = auth['customerEmail']
        self._customer_id = auth['customerId']
        self._customer_name = auth['customerName']

    def refresh(self, device=None):
        """Refresh key device data.

        Args:
        device (json): A refreshed device json from Amazon. For efficiency,
                       an individual device does not refresh if it's reported
                       as offline.
        """
        if device is not None:
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
        if self._available is True:
            self._source = self._get_source()
            self._source_list = self._get_source_list()
            session = self.alexa_api.get_state()
            self._last_called = self._get_last_called()
        self._clear_media_details()
        # update the session if it exists; not doing relogin here
        if session is not None:
            self._session = session
        if 'playerInfo' in self._session:
            self._session = self._session['playerInfo']
            if self._session['state'] is not None:
                self._media_player_state = self._session['state']
                self._media_pos = (self._session['progress']['mediaProgress']
                                   if (self._session['progress'] is not None
                                       and 'mediaProgress' in
                                       self._session['progress'])
                                   else None)
                self._media_is_muted = (self._session['volume']['muted']
                                        if (self._session['volume'] is not None
                                            and 'muted' in
                                            self._session['volume'])
                                        else None)
                self._media_vol_level = (self._session['volume']
                                                      ['volume'] / 100
                                         if(self._session['volume'] is not None
                                             and 'volume' in
                                             self._session['volume'])
                                         else None)
                self._media_title = (self._session['infoText']['title']
                                     if (self._session['infoText'] is not None
                                         and 'title' in
                                         self._session['infoText'])
                                     else None)
                self._media_artist = (self._session['infoText']['subText1']
                                      if (self._session['infoText'] is not None
                                          and 'subText1' in
                                          self._session['infoText'])
                                      else None)
                self._media_album_name = (self._session['infoText']['subText2']
                                          if (self._session['infoText'] is not
                                              None and 'subText2' in
                                              self._session['infoText'])
                                          else None)
                self._media_image_url = (self._session['mainArt']['url']
                                         if (self._session['mainArt'] is not
                                             None and 'url' in
                                             self._session['mainArt'])
                                         else None)
                self._media_duration = (self._session['progress']
                                                     ['mediaLength']
                                        if (self._session['progress'] is not
                                            None and 'mediaLength' in
                                            self._session['progress'])
                                        else None)

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
                if device['connected'] is True:
                    return device['friendlyName']
        return source

    def _get_source_list(self):
        sources = []
        if self._bluetooth_state['pairedDeviceList'] is not None:
            for devices in self._bluetooth_state['pairedDeviceList']:
                sources.append(devices['friendlyName'])
        return ['Local Speaker'] + sources

    def _get_last_called(self):
        if (self._device_serial_number ==
                self.alexa_api.get_last_device_serial()):
            return True
        return False

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
        self.update_devices(no_throttle=False)
        self.refresh()

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
        """Send TTS to Device NOTE: Does not work on WHA Groups."""
        self.alexa_api.send_tts(message, customer_id=self._customer_id)

    def play_media(self, media_type, media_id, **kwargs):
        """Send the play_media command to the media player."""
        if media_type == "music":
            self.alexa_api.send_tts("Sorry, text to speech can only be called "
                                    " with the media player alexa tts service")
        else:
            self.alexa_api.play_music(media_type, media_id,
                                      customer_id=self._customer_id)

    @property
    def device_state_attributes(self):
        """Return the scene state attributes."""
        attr = {
            'available': self._available,
            'last_called': self._last_called
        }
        return attr
