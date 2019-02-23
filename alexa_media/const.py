"""
Support to interface with Alexa Devices.

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
VERSION 1.0.0
"""
from datetime import timedelta

DOMAIN = 'alexa_media'
DATA_ALEXAMEDIA = 'alexa_media'

PLAY_SCAN_INTERVAL = 20
SCAN_INTERVAL = timedelta(seconds=60)
MIN_TIME_BETWEEN_SCANS = SCAN_INTERVAL
MIN_TIME_BETWEEN_FORCED_SCANS = timedelta(seconds=1)

ALEXA_COMPONENTS = [
    'media_player'
]

CONF_ACCOUNTS = 'accounts'
CONF_DEBUG = 'debug'
CONF_INCLUDE_DEVICES = 'include_devices'
CONF_EXCLUDE_DEVICES = 'exclude_devices'
SERVICE_ALEXA_TTS = 'alexa_tts'
ATTR_MESSAGE = 'message'
