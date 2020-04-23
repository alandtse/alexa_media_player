#!/usr/bin/env python
# -*- coding: utf-8 -*-
#  SPDX-License-Identifier: Apache-2.0
"""
Support to interface with Alexa Devices.

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""
from datetime import timedelta

__version__ = "2.5.15"
PROJECT_URL = "https://github.com/custom-components/alexa_media_player/"
ISSUE_URL = "{}issues".format(PROJECT_URL)

DOMAIN = "alexa_media"
DATA_ALEXAMEDIA = "alexa_media"

PLAY_SCAN_INTERVAL = 20
SCAN_INTERVAL = timedelta(seconds=60)
MIN_TIME_BETWEEN_SCANS = SCAN_INTERVAL
MIN_TIME_BETWEEN_FORCED_SCANS = timedelta(seconds=1)

ALEXA_COMPONENTS = [
    "media_player",
]
DEPENDENT_ALEXA_COMPONENTS = ["notify", "switch", "sensor", "alarm_control_panel"]

CONF_ACCOUNTS = "accounts"
CONF_DEBUG = "debug"
CONF_INCLUDE_DEVICES = "include_devices"
CONF_EXCLUDE_DEVICES = "exclude_devices"

SERVICE_CLEAR_HISTORY = "clear_history"
SERVICE_UPDATE_LAST_CALLED = "update_last_called"
ATTR_MESSAGE = "message"
ATTR_EMAIL = "email"
ATTR_NUM_ENTRIES = "entries"
STARTUP = """
-------------------------------------------------------------------
{}
Version: {}
This is a custom component
If you have any issues with this you need to open an issue here:
{}
-------------------------------------------------------------------
""".format(
    DOMAIN, __version__, ISSUE_URL
)
