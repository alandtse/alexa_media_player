"""
Alexa Devices Sensors.

SPDX-License-Identifier: Apache-2.0

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""

import logging

from alexapy import hide_serial
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from . import (
    CONF_EMAIL,
    CONF_EXCLUDE_DEVICES,
    CONF_INCLUDE_DEVICES,
    DATA_ALEXAMEDIA,
    _network_allowed,
    hide_email,
)
from .alexa_entity import parse_detection_state_from_coordinator
from .amazon_kids import KIDS_CAPABLE_FAMILIES, async_get_state
from .connectivity import connectivity_state
from .const import CONF_EXTENDED_ENTITY_DISCOVERY
from .helpers import add_devices, safe_get

_LOGGER = logging.getLogger(__name__)


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

    # Inventory has already passed AMP's device name/capability filters.
    # Discover independently of media_player entity creation or enablement.
    def discover_connectivity():
        known = {
            entity.unique_id
            for entity in account_dict["entities"]["binary_sensor"]
            if isinstance(entity, EchoConnectivitySensor)
        }
        entities = []
        for serial, device in account_dict["devices"]["media_player"].items():
            if device.get("deviceFamily") not in KIDS_CAPABLE_FAMILIES:
                continue
            entity = EchoConnectivitySensor(coordinator, account_dict, serial, account)
            if entity.unique_id not in known:
                account_dict["entities"]["binary_sensor"].append(entity)
                entities.append(entity)
        if entities:
            add_devices_callback(entities)

    discover_connectivity()
    # Also discover devices on later inventory updates without another request.
    account_dict.setdefault("connectivity_discovery_unsub", lambda: None)()
    account_dict["connectivity_discovery_unsub"] = connectivity_state(
        account_dict
    ).add_listener(discover_connectivity)
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
    kids_state = async_get_state(hass, account_dict, login_obj)
    media_players = account_dict["entities"]["media_player"]
    kids_devices: list[BinarySensorEntity] = []
    for key, device in account_dict["devices"]["media_player"].items():
        if device.get("deviceFamily") not in KIDS_CAPABLE_FAMILIES:
            continue
        device_type = device.get("deviceType")
        client = media_players.get(key)
        if not device_type or client is None:
            continue
        kids_state.track(client.device_serial_number, device_type)
        kids_sensor = AmazonKidsSensor(kids_state, client)
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
        await kids_state.async_start()
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
    account_dict.pop("connectivity_discovery_unsub", lambda: None)()
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

    Reads from the shared per-account Amazon Kids state, so this sensor, the
    switch and the child select all share a single set of API calls.
    """

    _attr_has_entity_name = True
    _attr_name = "Amazon Kids"
    _attr_icon = "mdi:account-child"
    _attr_should_poll = False

    def __init__(self, kids_state, client) -> None:
        """Initialize the Amazon Kids sensor.

        client is the Echo's media_player entity; its unique id already encodes
        the account, so the sensor inherits the same (account-scoped) identity.
        """
        self._kids = kids_state
        self._client = client
        self._serial = client.device_serial_number

    @property
    def unique_id(self):
        """Return the unique id, scoped to the account like the media player."""
        return f"{self._client.unique_id}_amazon_kids"

    @property
    def is_on(self):
        """Return whether Amazon Kids is active."""
        return self._kids.state(self._serial)["kids"]

    @property
    def available(self):
        """Return whether the state is known."""
        return self._kids.state(self._serial)["kids"] is not None

    @property
    def device_info(self):
        """Attach to the Echo device."""
        return {
            "identifiers": {(DATA_ALEXAMEDIA, self._client.unique_id)},
        }

    async def async_added_to_hass(self):
        """Subscribe to shared Amazon Kids state updates."""
        self.async_on_remove(self._kids.async_add_listener(self.async_write_ha_state))


class EchoConnectivitySensor(BinarySensorEntity):
    """Amazon-reported Echo connectivity, independent of player availability."""

    _attr_has_entity_name = True
    _attr_name = "Connectivity"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_should_poll = False

    def __init__(self, coordinator, account, serial, email):
        """Attach to account observations and the existing Echo registry identity."""
        self.coordinator = coordinator
        self._account = account
        self._serial = serial
        self._connectivity = connectivity_state(account)
        self._attr_unique_id = f"{slugify(f'{serial}_{email}')}_connectivity"
        device_id = (
            slugify(f"{serial}_{email}")
            if account.get("second_account_index")
            else serial
        )
        self._attr_device_info = {"identifiers": {(DATA_ALEXAMEDIA, device_id)}}

    @property
    def is_on(self):
        """Return unknown until a valid observation, including after failure."""
        return self._connectivity.values.get(self._serial)

    @property
    def available(self):
        """An explicitly offline Echo is available; an unusable account is not."""
        login = self._account.get("login_obj")
        return bool(
            self._connectivity.account_available
            and self.coordinator.last_update_success
            and login
            and _network_allowed(login)
        )

    async def async_added_to_hass(self):
        """Listen passively to account observations without coordinator polling."""
        await super().async_added_to_hass()
        self.async_on_remove(self._connectivity.add_listener(self.async_write_ha_state))
