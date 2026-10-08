"""
Shared Amazon Kids (child mode) state for Alexa Media Player.

SPDX-License-Identifier: Apache-2.0

Polls the per-device Amazon Kids state (``isChildDirectedDevice``) and the
assigned child profile once per account, so the binary sensor, the switch and
the child select all share a single set of API calls.
"""

from __future__ import annotations

from datetime import timedelta
import logging

from alexapy import AlexaAPI, hide_email
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_time_interval

_LOGGER = logging.getLogger(__name__)

KIDS_SCAN_INTERVAL = timedelta(minutes=5)
KIDS_CAPABLE_FAMILIES = {"ECHO", "ROOK", "KNIGHT", "REAVER", "MANTIS"}

# Select option used when a device is not assigned to any child.
OPTION_NONE = "None"


class AmazonKidsState:
    """Poll and cache the Amazon Kids state for a single Alexa account."""

    def __init__(self, hass, login) -> None:
        """Initialize the shared state for one account."""
        self.hass = hass
        self.login = login
        self.children: list[dict] = []
        self.devices: dict[str, dict] = {}
        self._tracked: dict[str, str] = {}
        self._listeners: list = []
        self._unsub = None

    def track(self, serial: str, device_type: str) -> None:
        """Register a device to be polled."""
        self._tracked[serial] = device_type
        self.devices.setdefault(
            serial, {"kids": None, "child": None, "last_child": None}
        )

    @callback
    def async_add_listener(self, update_callback) -> callable:
        """Register an entity callback; returns an unsubscribe function."""
        self._listeners.append(update_callback)

        @callback
        def _remove() -> None:
            if update_callback in self._listeners:
                self._listeners.remove(update_callback)

        return _remove

    @callback
    def _async_notify(self) -> None:
        for update_callback in list(self._listeners):
            update_callback()

    def state(self, serial: str) -> dict:
        """Return the cached state for a device.

        Keys: ``kids`` (bool|None), ``child`` (directedId|None, only while child
        mode is on) and ``last_child`` (the most recently seen assignment).
        """
        return self.devices.get(serial) or {
            "kids": None,
            "child": None,
            "last_child": None,
        }

    def default_child_id(self, serial: str) -> str | None:
        """Child to assign when switching a device on.

        Prefers the current assignment, then the last one seen for that device,
        and finally the first child profile of the household.
        """
        current = self.state(serial)
        return (
            current.get("child")
            or current.get("last_child")
            or (self.children[0].get("directedId") if self.children else None)
        )

    def child_name(self, directed_id: str | None) -> str | None:
        """Return the first name for a child directedId."""
        if not directed_id:
            return None
        for child in self.children:
            if child.get("directedId") == directed_id:
                return child.get("firstName") or directed_id
        return directed_id

    def child_id(self, name: str | None) -> str | None:
        """Return the directedId for a child first name."""
        if not name:
            return None
        for child in self.children:
            if (child.get("firstName") or "") == name:
                return child.get("directedId")
        return None

    @property
    def child_names(self) -> list[str]:
        """Return the household's child first names."""
        return [c.get("firstName") for c in self.children if c.get("firstName")]

    async def async_start(self) -> None:
        """Do a first refresh and schedule periodic updates."""
        if self._unsub is not None:
            # Already polling for this account; entities get data via listeners.
            return
        self._unsub = async_track_time_interval(
            self.hass, self._async_interval, KIDS_SCAN_INTERVAL
        )
        await self.async_refresh()

    @callback
    def async_stop(self) -> None:
        """Cancel the polling timer."""
        if self._unsub:
            self._unsub()
            self._unsub = None

    async def _async_interval(self, now) -> None:
        await self.async_refresh()

    async def async_refresh(self) -> None:
        """Refresh child profiles and the state of all tracked devices."""
        if not self.children:
            try:
                self.children = await AlexaAPI.get_child_profiles(self.login) or []
            except Exception as ex:  # noqa: BLE001  pylint: disable=broad-except
                _LOGGER.debug(
                    "%s: Unable to list Amazon Kids child profiles: %s",
                    hide_email(self.login.email),
                    ex,
                )
        for serial, device_type in self._tracked.items():
            kids = None
            child = None
            try:
                kids = await AlexaAPI.get_child_mode(self.login, serial, device_type)
                # The assigned child is only meaningful while child mode is on.
                if kids:
                    child = await AlexaAPI.get_device_child(
                        self.login, serial, device_type
                    )
            except Exception as ex:  # noqa: BLE001  pylint: disable=broad-except
                _LOGGER.debug("Amazon Kids refresh failed for a device: %s", ex)
            previous = self.devices.get(serial) or {}
            self.devices[serial] = {
                "kids": kids,
                "child": child,
                # Remember the last assignment so switching back on restores it.
                "last_child": child or previous.get("last_child"),
            }
        self._async_notify()


def async_get_state(hass, account_dict: dict, login) -> AmazonKidsState:
    """Return (creating if needed) the shared Amazon Kids state for an account."""
    state = account_dict.get("amazon_kids")
    if state is None:
        state = AmazonKidsState(hass, login)
        account_dict["amazon_kids"] = state
    return state
