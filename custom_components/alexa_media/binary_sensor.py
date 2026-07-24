"""
Alexa Devices Sensors.

SPDX-License-Identifier: Apache-2.0

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""

from datetime import timedelta
import logging

from alexapy import AlexaAPI, hide_serial
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import (
    CONF_EMAIL,
    CONF_EXCLUDE_DEVICES,
    CONF_INCLUDE_DEVICES,
    DATA_ALEXAMEDIA,
    hide_email,
)
from .alexa_entity import parse_detection_state_from_coordinator
from .const import CONF_EXTENDED_ENTITY_DISCOVERY
from .helpers import _catch_login_errors, add_devices, safe_get

_LOGGER = logging.getLogger(__name__)

KIDS_SCAN_INTERVAL = timedelta(minutes=5)
KIDS_CAPABLE_FAMILIES = {"ECHO", "ROOK", "KNIGHT", "REAVER", "MANTIS"}


async def async_setup_platform(hass, config, add_devices_callback, discovery_info=None):
    """Set up the Alexa sensor platform."""
    devices: list[BinarySensorEntity] = []
    account = None
    if config:
        account = config.get(CONF_EMAIL)
    if account is None and discovery_info:
        account = safe_get(discovery_info, ["config", CONF_EMAIL])
    if account is None:
        raise ConfigEntryNotReady
    account_dict = hass.data[DATA_ALEXAMEDIA]["accounts"][account]
    include_filter = config.get(CONF_INCLUDE_DEVICES, [])
    exclude_filter = config.get(CONF_EXCLUDE_DEVICES, [])
    coordinator = account_dict["coordinator"]
    binary_entities = safe_get(account_dict, ["devices", "binary_sensor"], [])
    if binary_entities and account_dict["options"].get(CONF_EXTENDED_ENTITY_DISCOVERY):
        for binary_entity in binary_entities:
            _LOGGER.debug(
                "Creating entity %s for a binary_sensor with name %s",
                hide_serial(binary_entity["id"]),
                binary_entity["name"],
            )
            contact_sensor = AlexaContact(coordinator, binary_entity)
            account_dict["entities"]["binary_sensor"].append(contact_sensor)
            devices.append(contact_sensor)

    # Amazon Kids (child mode) sensor per Echo device.
    # Only create a sensor for Echos that already have a media_player entity, so
    # the configured include/exclude device filters are inherited and the unique
    # id can be scoped to the account exactly like the media player.
    login_obj = account_dict["login_obj"]
    media_players = account_dict["entities"]["media_player"]
    kids_devices: list[BinarySensorEntity] = []
    for key, device in account_dict["devices"]["media_player"].items():
        if device.get("deviceFamily") not in KIDS_CAPABLE_FAMILIES:
            continue
        device_type = device.get("deviceType")
        client = media_players.get(key)
        if not device_type or client is None:
            continue
        kids_sensor = AmazonKidsSensor(login_obj, client, device_type)
        account_dict["entities"]["binary_sensor"].append(kids_sensor)
        kids_devices.append(kids_sensor)

    result = await add_devices(
        hide_email(account),
        devices,
        add_devices_callback,
        include_filter,
        exclude_filter,
    )
    if kids_devices:
        # Already scoped via the media_player entities, so no extra name filter.
        result = (
            await add_devices(hide_email(account), kids_devices, add_devices_callback)
            and result
        )
    return result


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Set up the Alexa sensor platform by config_entry."""
    return await async_setup_platform(
        hass, config_entry.data, async_add_devices, discovery_info=None
    )


async def async_unload_entry(hass, entry) -> bool:
    """Unload a config entry."""
    account = entry.data[CONF_EMAIL]
    account_dict = hass.data[DATA_ALEXAMEDIA]["accounts"][account]
    _LOGGER.debug("Attempting to unload binary sensors")
    for binary_sensor in account_dict["entities"]["binary_sensor"]:
        await binary_sensor.async_remove()
    return True


class AlexaContact(CoordinatorEntity, BinarySensorEntity):
    """A contact sensor controlled by an Echo."""

    _attr_device_class = BinarySensorDeviceClass.DOOR

    def __init__(self, coordinator: CoordinatorEntity, details: dict):
        """Initialize alexa contact sensor.

        Args
            coordinator (CoordinatorEntity): Coordinator
            details (dict): Details dictionary

        """
        super().__init__(coordinator)
        self.alexa_entity_id = details["id"]
        self._name = details["name"]

    @property
    def name(self):
        """Return name."""
        return self._name

    @property
    def unique_id(self):
        """Return unique id."""
        return self.alexa_entity_id

    @property
    def is_on(self):
        """Return whether on."""
        detection = parse_detection_state_from_coordinator(
            self.coordinator, self.alexa_entity_id
        )

        return detection == "DETECTED" if detection is not None else None

    @property
    def assumed_state(self) -> bool:
        """Return assumed state."""
        last_refresh_success = (
            self.coordinator.data and self.alexa_entity_id in self.coordinator.data
        )
        return not last_refresh_success


class AmazonKidsSensor(BinarySensorEntity):
    """Whether Amazon Kids (child mode) is active on an Echo device.

    Polls the per-device ``isChildDirectedDevice`` state via alexapy on its own
    interval (independent of the main coordinator).
    """

    _attr_has_entity_name = True
    _attr_name = "Amazon Kids"
    _attr_icon = "mdi:account-child"
    _attr_should_poll = False

    def __init__(self, login, client, device_type: str) -> None:
        """Initialize the Amazon Kids sensor.

        client is the Echo's media_player entity; its unique id already encodes
        the account, so the sensor inherits the same (account-scoped) identity.
        """
        self._login = login
        self._client = client
        self._serial = client.device_serial_number
        self._device_type = device_type
        self._state = None

    @property
    def unique_id(self):
        """Return the unique id, scoped to the account like the media player."""
        return f"{self._client.unique_id}_amazon_kids"

    @property
    def is_on(self):
        """Return whether Amazon Kids is active."""
        return self._state

    @property
    def available(self):
        """Return whether the state is known."""
        return self._state is not None

    @property
    def device_info(self):
        """Attach to the Echo device."""
        return {
            "identifiers": {(DATA_ALEXAMEDIA, self._client.unique_id)},
            "via_device": (DATA_ALEXAMEDIA, self._client.unique_id),
        }

    async def async_added_to_hass(self):
        """Do an initial refresh and schedule periodic updates."""
        await self._async_refresh()
        self.async_on_remove(
            async_track_time_interval(
                self.hass, self._async_interval, KIDS_SCAN_INTERVAL
            )
        )

    async def _async_interval(self, now):
        await self._async_refresh()

    @_catch_login_errors
    async def _async_refresh(self):
        """Fetch the current Amazon Kids state."""
        self._state = await AlexaAPI.get_child_mode(
            self._login, self._serial, self._device_type
        )
        self.async_write_ha_state()
