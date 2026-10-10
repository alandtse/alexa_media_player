"""
Shared Amazon Kids (child mode) state for Alexa Media Player.

SPDX-License-Identifier: Apache-2.0

Polls the per-device Amazon Kids state (``isChildDirectedDevice``) and the
assigned child profile once per account, so the binary sensor, the switch and
the child select all share a single set of API calls.
"""

from __future__ import annotations

import asyncio
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
        self._options: dict[str, str] = {}
        self._tracked: dict[str, str] = {}
        self._listeners: list = []
        self._refresh_lock = asyncio.Lock()
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

    def _set_children(self, children: list[dict]) -> None:
        """Store the child profiles and rebuild the select options.

        Profiles can share a first name, can have no first name at all, and can
        even be named like the release option, so every option label is made
        unique and maps to exactly one ``directedId``.
        """
        self.children = children
        options: dict[str, str] = {}
        used = {OPTION_NONE}
        for child in children:
            directed_id = child.get("directedId")
            if not directed_id:
                continue
            base = (child.get("firstName") or "").strip() or directed_id
            label = base
            if label in used:
                label = f"{base} ({directed_id[-4:]})"
                index = 2
                while label in used:
                    label = f"{base} ({directed_id[-4:]}-{index})"
                    index += 1
            used.add(label)
            options[label] = directed_id
        self._options = options

    @property
    def child_options(self) -> list[str]:
        """Return one select option label per child profile."""
        return list(self._options)

    def child_id(self, option: str | None) -> str | None:
        """Return the directedId for a select option label."""
        if not option:
            return None
        return self._options.get(option)

    def child_option(self, directed_id: str | None) -> str | None:
        """Return the select option label for a child directedId."""
        if not directed_id:
            return None
        for label, candidate in self._options.items():
            if candidate == directed_id:
                return label
        return None

    def default_child_id(self, serial: str) -> str | None:
        """Child to assign when switching a device on.

        Prefers the current assignment, then the last one seen for that device,
        and finally the first child profile of the household. A child that no
        longer exists is skipped, unless the profile list is unavailable and the
        device assignment is all we know.
        """
        known = set(self._options.values())
        current = self.state(serial)
        for candidate in (current.get("child"), current.get("last_child")):
            if candidate and (not known or candidate in known):
                return candidate
        return next(iter(self._options.values()), None)

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
        """Refresh child profiles and the state of all tracked devices.

        Refreshes are serialized: a device command refreshes right after it
        completes, and without the lock a slower poll already in flight could
        finish last and write back the assignment it read before the command.
        """
        async with self._refresh_lock:
            await self._async_refresh()

    async def _async_refresh(self) -> None:
        try:
            children = await AlexaAPI.get_child_profiles(self.login)
        except Exception as ex:  # noqa: BLE001  pylint: disable=broad-except
            # Keep the profiles from the last successful poll; a failed fetch
            # must not empty the select or drop the switch's fallback child.
            _LOGGER.debug(
                "%s: Unable to list Amazon Kids child profiles: %s",
                hide_email(self.login.email),
                ex,
            )
        else:
            self._set_children(children or [])
        # Snapshot: a platform still setting up may track a device meanwhile.
        for serial, device_type in list(self._tracked.items()):
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
