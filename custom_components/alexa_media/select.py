"""
Alexa Devices Amazon Kids child select.

SPDX-License-Identifier: Apache-2.0

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""

import logging

from alexapy import AlexaAPI
from homeassistant.components.select import SelectEntity
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError

from . import CONF_EMAIL, DATA_ALEXAMEDIA, hide_email
from .amazon_kids import KIDS_CAPABLE_FAMILIES, OPTION_NONE, async_get_state
from .helpers import _catch_login_errors, add_devices, safe_get

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, add_devices_callback, discovery_info=None):
    """Set up the Alexa select platform."""
    devices: list[SelectEntity] = []
    account = None
    if config:
        account = config.get(CONF_EMAIL)
    if account is None and discovery_info:
        account = safe_get(discovery_info, ["config", CONF_EMAIL])
    if account is None:
        raise ConfigEntryNotReady
    account_dict = hass.data[DATA_ALEXAMEDIA]["accounts"][account]
    login_obj = account_dict["login_obj"]
    kids_state = async_get_state(hass, account_dict, login_obj)
    media_players = account_dict["entities"]["media_player"]

    # One child select per Amazon Kids capable Echo. Only devices that already
    # have a media_player entity are used, so the configured include/exclude
    # device filters are inherited and unique ids stay account scoped.
    for key, device in account_dict["devices"]["media_player"].items():
        if device.get("deviceFamily") not in KIDS_CAPABLE_FAMILIES:
            continue
        device_type = device.get("deviceType")
        client = media_players.get(key)
        if not device_type or client is None:
            continue
        kids_state.track(client.device_serial_number, device_type)
        select = AmazonKidsChildSelect(kids_state, login_obj, client, device_type)
        account_dict["entities"]["select"].append(select)
        devices.append(select)

    if not devices:
        return True
    await kids_state.async_start()
    return await add_devices(hide_email(account), devices, add_devices_callback)


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Set up the Alexa select platform by config_entry."""
    return await async_setup_platform(
        hass, config_entry.data, async_add_devices, discovery_info=None
    )


async def async_unload_entry(hass, entry) -> bool:
    """Unload a config entry."""
    account = entry.data[CONF_EMAIL]
    account_dict = hass.data[DATA_ALEXAMEDIA]["accounts"][account]
    _LOGGER.debug("Attempting to unload selects")
    for select in account_dict["entities"].get("select", []):
        await select.async_remove()
    return True


class AmazonKidsChildSelect(SelectEntity):
    """The child profile an Echo is assigned to for Amazon Kids.

    Selecting a child turns Amazon Kids on for that device and assigns it to
    that child; selecting "None" releases the device again.
    """

    _attr_has_entity_name = True
    _attr_name = "Amazon Kids child"
    _attr_icon = "mdi:account-child-outline"
    _attr_should_poll = False

    def __init__(self, kids_state, login, client, device_type: str) -> None:
        """Initialize the Amazon Kids child select."""
        self._kids = kids_state
        self._login = login
        self._client = client
        self._serial = client.device_serial_number
        self._device_type = device_type

    @property
    def unique_id(self):
        """Return the unique id, scoped to the account like the media player."""
        return f"{self._client.unique_id}_amazon_kids_profile"

    @property
    def options(self) -> list[str]:
        """Return the household's child profiles plus "None"."""
        return [*self._kids.child_options, OPTION_NONE]

    @property
    def current_option(self):
        """Return the assigned child, or "None" while child mode is off.

        A child that is missing from the profile list reads as unknown, so the
        state never falls outside ``options``.
        """
        state = self._kids.state(self._serial)
        if state["kids"] is None:
            return None
        if state["child"]:
            return self._kids.child_option(state["child"])
        return OPTION_NONE

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

    @_catch_login_errors
    async def async_select_option(self, option: str) -> None:
        """Assign the Echo to a child profile, or release it."""
        if option == OPTION_NONE:
            await AlexaAPI.disable_child_mode(
                self._login, self._serial, self._device_type
            )
        else:
            child_id = self._kids.child_id(option)
            if not child_id:
                raise HomeAssistantError(f"Unknown Amazon Kids child profile: {option}")
            await AlexaAPI.enable_child_mode(
                self._login, self._serial, self._device_type, child_id
            )
        await self._kids.async_refresh()
