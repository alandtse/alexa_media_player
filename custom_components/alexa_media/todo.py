"""
Alexa shopping and to-do lists for Alexa Media Player.

SPDX-License-Identifier: Apache-2.0

Each list of the Alexa account (the shopping list, the to-do list and custom
lists) becomes a to-do list entity on the virtual Alexa Account device. One
coordinator per account reads the lists and their items through the Alexa list
API of AlexaPy. Alexa announces list changes through the HTTP2 push
connection, which requests a refresh; polling only reconciles missed events.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import Any

from aiohttp import ClientError
from alexapy import AlexaAPI, hide_email
from alexapy.const import LIST_MARKETPLACE_IDS
from alexapy.errors import AlexapyError, AlexapyLoginError
from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.const import CONF_EMAIL
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from . import account_device_identifier
from .const import DATA_ALEXAMEDIA, DOMAIN
from .helpers import is_http2_enabled, report_relogin_required

_LOGGER = logging.getLogger(__name__)

# Writes need the version of the last read, so they run one at a time.
PARALLEL_UPDATES = 1

# Alexa pushes list changes over HTTP2; polling only catches missed events.
LISTS_SCAN_INTERVAL = timedelta(minutes=15)
LISTS_SCAN_INTERVAL_WITHOUT_PUSH = timedelta(minutes=5)
# Coalesce the burst of push events that one spoken request can cause.
LISTS_REFRESH_COOLDOWN = 3.0

# The account dict key of the coordinator; the HTTP2 push handler refreshes it.
ACCOUNT_KEY = "alexa_lists"
LIST_TRANSLATION_KEYS = {"SHOP": "shopping_list", "TODO": "to_do_list"}

ITEM_COMPLETE = "COMPLETE"


@dataclass(frozen=True)
class AlexaList:
    """One Alexa list and its items, keyed by item ID.

    ``items`` is None while the items of the list could not be read yet.
    """

    list_id: str
    list_type: str
    name: str | None
    items: dict[str, dict[str, Any]] | None


def _unique_id(config_entry, list_id: str) -> str:
    """Return the unique ID of the entity of one list."""
    return f"{config_entry.entry_id}_list_{list_id}"


def _has_list_api(url: str) -> bool:
    """Return whether AlexaPy has the list API for the marketplace of a login."""
    # AlexaPy accepts the legacy Mexico domain as an alias.
    return ("amazon.com.mx" if url == "amazon.mx" else url) in LIST_MARKETPLACE_IDS


def _is_active(record: dict[str, Any]) -> bool:
    """Skip lists that were archived in the Alexa app."""
    return record.get("listStatus") != "ARCHIVED"


class AlexaListsCoordinator(DataUpdateCoordinator[dict[str, AlexaList]]):
    """Read the lists of one Alexa account and their items."""

    def __init__(self, hass: HomeAssistant, config_entry) -> None:
        """Initialize the coordinator of one account."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} lists",
            config_entry=config_entry,
            update_interval=LISTS_SCAN_INTERVAL,
            request_refresh_debouncer=Debouncer(
                hass, _LOGGER, cooldown=LISTS_REFRESH_COOLDOWN, immediate=False
            ),
        )
        self.email: str = config_entry.data[CONF_EMAIL]
        # True once the account turned out to have no list API (marketplace).
        self.unsupported = False
        self._fetch_lock = asyncio.Lock()
        # Set while an authentication failure of the list API is reported.
        self._relogin_reported = False

    @property
    def login(self):
        """Return the current login of the account, which a relogin replaces."""
        account = (
            self.hass.data.get(DATA_ALEXAMEDIA, {}).get("accounts", {}).get(self.email)
        )
        login = account.get("login_obj") if isinstance(account, dict) else None
        if login is None:
            raise HomeAssistantError("The Alexa account is not loaded")
        return login

    def _wanted(self, list_id: str) -> bool:
        """Read items only for lists whose entity is not disabled."""
        registry = er.async_get(self.hass)
        entity_id = registry.async_get_entity_id(
            "todo", DOMAIN, _unique_id(self.config_entry, list_id)
        )
        if entity_id is None:
            return True
        entry = registry.async_get(entity_id)
        return entry is None or entry.disabled_by is None

    async def _async_update_data(self) -> dict[str, AlexaList]:
        """Read all lists, keeping the last good items of a list on failure."""
        async with self._fetch_lock:
            try:
                login = self.login
            except HomeAssistantError as err:
                return self._keep_or_fail(str(err))
            if not _has_list_api(login.url):
                _LOGGER.debug(
                    "%s: Alexa lists are not supported on %s",
                    hide_email(self.email),
                    login.url,
                )
                self.unsupported = True
                return {}
            try:
                records = await AlexaAPI.get_lists(login)
            except AlexapyLoginError as err:
                self.report_login_error(login)
                return self._keep_or_fail(f"Unable to read the Alexa lists: {err}")
            except (AlexapyError, ClientError, ValueError) as err:
                # ValueError: AlexaPy rejected the account's retail endpoints.
                return self._keep_or_fail(f"Unable to read the Alexa lists: {err}")
            if not isinstance(records, list):
                return self._keep_or_fail("Alexa returned no list data")
            self._relogin_reported = False

            previous = self.data or {}
            lists: dict[str, AlexaList] = {}
            for record in records:
                if not _is_active(record):
                    continue
                list_id = record["listId"]
                old = previous.get(list_id)
                items = old.items if old else None
                if self._wanted(list_id):
                    items = await self._read_items(list_id, items)
                lists[list_id] = AlexaList(
                    list_id=list_id,
                    list_type=str(record.get("listType") or ""),
                    name=record.get("listName") or None,
                    items=items,
                )
        self._set_interval()
        return lists

    def _keep_or_fail(self, message: str) -> dict[str, AlexaList]:
        """Keep the cached lists on a transient failure, else fail."""
        if self.data is None:
            raise UpdateFailed(message)
        _LOGGER.debug(
            "%s: %s; keeping the cached lists", hide_email(self.email), message
        )
        return self.data

    async def _read_items(
        self, list_id: str, cached: dict[str, dict[str, Any]] | None
    ) -> dict[str, dict[str, Any]] | None:
        """Read the items of one list, or return the cached items on failure."""
        login = None
        try:
            login = self.login
            records = await AlexaAPI.get_list_items(login, list_id)
        except AlexapyLoginError as err:
            self.report_login_error(login)
            _LOGGER.debug(
                "%s: Unable to read the items of an Alexa list: %s",
                hide_email(self.email),
                err,
            )
            return cached
        except (AlexapyError, ClientError, HomeAssistantError, ValueError) as err:
            _LOGGER.debug(
                "%s: Unable to read the items of an Alexa list: %s",
                hide_email(self.email),
                err,
            )
            return cached
        if not isinstance(records, list):
            return cached
        return {record["itemId"]: record for record in records}

    def report_login_error(self, login) -> None:
        """Report an authentication failure of the list API once per episode.

        The episode ends with the next successful read of the lists.
        """
        if self._relogin_reported:
            return
        if report_relogin_required(self.hass, login, self.email, require_status=False):
            self._relogin_reported = True

    def _set_interval(self) -> None:
        """Poll less often while the HTTP2 push connection is up."""
        self.update_interval = (
            LISTS_SCAN_INTERVAL
            if is_http2_enabled(self.hass, self.email)
            else LISTS_SCAN_INTERVAL_WITHOUT_PUSH
        )

    async def async_refresh_list(self, list_id: str) -> None:
        """Read the items of one list again after a change from Home Assistant."""
        async with self._fetch_lock:
            current = (self.data or {}).get(list_id)
            if current is None:
                return
            items = await self._read_items(list_id, current.items)
            data = dict(self.data or {})
            data[list_id] = AlexaList(
                list_id=current.list_id,
                list_type=current.list_type,
                name=current.name,
                items=items,
            )
            # async_set_updated_data would cancel a refresh that a push for
            # another list requested, so publish without touching the timers.
            self.data = data
        self.async_update_listeners()


async def async_setup_entry(hass, config_entry, async_add_entities) -> bool:
    """Set up one to-do list entity per Alexa list of the account."""
    account = hass.data[DATA_ALEXAMEDIA]["accounts"][config_entry.data[CONF_EMAIL]]
    coordinator = AlexaListsCoordinator(hass, config_entry)
    account[ACCOUNT_KEY] = coordinator

    async def _async_stop() -> None:
        if account.get(ACCOUNT_KEY) is coordinator:
            account.pop(ACCOUNT_KEY, None)
        await coordinator.async_shutdown()

    config_entry.async_on_unload(_async_stop)

    await coordinator.async_refresh()
    if coordinator.unsupported:
        _LOGGER.debug(
            "%s: Alexa lists are not available for this account",
            hide_email(coordinator.email),
        )
        return True

    known: set[str] = set()

    @callback
    def _async_add_new_lists() -> None:
        new = [
            alexa_list
            for list_id, alexa_list in (coordinator.data or {}).items()
            if list_id not in known
        ]
        if not new:
            return
        known.update(alexa_list.list_id for alexa_list in new)
        async_add_entities(
            AlexaTodoList(coordinator, config_entry, alexa_list) for alexa_list in new
        )

    _async_add_new_lists()
    config_entry.async_on_unload(coordinator.async_add_listener(_async_add_new_lists))
    return True


class AlexaTodoList(CoordinatorEntity[AlexaListsCoordinator], TodoListEntity):
    """An Alexa shopping, to-do or custom list."""

    _attr_has_entity_name = True
    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
    )

    def __init__(
        self, coordinator: AlexaListsCoordinator, config_entry, alexa_list: AlexaList
    ) -> None:
        """Bind the entity to one list on the virtual Alexa Account device."""
        super().__init__(coordinator)
        self._list_id = alexa_list.list_id
        self._attr_unique_id = _unique_id(config_entry, alexa_list.list_id)
        self._attr_device_info = dr.DeviceInfo(
            identifiers={account_device_identifier(config_entry)},
        )
        translation_key = LIST_TRANSLATION_KEYS.get(alexa_list.list_type)
        if translation_key:
            self._attr_translation_key = translation_key
        else:
            self._attr_name = alexa_list.name or "List"

    @property
    def _list(self) -> AlexaList | None:
        return (self.coordinator.data or {}).get(self._list_id)

    @property
    def available(self) -> bool:
        """Return whether the list exists and its items are known."""
        alexa_list = self._list
        return (
            super().available
            and alexa_list is not None
            and alexa_list.items is not None
        )

    @property
    def todo_items(self) -> list[TodoItem] | None:
        """Return the items of the list."""
        alexa_list = self._list
        if alexa_list is None or alexa_list.items is None:
            return None
        return [
            TodoItem(
                uid=item_id,
                summary=item.get("itemName") or "",
                status=(
                    TodoItemStatus.COMPLETED
                    if item.get("itemStatus") == ITEM_COMPLETE
                    else TodoItemStatus.NEEDS_ACTION
                ),
            )
            for item_id, item in alexa_list.items.items()
        ]

    def _item(self, uid: str | None) -> dict[str, Any]:
        """Return the cached record of an item, which holds its version."""
        alexa_list = self._list
        items = alexa_list.items if alexa_list else None
        if not items or uid not in items:
            raise HomeAssistantError(f"Item {uid} is not on the Alexa list")
        return items[uid]

    async def _call(self, action: str, request: Callable) -> Any:
        """Run one list request and turn its failures into Home Assistant errors."""
        login = self.coordinator.login
        try:
            result = await request(login)
        except AlexapyLoginError as err:
            self.coordinator.report_login_error(login)
            raise HomeAssistantError(f"Unable to {action}: {err}") from err
        except (AlexapyError, ClientError, ValueError) as err:
            raise HomeAssistantError(f"Unable to {action}: {err}") from err
        if result is None or result is False:
            raise HomeAssistantError(f"Unable to {action}: Alexa rejected the request")
        return result

    async def async_create_todo_item(self, item: TodoItem) -> None:
        """Add an item to the list."""
        try:
            result = await self._call(
                "add the item",
                lambda login: AlexaAPI.add_list_item(
                    login, self._list_id, item.summary
                ),
            )
            if result.get("failures") or not result.get("itemInfoList"):
                raise HomeAssistantError(
                    "Unable to add the item: Alexa rejected the request"
                )
        finally:
            await self.coordinator.async_refresh_list(self._list_id)

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Rename an item or check it off, in one request."""
        record = self._item(item.uid)
        name = (
            item.summary
            if item.summary and item.summary != record.get("itemName")
            else None
        )
        completed = item.status == TodoItemStatus.COMPLETED
        if completed == (record.get("itemStatus") == ITEM_COMPLETE):
            completed = None
        if name is None and completed is None:
            return
        try:
            await self._call(
                "update the item",
                lambda login: AlexaAPI.update_list_item(
                    login,
                    self._list_id,
                    item.uid,
                    record["version"],
                    name=name,
                    completed=completed,
                ),
            )
        finally:
            await self.coordinator.async_refresh_list(self._list_id)

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        """Delete items; a failed item does not stop the others."""
        records = {uid: self._item(uid) for uid in uids}
        failed: list[str] = []
        try:
            for uid, record in records.items():
                try:
                    await self._call(
                        "delete the item",
                        lambda login, uid=uid, version=record["version"]: (
                            AlexaAPI.delete_list_item(
                                login, self._list_id, uid, version
                            )
                        ),
                    )
                except HomeAssistantError as err:
                    _LOGGER.debug("Unable to delete item %s: %s", uid, err)
                    failed.append(uid)
        finally:
            await self.coordinator.async_refresh_list(self._list_id)
        if failed:
            raise HomeAssistantError(
                f"Unable to delete {len(failed)} of {len(uids)} items from the Alexa list"
            )
