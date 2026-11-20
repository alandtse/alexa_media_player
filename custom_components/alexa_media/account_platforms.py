"""Account-level platform reconciliation independent of inventory refresh."""

import asyncio

from homeassistant.exceptions import ConfigEntryNotReady

from .const import ALEXA_COMPONENTS
from .exceptions import TimeoutException


async def sync_echo_platforms(hass, config_entry, account: dict) -> None:
    """Load media_player once, then add later Echos to its existing platform."""
    pending = [
        serial
        for serial in account["devices"]["media_player"]
        if serial not in account["entities"]["media_player"]
    ]
    if not account.get("media_player_platform_loaded"):
        # A prior media-player forward may have created entities before its
        # dependent platforms failed. Complete that setup using the existing
        # platform rather than forwarding media_player a second time.
        if account.get("media_player_add_entities") is not None:
            from .media_player import async_complete_dependent_platforms

            await async_complete_dependent_platforms(hass, config_entry, account)
            account["media_player_platform_loaded"] = True
            return
        if not pending:
            return
        try:
            await hass.config_entries.async_forward_entry_setups(
                config_entry, ALEXA_COMPONENTS
            )
        except (asyncio.TimeoutError, TimeoutException) as err:
            raise ConfigEntryNotReady(
                f"Media player platform setup timed out: {err}"
            ) from err
        if not account.get("media_player_platform_loaded"):
            await hass.config_entries.async_forward_entry_unload(
                config_entry, "media_player"
            )
            raise ConfigEntryNotReady("Media player platform not ready")
        return

    if not pending:
        return
    from .media_player import async_setup_platform

    adder = account.get("media_player_add_entities")
    if adder is None:
        raise ConfigEntryNotReady("Media player entity adder not ready")
    if not await async_setup_platform(
        hass, config_entry.data, adder, discover_only=True
    ):
        raise ConfigEntryNotReady("New media players could not be added")
