"""
Support to interface with Alexa Devices.

SPDX-License-Identifier: Apache-2.0

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""

import asyncio
import logging
import os
import re
import subprocess
from typing import Any, Dict, List, Optional
import urllib.request

from homeassistant import util
from homeassistant.components import media_source
from homeassistant.components.media_player import MediaPlayerEntity as MediaPlayerDevice
from homeassistant.components.media_player.browse_media import (
    async_process_play_media_url,
)
from homeassistant.components.media_player.const import (
    ATTR_MEDIA_ANNOUNCE,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
    RepeatMode,
)
from homeassistant.const import CONF_EMAIL, CONF_NAME, CONF_PASSWORD, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.event import async_call_later
from homeassistant.util import slugify

from . import (
    CONF_PUBLIC_URL,
    CONF_QUEUE_DELAY,
    DATA_ALEXAMEDIA,
    DEFAULT_PUBLIC_URL,
    DEFAULT_QUEUE_DELAY,
    DOMAIN as ALEXA_DOMAIN,
    hide_email,
    hide_serial,
)
from .alexa_media import AlexaMedia
from .const import (
    DEPENDENT_ALEXA_COMPONENTS,
    MIN_TIME_BETWEEN_FORCED_SCANS,
    MIN_TIME_BETWEEN_SCANS,
    MODEL_IDS,
    PLAY_SCAN_INTERVAL,
    PUBLIC_URL_ERROR_MESSAGE,
    STREAMING_ERROR_MESSAGE,
    UPLOAD_PATH,
)
from .exceptions import TimeoutException
from .helpers import _catch_login_errors, add_devices

SUPPORT_ALEXA = (
    MediaPlayerEntityFeature.PAUSE
    | MediaPlayerEntityFeature.SEEK
    | MediaPlayerEntityFeature.PREVIOUS_TRACK
    | MediaPlayerEntityFeature.NEXT_TRACK
    | MediaPlayerEntityFeature.STOP
    | MediaPlayerEntityFeature.VOLUME_SET
    | MediaPlayerEntityFeature.PLAY
    | MediaPlayerEntityFeature.PLAY_MEDIA
    | MediaPlayerEntityFeature.TURN_OFF
    | MediaPlayerEntityFeature.TURN_ON
    | MediaPlayerEntityFeature.VOLUME_MUTE
    | MediaPlayerEntityFeature.SELECT_SOURCE
    | MediaPlayerEntityFeature.SHUFFLE_SET
    | MediaPlayerEntityFeature.REPEAT_SET
)

TRANSPORT_FEATURES: dict[str, MediaPlayerEntityFeature] = {
    "next": MediaPlayerEntityFeature.NEXT_TRACK,
    "previous": MediaPlayerEntityFeature.PREVIOUS_TRACK,
    "shuffle": MediaPlayerEntityFeature.SHUFFLE_SET,
    "repeat": MediaPlayerEntityFeature.REPEAT_SET,
    "seekForward": MediaPlayerEntityFeature.SEEK,
    "seekBackward": MediaPlayerEntityFeature.SEEK,
}

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = [ALEXA_DOMAIN]


async def create_www_directory(hass: HomeAssistant):
    """Create www directory."""
    paths = [
        hass.config.path("www"),  # http://homeassistant.local:8123/local
        hass.config.path(
            UPLOAD_PATH
        ),  # http://homeassistant.local:8123/local/alexa_tts
    ]

    def mkdir() -> None:
        """Create a directory."""
        for path in paths:
            if not os.path.exists(path):
                _LOGGER.debug("Creating directory: %s", path)
                os.makedirs(path, exist_ok=True)

    await hass.async_add_executor_job(mkdir)


# @retry_async(limit=5, delay=2, catch_exceptions=True)
async def async_setup_platform(hass, config, add_devices_callback, discovery_info=None):
    """Set up the Alexa media player platform."""
    await create_www_directory(hass)

    devices = []  # type: List[AlexaClient]
    account = None
    if config:
        account = config.get(CONF_EMAIL)
    if account is None and discovery_info:
        account = discovery_info.get("config", {}).get(CONF_EMAIL)
    if account is None:
        raise ConfigEntryNotReady
    account_dict = hass.data[DATA_ALEXAMEDIA]["accounts"][account]
    entry_setup = len(account_dict["entities"]["media_player"])
    media_players = account_dict["devices"]["media_player"]
    alexa_client = None
    # Make clusterMembers list from parentClusters
    for key, device in media_players.items():
        if parent_clusters := device.get("parentClusters"):
            for parent_id in parent_clusters:
                if media_players.get(parent_id):
                    if media_players[parent_id].get("clusterMembers") is None:
                        media_players[parent_id]["clusterMembers"] = []
                    if key not in media_players[parent_id]["clusterMembers"]:
                        media_players[parent_id]["clusterMembers"].append(key)
    for key, device in media_players.items():
        if key not in account_dict["entities"]["media_player"]:
            alexa_client = AlexaClient(
                device,
                account_dict["login_obj"],
                hass.data[DATA_ALEXAMEDIA]["accounts"][account]["second_account_index"],
            )
            await alexa_client.init(device)
            devices.append(alexa_client)
            (
                hass.data[DATA_ALEXAMEDIA]["accounts"][account]["entities"][
                    "media_player"
                ][key]
            ) = alexa_client
        else:
            _LOGGER.debug(
                "%s: Skipping already added device: %s:%s",
                hide_email(account),
                hide_serial(key),
                alexa_client,
            )
    result = await add_devices(hide_email(account), devices, add_devices_callback)
    if result and entry_setup:
        _LOGGER.debug("Detected config entry already setup, using load platform")
        for component in DEPENDENT_ALEXA_COMPONENTS:
            hass.async_create_task(
                async_load_platform(
                    hass,
                    component,
                    ALEXA_DOMAIN,
                    {CONF_NAME: ALEXA_DOMAIN, "config": config},
                    config,
                )
            )
    return result


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Set up the Alexa media player platform by config_entry."""
    if await async_setup_platform(
        hass, config_entry.data, async_add_devices, discovery_info=None
    ):
        account = config_entry.data[CONF_EMAIL]
        account_dict = hass.data[DATA_ALEXAMEDIA]["accounts"][account]
        for component in DEPENDENT_ALEXA_COMPONENTS:
            try:
                entry_setup = len(account_dict["entities"][component])
            except (TypeError, KeyError):
                entry_setup = 1
            if entry_setup or component == "notify":
                _LOGGER.debug("%s: Loading %s", hide_email(account), component)
                cleaned_config = config_entry.data.copy()
                cleaned_config.pop(CONF_PASSWORD, None)
                # CONF_PASSWORD contains sensitive info which is no longer needed
                hass.async_create_task(
                    async_load_platform(
                        hass,
                        component,
                        ALEXA_DOMAIN,
                        {CONF_NAME: ALEXA_DOMAIN, "config": cleaned_config},
                        cleaned_config,
                    )
                )
            else:
                _LOGGER.debug(
                    "%s: Loading config entry for %s", hide_email(account), component
                )
                try:
                    await hass.config_entries.async_forward_entry_setups(
                        config_entry, [component]
                    )
                except (asyncio.TimeoutError, TimeoutException) as ex:
                    raise ConfigEntryNotReady(
                        f"Timeout while loading config entry for {component}"
                    ) from ex
        return True
    raise ConfigEntryNotReady


async def async_unload_entry(hass, entry) -> bool:
    """Unload a config entry."""
    account = entry.data[CONF_EMAIL]
    _LOGGER.debug("%s: Attempting to unload media players", hide_email(account))
    account_dict = hass.data[DATA_ALEXAMEDIA]["accounts"][account]
    for device in account_dict["entities"]["media_player"].values():
        _LOGGER.debug("%s: Removing %s", hide_email(account), device)
        await device.async_remove()
    return True


class AlexaClient(MediaPlayerDevice, AlexaMedia):
    """Representation of a Alexa device."""

    def __init__(self, device, login, second_account_index=0):
        """Initialize the Alexa device."""
        super().__init__(self, login)

        # Logged in info
        self._authenticated = None
        self._can_access_prime_music = None
        self._customer_email = None
        self._customer_id = None
        self._customer_name = None

        # Device info
        self._device = device
        self._device_name = None
        self._device_serial_number = None
        self._device_type = None
        self._device_family = None
        self._device_owner_customer_id = None
        self._software_version = None
        self._available = None
        self._assumed_state = False
        self._capabilities = []
        self._cluster_members = []
        self._locale = None
        # Media
        self._session = None
        self._media_duration = None
        self._media_image_url = None
        self._media_title = None
        self._media_pos = None
        self._media_album_name = None
        self._media_artist = None
        self._media_player_state = None
        self._media_is_muted = False
        self._media_vol_level = None
        self._previous_volume = None
        self._saved_volume = None
        self._source = None
        self._source_list = []
        self._connected_bluetooth = None
        self._bluetooth_list = []
        self._history_records = []
        self._shuffle = None
        self._repeat = None
        self._playing_parent = None
        self._player_info = None
        self._waiting_media_id = None
        # Last Device
        self._last_called = None
        self._last_called_timestamp = None
        self._last_called_summary = None
        # Do not Disturb state
        self._dnd = None
        # Polling state
        self._should_poll = True
        self._last_update = util.utcnow()
        self._listener = None
        self._bluetooth_state = None
        self._app_device_list = None
        self._parent_clusters = None
        self._timezone = None
        self._second_account_index = second_account_index

        self._prev_state = None
        self._state_call_later_cancel = None

        self._attr_supported_features = SUPPORT_ALEXA

    async def init(self, device):
        """Initialize."""
        await self.refresh(device, skip_api=True)

    async def async_added_to_hass(self):
        """Perform tasks after loading."""
        # Register event handler on bus
        await self.refresh(self._device)
        self._listener = async_dispatcher_connect(
            self.hass,
            f"{ALEXA_DOMAIN}_{hide_email(self._login.email)}"[0:32],
            self._handle_event,
        )
        # Register to coordinator:
        email = self._login.email
        coordinator = self.hass.data[DATA_ALEXAMEDIA]["accounts"][email].get(
            "coordinator"
        )
        if coordinator:
            coordinator.async_add_listener(self.update)

    async def async_will_remove_from_hass(self):
        """Prepare to remove entity."""
        # Register event handler on bus
        self._listener()
        email = self._login.email
        coordinator = self.hass.data[DATA_ALEXAMEDIA]["accounts"][email].get(
            "coordinator"
        )
        if coordinator:
            try:
                coordinator.async_remove_listener(self.update)
            except AttributeError:
                pass  # ignore missing listener

    async def _handle_event(self, event):
        # pylint: disable=too-many-branches,too-many-statements
        """Handle events.

        This will update last_called and player_state events.
        Each MediaClient reports if it's the last_called MediaClient and will
        listen for HA events to determine it is the last_called.
        When polling instead of websockets, all devices on same account will
        update to handle starting music with other devices. If websocket is on
        only the updated alexa will update.
        Last_called events are only sent if it's a new device or timestamp.
        Without polling, we must schedule the HA update manually.
        https://developers.home-assistant.io/docs/en/entity_index.html#subscribing-to-updates
        The difference between self.update and self.schedule_update_ha_state
        is self.update will pull data from Amazon, while schedule_update
        assumes the MediaClient state is already updated.
        """

        async def _refresh_if_no_audiopush(already_refreshed=False):
            email = self._login.email
            seen_commands = (
                self.hass.data[DATA_ALEXAMEDIA]["accounts"][email][
                    "websocket_commands"
                ].keys()
                if "websocket_commands"
                in (self.hass.data[DATA_ALEXAMEDIA]["accounts"][email])
                else None
            )
            if (
                not already_refreshed
                and seen_commands
                and not (
                    "PUSH_AUDIO_PLAYER_STATE" in seen_commands
                    or "PUSH_MEDIA_CHANGE" in seen_commands
                    or "PUSH_MEDIA_PROGRESS_CHANGE" in seen_commands
                )
            ):
                # force refresh if player_state update not found, see #397
                _LOGGER.debug(
                    "%s: No PUSH_AUDIO_PLAYER_STATE/"
                    "PUSH_MEDIA_CHANGE/PUSH_MEDIA_PROGRESS_CHANGE in %s;"
                    "forcing refresh",
                    hide_email(email),
                    seen_commands,
                )
                await self.async_update()

        async def _wait_player_info(media_id, timeout=3):
            self._player_info = None
            start = util.dt.as_timestamp(util.utcnow())
            while (
                self._player_info is None
                and media_id == self._waiting_media_id
                and (start + timeout >= util.dt.as_timestamp(util.utcnow()))
            ):
                await asyncio.sleep(0.1)

        try:
            if not self.enabled:
                return
        except AttributeError:
            pass
        already_refreshed = False
        event_serial = None
        info_changed = False
        if "last_called_change" in event:
            event_serial = (
                event["last_called_change"]["serialNumber"]
                if event["last_called_change"]
                else None
            )
        elif "bluetooth_change" in event:
            event_serial = (
                event["bluetooth_change"]["deviceSerialNumber"]
                if event["bluetooth_change"]
                else None
            )
        elif "player_state" in event:
            event_serial = (
                event["player_state"]["dopplerId"]["deviceSerialNumber"]
                if event["player_state"]
                else None
            )
        elif "queue_state" in event:
            event_serial = (
                event["queue_state"]["dopplerId"]["deviceSerialNumber"]
                if event["queue_state"]
                else None
            )
        elif "push_activity" in event:
            event_serial = (
                event.get("push_activity", {}).get("key", {}).get("serialNumber")
            )
        elif "now_playing" in event:
            player_info = (
                event.get("now_playing", {})
                .get("update", {})
                .get("update", {})
                .get("nowPlayingData", {})
            )
            media_id = player_info.get("mediaId")
            if self._waiting_media_id and media_id in self._waiting_media_id:
                if player_info.get("playerState"):
                    player_info["state"] = player_info["playerState"]
                if player_info.get("progress", {}).get("mediaLength"):
                    player_info["progress"]["mediaLength"] = int(
                        player_info["progress"]["mediaLength"] / 1000
                    )
                    # Get and set mediaProgress only when mediaLength is obtained.
                    # Fixed an issue where mediaLength was sometimes acquired as 0 on Spotify etc.,
                    # causing the progress bar to disappear.
                    if player_info.get("progress", {}).get("mediaProgress") is not None:
                        player_info["progress"]["mediaProgress"] = int(
                            player_info["progress"]["mediaProgress"] / 1000
                        )
                if player_info.get("mainArt", {}).get("url") is None:
                    if not player_info.get("mainArt"):
                        player_info["mainArt"] = {}
                    player_info["mainArt"]["url"] = player_info["mainArt"].get(
                        "fullUrl"
                    )
                player_info["last_update"] = util.utcnow()
                event_serial = self.device_serial_number
                _LOGGER.debug(
                    f"Match media_id: {media_id} in waiting_media_id:{self._waiting_media_id} , player_info: {player_info}"
                )
                self._player_info = player_info
                info_changed = True
        elif "parent_state" in event:
            event_serial = (
                event.get("parent_state", {})
                .get("dopplerId", {})
                .get("deviceSerialNumber")
            )
            if event_serial == self.device_serial_number:
                _LOGGER.debug(
                    "DeviceID(%s) receive event form parent: %s",
                    hide_serial(event_serial),
                    hide_serial(event),
                )
                parent_state = event.get("parent_state", {})
                if parent_state.get("volume") is None:
                    parent_state["volume"] = {
                        "muted": self._media_is_muted,
                        "volume": self._media_vol_level,
                    }
                self._set_attrs(parent_state)
                self._player_info = parent_state
                if parent_state.get("state") == "PLAYING" and (
                    parentSerial := (
                        event.get("parent_state", {})
                        .get("dopplerId", {})
                        .get("parentSerialNumber")
                    )
                ):
                    self._playing_parent = self.hass.data[DATA_ALEXAMEDIA]["accounts"][
                        self._login.email
                    ]["entities"]["media_player"].get(parentSerial)
                else:
                    self._playing_parent = None
                info_changed = True
        if not event_serial:
            return
        if event_serial == self.device_serial_number:
            self._available = True
            self.schedule_update_ha_state()
        if "last_called_change" in event:
            if (
                event_serial == self.device_serial_number
                or any(
                    item["serialNumber"] == event_serial
                    for item in self._app_device_list
                )
                and self._last_called_timestamp
                != event["last_called_change"]["timestamp"]
            ):
                _LOGGER.debug(
                    "%s: %s is last_called: %s",
                    hide_email(self._login.email),
                    self,
                    hide_serial(self.device_serial_number),
                )
                self._last_called = True
                self._last_called_timestamp = event["last_called_change"]["timestamp"]
                self._last_called_summary = event["last_called_change"].get("summary")
                if self.hass and self.schedule_update_ha_state:
                    self.schedule_update_ha_state()
                await self._update_notify_targets()
            else:
                self._last_called = False
            if self.hass and self.async_schedule_update_ha_state:
                email = self._login.email
                force_refresh = not (
                    self.hass.data[DATA_ALEXAMEDIA]["accounts"][email]["http2"]
                )
                self.async_schedule_update_ha_state(force_refresh=force_refresh)
            if self._last_called:
                self.hass.bus.async_fire(
                    "alexa_media_last_called_event",
                    {
                        "last_called": self.device_serial_number,
                        "timestamp": self._last_called_timestamp,
                        "summary": self._last_called_summary,
                    },
                )
        elif "bluetooth_change" in event:
            if event_serial == self.device_serial_number:
                _LOGGER.debug(
                    "%s: %s bluetooth_state update: %s",
                    hide_email(self._login.email),
                    self.name,
                    hide_serial(event["bluetooth_change"]),
                )
                self._bluetooth_state = event["bluetooth_change"]
                # the setting of bluetooth_state is not consistent as this
                # takes from the event instead of the hass storage. We're
                # setting the value twice. Architecturally we should have a
                # single authoritative source of truth.
                self._source = self._get_source()
                self._source_list = self._get_source_list()
                self._connected_bluetooth = self._get_connected_bluetooth()
                self._bluetooth_list = self._get_bluetooth_list()
                if self.hass and self.schedule_update_ha_state:
                    self.schedule_update_ha_state()
        elif "player_state" in event:
            player_state = event["player_state"]
            if event_serial == self.device_serial_number:
                if "audioPlayerState" in player_state:
                    _LOGGER.debug(
                        "%s: %s state update: %s",
                        hide_email(self._login.email),
                        self.name,
                        player_state["audioPlayerState"],
                    )
                    if player_state["audioPlayerState"] == "PLAYING":
                        self._media_player_state = "PLAYING"
                    elif player_state["audioPlayerState"] == "INTERRUPTED":
                        self._clear_media_details()
                    media_id = player_state.get("mediaReferenceId")
                    if media_id:
                        self._waiting_media_id = media_id
                        await _wait_player_info(media_id)
                        if self._waiting_media_id != media_id:
                            return
                    if not media_id and self._player_info is None:
                        # allow delay before trying to refresh to avoid http 400 errors
                        await asyncio.sleep(2)
                    await self.async_update()
                    already_refreshed = True
                elif "mediaReferenceId" in player_state:
                    _LOGGER.debug(
                        "%s: %s media update: %s",
                        hide_email(self._login.email),
                        self.name,
                        player_state["mediaReferenceId"],
                    )
                    await self.async_update()
                    already_refreshed = True
                elif "volumeSetting" in player_state:
                    _LOGGER.debug(
                        "%s: %s volume updated: %s",
                        hide_email(self._login.email),
                        self.name,
                        player_state["volumeSetting"],
                    )
                    if self._session:
                        if not self._session.get("volume"):
                            self._session["volume"] = {}
                        self._session["volume"]["volume"] = player_state[
                            "volumeSetting"
                        ]
                        self._session["volume"]["muted"] = player_state.get(
                            "isMuted", False
                        )
                        self._media_is_muted = self._session["volume"]["muted"]
                    self._media_vol_level = player_state["volumeSetting"] / 100
                    if self.hass and self.schedule_update_ha_state:
                        self.schedule_update_ha_state()
                elif "dopplerConnectionState" in player_state:
                    self.available = player_state["dopplerConnectionState"] == "ONLINE"
                    if self.hass and self.schedule_update_ha_state:
                        self.schedule_update_ha_state()
                await _refresh_if_no_audiopush(already_refreshed)
        elif "push_activity" in event:
            if self.state in {
                MediaPlayerState.IDLE,
                MediaPlayerState.PAUSED,
                MediaPlayerState.PLAYING,
            }:
                _LOGGER.debug(
                    "%s: %s checking for potential state update due to push activity on %s",
                    hide_email(self._login.email),
                    self.name,
                    hide_serial(event_serial),
                )
                # allow delay before trying to refresh to avoid http 400 errors
                await asyncio.sleep(2)
                await self.async_update()
                already_refreshed = True

        if info_changed and self._player_info and self._cluster_members:
            # This is Speaker Group or Speaker pair so throw event data
            if self.hass:
                for device_id in self._cluster_members:
                    json_payload = self._make_dispatcher_data(
                        self._player_info, device_id
                    )
                    _LOGGER.debug(
                        "Updating player info by parent (http2): %s",
                        hide_serial(json_payload),
                    )
                    async_dispatcher_send(
                        self.hass,
                        f"{ALEXA_DOMAIN}_{hide_email(self._login.email)}"[0:32],
                        {"parent_state": json_payload},
                    )

        if "queue_state" in event:
            queue_state = event["queue_state"]
            if event_serial == self.device_serial_number:
                if (
                    "trackOrderChanged" in queue_state
                    and not queue_state["trackOrderChanged"]
                    and "loopMode" in queue_state
                ):
                    self._attr_supported_features |= MediaPlayerEntityFeature.REPEAT_SET
                    self._repeat = queue_state["loopMode"] == "LOOP_QUEUE"
                    self._attr_repeat = (
                        RepeatMode.ALL if self._repeat else RepeatMode.OFF
                    )
                    _LOGGER.debug(
                        "%s: %s repeat updated to: %s %s",
                        hide_email(self._login.email),
                        self.name,
                        self._repeat,
                        queue_state["loopMode"],
                    )
                elif "playBackOrder" in queue_state:
                    self._attr_supported_features |= (
                        MediaPlayerEntityFeature.SHUFFLE_SET
                    )
                    self._shuffle = queue_state["playBackOrder"] == "SHUFFLE_ALL"
                    _LOGGER.debug(
                        "%s: %s shuffle updated to: %s %s",
                        hide_email(self._login.email),
                        self.name,
                        self._shuffle,
                        queue_state["playBackOrder"],
                    )
                await _refresh_if_no_audiopush(already_refreshed)

    def _make_dispatcher_data(
        self, player_info: dict[str, Any], device_id: str
    ) -> dict[str, Any]:
        """Rewrite data that propagates downstream"""
        json_payload = player_info.copy()
        json_payload["dopplerId"] = {
            "deviceSerialNumber": device_id,
            "parentSerialNumber": self._device_serial_number,
        }
        json_payload["isPlayingInLemur"] = False
        json_payload["lemurVolume"] = None
        json_payload["volume"] = None
        return json_payload

    def _clear_media_details(self):
        """Set all Media Items to None."""
        # General
        self._media_duration = None
        self._media_image_url = None
        self._media_title = None
        self._media_pos = None
        self._media_album_name = None
        self._media_artist = None
        self._media_player_state = "IDLE"
        self._media_is_muted = False
        # volume is also used for announce/tts so state should remain
        # self._media_vol_level = None
        self._attr_supported_features = SUPPORT_ALEXA
        self._player_info = None

    def _set_authentication_details(self, auth):
        """Set Authentication based off auth."""
        self._authenticated = auth["authenticated"]
        self._can_access_prime_music = auth["canAccessPrimeMusicContent"]
        self._customer_email = auth["customerEmail"]
        self._customer_id = auth["customerId"]
        self._customer_name = auth["customerName"]

    @util.Throttle(MIN_TIME_BETWEEN_SCANS, MIN_TIME_BETWEEN_FORCED_SCANS)
    async def _api_get_state(self):
        return await self.alexa_api.get_state()

    @_catch_login_errors
    async def refresh(self, device=None, skip_api: bool = False, no_throttle=False):
        # pylint: disable=too-many-branches,too-many-statements
        """Refresh device data.

        This is a per device refresh and for many Alexa devices can result in
        many refreshes from each individual device. This will call the
        AlexaAPI directly.

        Args:
        device (json): A refreshed device json from Amazon. For efficiency,
                       an individual device does not refresh if it's reported
                       as offline.
        skip_api (bool): Whether to only due a device json update and not hit the API

        """
        if device is not None:
            self._device_name = device["accountName"]
            self._device_family = device["deviceFamily"]
            self._device_type = device["deviceType"]
            self._device_serial_number = device["serialNumber"]
            self._app_device_list = device["appDeviceList"]
            self._device_owner_customer_id = device["deviceOwnerCustomerId"]
            self._software_version = device["softwareVersion"]
            self._available = device["online"]
            self._capabilities = device["capabilities"]
            self._cluster_members = device["clusterMembers"]
            self._parent_clusters = device["parentClusters"]
            self._bluetooth_state = device.get("bluetooth_state", {})
            self._locale = device["locale"] if "locale" in device else "en-US"
            self._timezone = device["timeZoneId"] if "timeZoneId" in device else "UTC"
            self._dnd = device["dnd"] if "dnd" in device else None
            self._set_authentication_details(device["auth_info"])
        session = None
        api_call = False
        if self.available:
            _LOGGER.debug(
                "%s: Refreshing %s",
                self.account,
                self if device is None else self._device_name,
            )
            self._assumed_state = False
            if "PAIR_BT_SOURCE" in self._capabilities:
                self._source = self._get_source()
                self._source_list = self._get_source_list()
                self._connected_bluetooth = self._get_connected_bluetooth()
                self._bluetooth_list = self._get_bluetooth_list()
            new_last_called = self._get_last_called()
            if new_last_called and self._last_called != new_last_called:
                self._last_called = new_last_called
                self._last_called_timestamp = self.hass.data[DATA_ALEXAMEDIA][
                    "accounts"
                ][self._login.email]["last_called"]["timestamp"]
                self._last_called_summary = self.hass.data[DATA_ALEXAMEDIA]["accounts"][
                    self._login.email
                ]["last_called"].get("summary")
                await self._update_notify_targets()
            if skip_api and self.hass:
                self.schedule_update_ha_state()
                return
            if "MUSIC_SKILL" in self._capabilities:
                if self._parent_clusters and self.hass:
                    playing_parents = list(
                        filter(
                            lambda x: (
                                self.hass.data[DATA_ALEXAMEDIA]["accounts"][
                                    self._login.email
                                ]["entities"]["media_player"].get(x)
                                and self.hass.data[DATA_ALEXAMEDIA]["accounts"][
                                    self._login.email
                                ]["entities"]["media_player"][x].state
                                == MediaPlayerState.PLAYING
                            ),
                            self._parent_clusters,
                        )
                    )
                else:
                    playing_parents = []
                parent_session = {}
                if playing_parents:
                    if len(playing_parents) > 1:
                        _LOGGER.warning(
                            "Found multiple playing parents please file an issue"
                        )
                    parent = self.hass.data[DATA_ALEXAMEDIA]["accounts"][
                        self._login.email
                    ]["entities"]["media_player"][playing_parents[0]]
                    self._playing_parent = parent
                    parent_session = parent.session
                if parent_session:
                    session = parent_session.copy()
                    session["isPlayingInLemur"] = False
                    session["lemurVolume"] = None
                    session["volume"] = (
                        parent_session["lemurVolume"]["memberVolume"][
                            self.device_serial_number
                        ]
                        if parent_session.get("lemurVolume")
                        and parent_session.get("lemurVolume", {})
                        .get("memberVolume", {})
                        .get(self.device_serial_number)
                        else session["volume"]
                    )
                    session = {"playerInfo": session}
                else:
                    self._playing_parent = None
                    if self._player_info:
                        _player_info = self._player_info.copy()
                        if self._session:
                            _player_info["volume"] = self._session.get("volume", {})
                        session = {"playerInfo": _player_info}
                    else:
                        session = await self._api_get_state(no_throttle=no_throttle)
                        _LOGGER.debug("Returned data of _api_get_state(): %s", session)
                        api_call = True
                        if (
                            session is None
                            or session.get("playerInfo", {}).get("state") is None
                        ):
                            # _LOGGER.warning(
                            #     "%s: Can't get session state by alexa_api.get_state() of %s. Probably a re-login occurred, so ignore it this time.",
                            #     self.account,
                            #     self if device is None else self._device_name,
                            # )
                            return
        self._clear_media_details()
        # update the session if it exists
        self._session = session.get("playerInfo") if session else None
        if self._session:
            if self._session.get("isPlayingInLemur"):
                if menbers_volume := self._session.get("lemurVolume", {}).get(
                    "memberVolume"
                ):
                    if self.hass:
                        for device_id in self._cluster_members:
                            json_payload = self._make_dispatcher_data(
                                self._session, device_id
                            )
                            json_payload["volume"] = menbers_volume.get(device_id)
                            _LOGGER.debug(
                                "Updating player info by parent (API Call): %s",
                                hide_serial(json_payload),
                            )
                            async_dispatcher_send(
                                self.hass,
                                f"{ALEXA_DOMAIN}_{hide_email(self._login.email)}"[0:32],
                                {"parent_state": json_payload},
                            )

            if _transport := self._session.get("transport"):
                if not api_call:
                    # API calls do not return correct values for "shuffle" and "repeat"
                    self._shuffle = (
                        _transport["shuffle"] == "SELECTED"
                        if (
                            "shuffle" in _transport
                            and _transport["shuffle"] not in ("DISABLED", "HIDDEN")
                        )
                        else None
                    )
                    self._repeat = (
                        _transport["repeat"] == "SELECTED"
                        if (
                            "repeat" in _transport
                            and _transport["repeat"] not in ("DISABLED", "HIDDEN")
                        )
                        else None
                    )
                    self._attr_repeat = (
                        RepeatMode.ALL if self._repeat else RepeatMode.OFF
                    )
                self._attr_supported_features = SUPPORT_ALEXA
                for transport_key, feature in TRANSPORT_FEATURES.items():
                    if api_call and transport_key in ("shuffle", "repeat"):
                        # API calls do not return correct values for "shuffle" and "repeat"
                        continue
                    if _transport.get(transport_key) in (
                        "DISABLED",
                        "HIDDEN",
                        None,
                    ) and self._attr_supported_features == (
                        self._attr_supported_features | feature
                    ):
                        self._attr_supported_features ^= feature

            if self._session.get("state"):
                self._set_attrs(self._session)
                # Safely access 'http2' setting
                push_disabled = self.hass and not (
                    self.hass.data.get(DATA_ALEXAMEDIA, {})
                    .get("accounts", {})
                    .get(self._login.email, {})
                    .get("http2")
                )
                if (
                    push_disabled
                    and self.hass
                    and self._session.get("isPlayingInLemur")
                ):
                    asyncio.gather(
                        *map(
                            lambda x: (
                                self.hass.data[DATA_ALEXAMEDIA]["accounts"][
                                    self._login.email
                                ]["entities"]["media_player"][x].async_update()
                            ),
                            filter(
                                lambda x: (
                                    self.hass.data[DATA_ALEXAMEDIA]["accounts"][
                                        self._login.email
                                    ]["entities"]["media_player"].get(x)
                                    and self.hass.data[DATA_ALEXAMEDIA]["accounts"][
                                        self._login.email
                                    ]["entities"]["media_player"][x].available
                                ),
                                self._cluster_members,
                            ),
                        )
                    )
        if self.hass:
            self.schedule_update_ha_state()

    @property
    def source(self):
        """Return the current input source."""
        return self._source

    @property
    def source_list(self):
        """List of available input sources."""
        return self._source_list

    @_catch_login_errors
    async def async_select_source(self, source):
        """Select input source."""
        if source == "Local Speaker":
            if self.hass:
                self.hass.async_create_task(self.alexa_api.disconnect_bluetooth())
            else:
                await self.alexa_api.disconnect_bluetooth()
            self._source = "Local Speaker"
        elif self._bluetooth_state.get("pairedDeviceList"):
            for devices in self._bluetooth_state["pairedDeviceList"]:
                if devices["friendlyName"] == source:
                    if self.hass:
                        self.hass.async_create_task(
                            self.alexa_api.set_bluetooth(devices["address"])
                        )
                    else:
                        await self.alexa_api.set_bluetooth(devices["address"])
                    self._source = source
        # Safely access 'http2' setting
        if not (
            self.hass.data.get(DATA_ALEXAMEDIA, {})
            .get("accounts", {})
            .get(self._login.email, {})
            .get("http2")
        ):
            await self.async_update()

    def _get_source(self):
        source = "Local Speaker"
        if self._bluetooth_state.get("pairedDeviceList"):
            for device in self._bluetooth_state["pairedDeviceList"]:
                if (
                    device["connected"] is True
                    and device["friendlyName"] in self.source_list
                ):
                    return device["friendlyName"]
        return source

    def _get_source_list(self):
        sources = []
        if self._bluetooth_state.get("pairedDeviceList"):
            for devices in self._bluetooth_state["pairedDeviceList"]:
                if devices["profiles"] and "A2DP-SOURCE" in devices["profiles"]:
                    sources.append(devices["friendlyName"])
        return ["Local Speaker"] + sources

    def _get_connected_bluetooth(self):
        source = None
        if self._bluetooth_state.get("pairedDeviceList"):
            for device in self._bluetooth_state["pairedDeviceList"]:
                if device["connected"] is True:
                    return device["friendlyName"]
        return source

    def _get_bluetooth_list(self):
        sources = []
        if self._bluetooth_state.get("pairedDeviceList"):
            for devices in self._bluetooth_state["pairedDeviceList"]:
                sources.append(devices["friendlyName"])
        return sources

    def _get_last_called(self):
        try:
            last_called_serial = (
                None
                if self.hass is None
                else (
                    self.hass.data[DATA_ALEXAMEDIA]["accounts"][self._login.email][
                        "last_called"
                    ]["serialNumber"]
                )
            )
        except (TypeError, KeyError):
            last_called_serial = None
        _LOGGER.debug(
            "%s: %s: Last_called check: self: %s reported: %s",
            hide_email(self._login.email),
            self._device_name,
            hide_serial(self._device_serial_number),
            hide_serial(last_called_serial),
        )
        return last_called_serial is not None and (
            self._device_serial_number == last_called_serial
            or any(
                item["serialNumber"] == last_called_serial
                for item in self._app_device_list
            )
        )

    def _set_attrs(self, player_info):
        """Set player attributes by player info dict."""
        self._media_player_state = player_info.get("state")
        self._media_title = player_info.get("infoText", {}).get("title")
        self._media_artist = player_info.get("infoText", {}).get("subText1")
        self._media_album_name = player_info.get("infoText", {}).get("subText2")
        self._media_image_url = player_info.get("mainArt", {}).get("url")
        self._media_pos = player_info.get("progress", {}).get("mediaProgress")
        self._media_duration = player_info.get("progress", {}).get("mediaLength")
        muted = volume = None
        if not player_info.get("lemurVolume"):
            if player_info.get("volume") is not None:
                volume_info = player_info.get("volume", {})
                muted = volume_info.get("muted")
                volume = volume_info.get("volume")
        else:
            if player_info.get("lemurVolume") is not None:
                composite = player_info.get("lemurVolume", {}).get(
                    "compositeVolume", {}
                )
                muted = composite.get("muted")
                volume = composite.get("volume")
        if muted is not None:
            self._media_is_muted = muted
        if volume is not None and isinstance(volume, (int, float)):
            if isinstance(volume, int) or volume > 1:
                self._media_vol_level = volume / 100
            else:
                self._media_vol_level = float(volume)

    @property
    def available(self):
        """Return the availability of the client."""
        return self._available

    @available.setter
    def available(self, state):
        """Set the availability state."""
        self._available = state

    @property
    def assumed_state(self):
        """Return whether the state is an assumed_state."""
        return self._assumed_state

    @property
    def hidden(self):
        """Return whether the sensor should be hidden."""
        return "MUSIC_SKILL" not in self._capabilities

    @property
    def unique_id(self):
        """Return the id of this Alexa client."""
        email = self._login.email
        return (
            slugify(f"{self.device_serial_number}_{email}")
            if self._second_account_index
            else self.device_serial_number
        )

    @property
    def name(self):
        """Return the name of the device."""
        return self._device_name

    @property
    def device_serial_number(self):
        """Return the machine identifier of the device."""
        return self._device_serial_number

    @property
    def session(self):
        """Return the session, if any."""
        return self._session

    @property
    def state(self):
        """Return the state of the device."""
        if not self.available:
            return STATE_UNAVAILABLE
        if self._media_player_state == "PLAYING":
            return MediaPlayerState.PLAYING
        if self._media_player_state == "PAUSED":
            return MediaPlayerState.PAUSED
        if self._media_player_state == "IDLE":
            return MediaPlayerState.IDLE
        return MediaPlayerState.IDLE

    def update(self):
        """Get the latest details on a media player synchronously."""
        return
        # return self.hass.add_job(async_update)

    @_catch_login_errors
    async def async_update(self):
        """Get the latest details on a media player.

        Because media players spend the majority of time idle, an adaptive
        update should be used to avoid flooding Amazon focusing on known
        play states. An initial version included an update_devices call on
        every update. However, this quickly floods the network for every new
        device added. This should only call refresh() to call the AlexaAPI.
        """
        try:
            if not self.enabled:
                return
        except AttributeError:
            pass
        email = self._login.email

        # Check if DATA_ALEXAMEDIA and 'accounts' exist
        accounts_data = self.hass.data.get(DATA_ALEXAMEDIA, {}).get("accounts", {})
        if (
            self.entity_id is None  # Device has not initialized yet
            or email not in accounts_data
            or self._login.session.closed
        ):
            self._assumed_state = True
            self.available = False
            return

        # Safely access the device
        device = accounts_data[email]["devices"]["media_player"].get(
            self.device_serial_number
        )
        if not device:
            _LOGGER.warning(
                "Device serial number %s not found for account %s. Skipping update.",
                self.device_serial_number,
                hide_email(email),
            )
            self.available = False
            return

        # Safely access websocket_commands
        seen_commands = (
            accounts_data[email]["websocket_commands"].keys()
            if "websocket_commands" in accounts_data[email]
            else None
        )

        await self.refresh(device, no_throttle=True)

        # Safely access 'http2' setting
        push_enabled = accounts_data[email].get("http2")

        if not push_enabled:
            if (
                self.state in [MediaPlayerState.PLAYING]
                and
                # Only enable polling if websocket not connected
                (
                    not push_enabled
                    or not seen_commands
                    or not (
                        "PUSH_AUDIO_PLAYER_STATE" in seen_commands
                        or "PUSH_MEDIA_CHANGE" in seen_commands
                        or "PUSH_MEDIA_PROGRESS_CHANGE" in seen_commands
                    )
                )
            ):
                self._should_poll = False  # disable polling since manual update
                if (
                    self._last_update == 0
                    or util.dt.as_timestamp(util.utcnow())
                    - util.dt.as_timestamp(self._last_update)
                    > PLAY_SCAN_INTERVAL
                ):
                    _LOGGER.debug(
                        "%s: %s playing; scheduling update in %s seconds",
                        hide_email(email),
                        self.name,
                        PLAY_SCAN_INTERVAL,
                    )
                    async_call_later(
                        self.hass,
                        PLAY_SCAN_INTERVAL,
                        self.async_schedule_update_ha_state,
                    )
            elif self._should_poll:  # Not playing, one last poll
                self._should_poll = False
                if not push_enabled:
                    _LOGGER.debug(
                        "%s: Disabling polling and scheduling last update in 300 seconds for %s",
                        hide_email(email),
                        self.name,
                    )
                    async_call_later(
                        self.hass,
                        300,
                        self.async_schedule_update_ha_state,
                    )
                else:
                    _LOGGER.debug(
                        "%s: Disabling polling for %s",
                        hide_email(email),
                        self.name,
                    )
        else:
            self._should_poll = False
        self._last_update = util.utcnow()
        self.schedule_update_ha_state()

    @property
    def media_content_type(self):
        """Return the content type of current playing media."""
        if self.state in [MediaPlayerState.PLAYING, MediaPlayerState.PAUSED]:
            return MediaType.MUSIC
        return MediaPlayerState.IDLE

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
    def media_position(self):
        """Return the duration of current playing media in seconds."""
        return self._media_pos

    @property
    def media_position_updated_at(self):
        """When was the position of the current playing media valid."""
        return (
            self._player_info["last_update"]
            if self._player_info and self._player_info.get("last_update")
            else self._last_update
        )

    @property
    def media_image_url(self) -> Optional[str]:
        """Return the image URL of current playing media."""
        if self._media_image_url:
            return re.sub("\\(", "%28", re.sub("\\)", "%29", self._media_image_url))
            # fix failure of HA media player ui to quote "(" or ")"
        return None

    @property
    def media_image_remotely_accessible(self):
        """Return whether image is accessible outside of the home network."""
        return bool(self._media_image_url)

    @property
    def media_title(self):
        """Return the title of current playing media."""
        return self._media_title

    @property
    def device_family(self):
        """Return the make of the device (ex. Echo, Other)."""
        return self._device_family

    @property
    def dnd_state(self):
        """Return the Do Not Disturb state."""
        return self._dnd

    @dnd_state.setter
    def dnd_state(self, state):
        """Set the Do Not Disturb state."""
        self._dnd = state

    @_catch_login_errors
    async def async_set_shuffle(self, shuffle):
        """Enable/disable shuffle mode."""
        if self.hass:
            self.hass.async_create_task(self.alexa_api.shuffle(shuffle))
        else:
            await self.alexa_api.shuffle(shuffle)
        self._shuffle = shuffle

    @property
    def shuffle(self):
        """Return the Shuffle state."""
        return self._shuffle

    @shuffle.setter
    def shuffle(self, state):
        """Set the Shuffle state."""
        self._shuffle = state
        self.schedule_update_ha_state()

    @_catch_login_errors
    async def async_set_repeat(self, repeat: RepeatMode) -> None:
        """Set repeat mode."""
        repeat_state = repeat == RepeatMode.ALL
        if self.hass:
            self.hass.async_create_task(self.alexa_api.repeat(repeat_state))
        else:
            await self.alexa_api.repeat(repeat_state)
        self._repeat = repeat_state
        self._attr_repeat = RepeatMode.ALL if self._repeat else RepeatMode.OFF

    @property
    def repeat_state(self):
        """Return the Repeat state."""
        return self._repeat

    @repeat_state.setter
    def repeat_state(self, state):
        """Set the Repeat state."""
        self._repeat = state
        self.schedule_update_ha_state()

    @_catch_login_errors
    async def async_set_volume_level(self, volume):
        """Set volume level, range 0..1."""
        if not self.available:
            return

        # Save the current volume level before we change it
        _LOGGER.debug("Saving previous volume level: %s", self.volume_level)
        self._previous_volume = self.volume_level

        # Change the volume level on the device
        if self.hass:
            self.hass.async_create_task(self.alexa_api.set_volume(volume))
        else:
            await self.alexa_api.set_volume(volume)
        self._media_vol_level = volume

        # Let http2push update the new volume level
        if not (
            self.hass.data[DATA_ALEXAMEDIA]["accounts"][self._login.email]["http2"]
        ):
            # Otherwise we do it ourselves
            await self.async_update()

    @property
    def volume_level(self):
        """Return the volume level of the client (0..1)."""
        return self._media_vol_level

    @property
    def is_volume_muted(self):
        """Return boolean if volume is currently muted."""
        return self._media_is_muted

    @_catch_login_errors
    async def async_mute_volume(self, mute):
        """Mute the volume.

        Since we can't actually mute, we'll:
        - On mute, store volume and set volume to 0
        - On unmute, set volume to previously stored volume
        """
        if not self.available:
            return

        self._media_is_muted = mute
        if mute:
            self._saved_volume = self.volume_level
            if self.hass:
                self.hass.async_create_task(self.alexa_api.set_volume(0))
            else:
                await self.alexa_api.set_volume(0)
        else:
            if self._saved_volume is not None:
                if self.hass:
                    self.hass.async_create_task(
                        self.alexa_api.set_volume(self._saved_volume)
                    )
                else:
                    await self.alexa_api.set_volume(self._saved_volume)
            else:
                if self.hass:
                    self.hass.async_create_task(self.alexa_api.set_volume(50))
                else:
                    await self.alexa_api.set_volume(50)
        if not (
            self.hass.data[DATA_ALEXAMEDIA]["accounts"][self._login.email]["http2"]
        ):
            await self.async_update()

    @_catch_login_errors
    async def async_media_play(self):
        """Send play command."""
        if not (
            self.state in [MediaPlayerState.PLAYING, MediaPlayerState.PAUSED]
            and self.available
        ):
            return
        if self._playing_parent:
            await self._playing_parent.async_media_play()
        else:
            if self.hass:
                self.hass.async_create_task(self.alexa_api.play())
            else:
                await self.alexa_api.play()
        if not (
            self.hass.data[DATA_ALEXAMEDIA]["accounts"][self._login.email]["http2"]
        ):
            await self.async_update()

    @_catch_login_errors
    async def async_media_pause(self):
        """Send pause command."""
        if not (
            self.state in [MediaPlayerState.PLAYING, MediaPlayerState.PAUSED]
            and self.available
        ):
            return
        if self._playing_parent:
            await self._playing_parent.async_media_pause()
        else:
            if self.hass:
                self.hass.async_create_task(self.alexa_api.pause())
            else:
                await self.alexa_api.pause()
        if not (
            self.hass.data[DATA_ALEXAMEDIA]["accounts"][self._login.email]["http2"]
        ):
            await self.async_update()

    @_catch_login_errors
    async def async_media_stop(self):
        """Send stop command."""
        if not self.available:
            return
        if self._playing_parent:
            await self._playing_parent.async_media_stop()
        else:
            if self.hass:
                self.hass.async_create_task(
                    self.alexa_api.stop(
                        customer_id=self._customer_id,
                        queue_delay=self.hass.data[DATA_ALEXAMEDIA]["accounts"][
                            self.email
                        ]["options"][CONF_QUEUE_DELAY],
                    )
                )
            else:
                await self.alexa_api.stop(
                    customer_id=self._customer_id,
                    queue_delay=self.hass.data[DATA_ALEXAMEDIA]["accounts"][self.email][
                        "options"
                    ][CONF_QUEUE_DELAY],
                )
        if not (
            self.hass.data[DATA_ALEXAMEDIA]["accounts"][self._login.email]["http2"]
        ):
            await self.async_update()

    @_catch_login_errors
    async def async_turn_off(self):
        """Turn the client off.

        While Alexa's do not have on/off capability, we can use this as another
        trigger to do updates. For turning off, we can clear media_details.
        """
        self._should_poll = False
        await self.async_media_pause()
        self._clear_media_details()

    @_catch_login_errors
    async def async_turn_on(self):
        """Turn the client on.

        While Alexa's do not have on/off capability, we can use this as another
        trigger to do updates.
        """
        self._should_poll = True
        await self.async_media_pause()

    @_catch_login_errors
    async def async_media_next_track(self):
        """Send next track command."""
        if not (
            self.state in [MediaPlayerState.PLAYING, MediaPlayerState.PAUSED]
            and self.available
        ):
            return
        if self._playing_parent:
            await self._playing_parent.async_media_next_track()
        else:
            if self.hass:
                self.hass.async_create_task(self.alexa_api.next())
            else:
                await self.alexa_api.next()
        if not (
            self.hass.data[DATA_ALEXAMEDIA]["accounts"][self._login.email]["http2"]
        ):
            await self.async_update()

    @_catch_login_errors
    async def async_media_previous_track(self):
        """Send previous track command."""
        if not (
            self.state in [MediaPlayerState.PLAYING, MediaPlayerState.PAUSED]
            and self.available
        ):
            return
        if self._playing_parent:
            await self._playing_parent.async_media_previous_track()
        else:
            if self.hass:
                self.hass.async_create_task(self.alexa_api.previous())
            else:
                await self.alexa_api.previous()
        if not (
            self.hass.data[DATA_ALEXAMEDIA]["accounts"][self._login.email]["http2"]
        ):
            await self.async_update()

    @_catch_login_errors
    async def async_send_tts(self, message, **kwargs):
        """Send TTS to Device.

        NOTE: Does not work on WHA Groups.
        """
        if self.hass:
            self.hass.async_create_task(
                self.alexa_api.send_tts(
                    message, customer_id=self._customer_id, **kwargs
                )
            )
        else:
            await self.alexa_api.send_tts(
                message, customer_id=self._customer_id, **kwargs
            )

    @_catch_login_errors
    async def async_send_announcement(self, message, **kwargs):
        """Send announcement to the media player."""
        if self.hass:
            self.hass.async_create_task(
                self.alexa_api.send_announcement(
                    message, customer_id=self._customer_id, **kwargs
                )
            )
        else:
            await self.alexa_api.send_announcement(
                message, customer_id=self._customer_id, **kwargs
            )

    @_catch_login_errors
    async def async_send_mobilepush(self, message, **kwargs):
        """Send push to the media player's associated mobile devices."""
        if self.hass:
            self.hass.async_create_task(
                self.alexa_api.send_mobilepush(
                    message, customer_id=self._customer_id, **kwargs
                )
            )
        else:
            await self.alexa_api.send_mobilepush(
                message, customer_id=self._customer_id, **kwargs
            )

    @_catch_login_errors
    async def async_send_dropin_notification(self, message, **kwargs):
        """Send notification dropin to the media player's associated mobile devices."""
        if self.hass:
            self.hass.async_create_task(
                self.alexa_api.send_dropin_notification(
                    message, customer_id=self._customer_id, **kwargs
                )
            )
        else:
            await self.alexa_api.send_dropin_notification(
                message, customer_id=self._customer_id, **kwargs
            )

    @_catch_login_errors
    async def async_play_tts_cloud_say(self, public_url, media_id, **kwargs):
        file_name = media_id
        if media_source.is_media_source_id(media_id):
            media = await media_source.async_resolve_media(
                self.hass, media_id, self.entity_id
            )
            file_name = media.url[media.url.rindex("/") : media.url.rindex(".")]
            media_id = async_process_play_media_url(self.hass, media.url)

        if kwargs.get(ATTR_MEDIA_ANNOUNCE):
            input_file_path = self.hass.config.path(
                f"{UPLOAD_PATH}{file_name}_input.mp3"
            )
            output_file_name = f"{file_name}_output.mp3"
            output_file_path = self.hass.config.path(f"{UPLOAD_PATH}{output_file_name}")

            # file might already exist -> the same tts is cached from previous calls
            if not os.path.exists(output_file_path):
                await self.hass.async_add_executor_job(
                    urllib.request.urlretrieve, media_id, input_file_path
                )
                command = [
                    "ffmpeg",
                    "-i",
                    input_file_path,
                    "-ac",
                    "2",
                    "-codec:a",
                    "libmp3lame",
                    "-b:a",
                    "48k",
                    "-ar",
                    "24000",
                    "-write_xing",
                    "0",
                    output_file_path,
                ]
                if subprocess.run(command, check=True).returncode != 0:
                    _LOGGER.error(
                        "%s: %s:ffmpeg command FAILED converting %s to %s",
                        hide_email(self._login.email),
                        self,
                        input_file_path,
                        output_file_path,
                    )

            _LOGGER.debug(
                "%s: %s:Playing %slocal/alexa_tts%s",
                hide_email(self._login.email),
                self,
                public_url,
                output_file_name,
            )
            await self.async_send_tts(
                f"<audio src='{public_url}local/alexa_tts{output_file_name}' />"
            )
        else:
            await self.async_send_tts(STREAMING_ERROR_MESSAGE)
            _LOGGER.warning(STREAMING_ERROR_MESSAGE)

    @_catch_login_errors
    async def async_play_media(self, media_type, media_id, enqueue=None, **kwargs):
        # pylint: disable=unused-argument,too-many-branches
        """Send the play_media command to the media player."""
        queue_delay = self.hass.data[DATA_ALEXAMEDIA]["accounts"][self.email][
            "options"
        ].get(CONF_QUEUE_DELAY, DEFAULT_QUEUE_DELAY)
        public_url = self.hass.data[DATA_ALEXAMEDIA]["accounts"][self.email][
            "options"
        ].get(CONF_PUBLIC_URL, DEFAULT_PUBLIC_URL)
        if media_type == "music":
            if public_url:
                # Handle TTS playback
                await self.async_play_tts_cloud_say(public_url, media_id, **kwargs)
            else:
                # Log and notify for missing public URL
                _LOGGER.warning(PUBLIC_URL_ERROR_MESSAGE)
                await self.async_send_tts(PUBLIC_URL_ERROR_MESSAGE)
        elif media_type == "sequence":
            _LOGGER.debug(
                "%s: %s:Running sequence %s with queue_delay %s",
                hide_email(self._login.email),
                self,
                media_id,
                queue_delay,
            )
            if self.hass:
                self.hass.async_create_task(
                    self.alexa_api.send_sequence(
                        media_id,
                        customer_id=self._customer_id,
                        queue_delay=queue_delay,
                        **kwargs,
                    )
                )
            else:
                await self.alexa_api.send_sequence(
                    media_id,
                    customer_id=self._customer_id,
                    queue_delay=queue_delay,
                    **kwargs,
                )
        elif media_type == "routine":
            _LOGGER.debug(
                "%s: %s:Running routine %s with queue_delay %s",
                hide_email(self._login.email),
                self,
                media_id,
                queue_delay,
            )
            if self.hass:
                self.hass.async_create_task(
                    self.alexa_api.run_routine(
                        media_id,
                        queue_delay=queue_delay,
                    )
                )
            else:
                await self.alexa_api.run_routine(
                    media_id,
                    queue_delay=queue_delay,
                )
        elif media_type == "sound":
            _LOGGER.debug(
                "%s: %s:Playing sound %s with queue_delay %s",
                hide_email(self._login.email),
                self,
                media_id,
                queue_delay,
            )
            if self.hass:
                self.hass.async_create_task(
                    self.alexa_api.play_sound(
                        media_id,
                        customer_id=self._customer_id,
                        queue_delay=queue_delay,
                        **kwargs,
                    )
                )
            else:
                await self.alexa_api.play_sound(
                    media_id,
                    customer_id=self._customer_id,
                    queue_delay=queue_delay,
                    **kwargs,
                )
        elif media_type == "skill":
            _LOGGER.debug(
                "%s: %s:Running skill %s with queue_delay %s",
                hide_email(self._login.email),
                self,
                media_id,
                queue_delay,
            )
            if self.hass:
                self.hass.async_create_task(
                    self.alexa_api.run_skill(
                        media_id,
                        queue_delay=queue_delay,
                    )
                )
            else:
                await self.alexa_api.run_skill(
                    media_id,
                    queue_delay=queue_delay,
                )
        elif media_type == "image":
            _LOGGER.debug(
                "%s: %s:Setting background to %s",
                hide_email(self._login.email),
                self,
                media_id,
            )
            if self.hass:
                self.hass.async_create_task(self.alexa_api.set_background(media_id))
            else:
                await self.alexa_api.set_background(media_id)
        elif media_type == "custom":
            _LOGGER.debug(
                '%s: %s:Running custom command: "%s" with queue_delay %s',
                hide_email(self._login.email),
                self,
                media_id,
                queue_delay,
            )
            if self.hass:
                self.hass.async_create_task(
                    self.alexa_api.run_custom(
                        media_id,
                        customer_id=self._customer_id,
                        queue_delay=queue_delay,
                        **kwargs,
                    )
                )
            else:
                await self.alexa_api.run_custom(
                    media_id,
                    customer_id=self._customer_id,
                    queue_delay=queue_delay,
                    **kwargs,
                )
        else:
            _LOGGER.debug(
                "%s: %s:Playing music %s on %s with queue_delay %s",
                hide_email(self._login.email),
                self,
                media_id,
                media_type,
                queue_delay,
            )
            if self.hass:
                self.hass.async_create_task(
                    self.alexa_api.play_music(
                        media_type,
                        media_id,
                        customer_id=self._customer_id,
                        queue_delay=queue_delay,
                        timer=kwargs.get("extra", {}).get("timer", None),
                        **kwargs,
                    )
                )
            else:
                await self.alexa_api.play_music(
                    media_type,
                    media_id,
                    customer_id=self._customer_id,
                    queue_delay=queue_delay,
                    timer=kwargs.get("extra", {}).get("timer", None),
                    **kwargs,
                )
        if not (
            self.hass.data[DATA_ALEXAMEDIA]["accounts"][self._login.email]["http2"]
        ):
            await self.async_update()

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attr = {
            "available": self.available,
            "last_called": self._last_called,
            "last_called_timestamp": self._last_called_timestamp,
            "last_called_summary": self._last_called_summary,
            "connected_bluetooth": self._connected_bluetooth,
            "bluetooth_list": self._bluetooth_list,
            "history_records": self._history_records,
            "previous_volume": self._previous_volume,
        }
        return attr

    @property
    def should_poll(self):
        """Return the polling state."""
        return self._should_poll

    @property
    def device_info(self):
        """Return the device_info of the device."""
        return {
            "identifiers": {(ALEXA_DOMAIN, self.unique_id)},
            "name": self.name,
            "manufacturer": "Amazon",
            "model": MODEL_IDS.get(
                self._device_type, f"{self._device_family} {self._device_type}"
            ),
            "sw_version": self._software_version,
        }

    async def _update_notify_targets(self) -> None:
        """Update notification service targets."""
        if self.hass.data[DATA_ALEXAMEDIA].get("notify_service"):
            notify = self.hass.data[DATA_ALEXAMEDIA].get("notify_service")
            if hasattr(notify, "registered_targets"):
                _LOGGER.debug(
                    "%s: Refreshing notify targets",
                    hide_email(self._login.email),
                )
                await notify.async_register_services()
                entity_name_last_called = f"{ALEXA_DOMAIN}_last_called{'_'+ self._login.email if self.unique_id[-1:].isdigit() else ''}"
                await asyncio.sleep(2)
                if (
                    notify.last_called
                    and notify.registered_targets.get(entity_name_last_called)
                    != self.unique_id
                ):
                    _LOGGER.debug(
                        "%s: Changing notify.targets is not supported by HA version < 2021.2.0; using toggle method",
                        hide_email(self._login.email),
                    )
                    notify.last_called = False
                    await notify.async_register_services()
                    await asyncio.sleep(2)
                    notify.last_called = True
                    await notify.async_register_services()
            else:
                _LOGGER.debug(
                    "%s: Unable to refresh notify targets; notify not ready",
                    hide_email(self._login.email),
                )
