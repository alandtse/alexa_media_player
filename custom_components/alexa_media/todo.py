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
from dataclasses import dataclass, replace
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
from homeassistant.helpers.entity import EntityDescription
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
# The shopping list and the to-do list have translated names. The English
# names of strings.json are the fallback while the translation files, which
# Lokalise builds, do not hold them yet; the entity IDs come from them.
LIST_DESCRIPTIONS = {
    "SHOP": EntityDescription(
        key="shopping_list", translation_key="shopping_list", name="Shopping list"
    ),
    "TODO": EntityDescription(
        key="to_do_list", translation_key="to_do_list", name="To-do list"
    ),
}

ITEM_COMPLETE = "COMPLETE"
# The largest page the list API returns.
ITEMS_PAGE_SIZE = 100
# The account setup does not wait for the first read of the lists. A failed
# first read is retried after these delays (seconds); then polling takes over.
LISTS_DISCOVERY_RETRY_DELAYS = (30, 60, 120)


@dataclass(frozen=True)
class AlexaList:
    """One Alexa list and its items, keyed by item ID.

    ``items`` is None while the items of the list could not be read yet.
    ``older_completed`` is True when the last read stopped before older
    completed items, which the entity does not show.
    """

    list_id: str
    list_type: str
    name: str | None
    items: dict[str, dict[str, Any]] | None
    older_completed: bool = False


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


def _version(record: dict[str, Any], action: str) -> str | int:
    """Return the item version of the last read, which every write needs."""
    version = record.get("version")
    if (
        isinstance(version, bool)
        or not isinstance(version, (str, int))
        or (isinstance(version, str) and not version.strip())
    ):
        raise HomeAssistantError(
            f"Unable to {action}: Alexa returned the item without a version"
        )
    return version


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
                items, older_completed = (
                    (old.items, old.older_completed) if old else (None, False)
                )
                if self._wanted(list_id):
                    items, older_completed = await self._read_items(list_id, old)
                lists[list_id] = AlexaList(
                    list_id=list_id,
                    list_type=str(record.get("listType") or ""),
                    name=record.get("listName") or None,
                    items=items,
                    older_completed=older_completed,
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
        self, list_id: str, cached: AlexaList | None
    ) -> tuple[dict[str, dict[str, Any]] | None, bool]:
        """Read the items of one list, or return the cached items on failure.

        Returns the items and whether older completed items were left unread.
        """
        kept = (cached.items, cached.older_completed) if cached else (None, False)
        login = None
        try:
            login = self.login
            result = await self._read_item_pages(login, list_id)
        except AlexapyLoginError as err:
            self.report_login_error(login)
            _LOGGER.debug(
                "%s: Unable to read the items of an Alexa list: %s",
                hide_email(self.email),
                err,
            )
            return kept
        except (AlexapyError, ClientError, HomeAssistantError, ValueError) as err:
            _LOGGER.debug(
                "%s: Unable to read the items of an Alexa list: %s",
                hide_email(self.email),
                err,
            )
            return kept
        return kept if result is None else result

    async def _read_item_pages(
        self, login, list_id: str
    ) -> tuple[dict[str, dict[str, Any]], bool] | None:
        """Read the open items of a list and the completed items next to them.

        Alexa returns the open items first and keeps every completed item, so a
        long-used shopping list can hold thousands of them. Paging stops after
        the first page that holds only completed items. Returns the items and
        whether older completed items were left unread, or None for a
        malformed page, which keeps the cached items.
        """
        items: dict[str, dict[str, Any]] = {}
        token: str | None = None
        seen: set[str] = set()
        while True:
            page = await AlexaAPI.get_list_items_page(
                login, list_id, limit=ITEMS_PAGE_SIZE, next_token=token
            )
            records = page.get("itemInfoList") if isinstance(page, dict) else None
            if not isinstance(records, list) or not all(
                isinstance(record, dict)
                and isinstance(record.get("itemId"), str)
                and record["itemId"]
                for record in records
            ):
                return None
            items.update((record["itemId"], record) for record in records)
            token = page.get("nextToken")
            if token is None or (isinstance(token, str) and not token):
                return items, False
            # A malformed or repeated token makes the whole response malformed,
            # even on the last page this read uses.
            if not isinstance(token, str) or token in seen:
                return None
            if records and all(
                record.get("itemStatus") == ITEM_COMPLETE for record in records
            ):
                return items, True
            seen.add(token)

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
            items, older_completed = await self._read_items(list_id, current)
            data = dict(self.data or {})
            data[list_id] = replace(
                current, items=items, older_completed=older_completed
            )
            # async_set_updated_data would cancel a refresh that a push for
            # another list requested, so publish without touching the timers.
            self.data = data
        self.async_update_listeners()

    async def async_discover(self) -> None:
        """Read the lists for the first time, retrying a failed read a few times.

        After the last retry, polling keeps trying.
        """
        await self.async_refresh()
        for delay in LISTS_DISCOVERY_RETRY_DELAYS:
            if self.data is not None:
                return
            await asyncio.sleep(delay)
            # A push or a poll may have read the lists in the meantime.
            if self.data is None:
                await self.async_refresh()


async def async_setup_entry(hass, config_entry, async_add_entities) -> bool:
    """Set up one to-do list entity per Alexa list of the account.

    The lists are read in a background task, so a slow or failing list API
    does not delay the setup of the account. The entities appear once the
    lists are read. Home Assistant cancels the task when the entry unloads.
    """
    account = hass.data[DATA_ALEXAMEDIA]["accounts"][config_entry.data[CONF_EMAIL]]
    coordinator = AlexaListsCoordinator(hass, config_entry)
    account[ACCOUNT_KEY] = coordinator

    async def _async_stop() -> None:
        if account.get(ACCOUNT_KEY) is coordinator:
            account.pop(ACCOUNT_KEY, None)
        await coordinator.async_shutdown()

    config_entry.async_on_unload(_async_stop)

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

    config_entry.async_on_unload(coordinator.async_add_listener(_async_add_new_lists))

    async def _async_discover() -> None:
        await coordinator.async_discover()
        if coordinator.unsupported:
            _LOGGER.debug(
                "%s: Alexa lists are not available for this account",
                hide_email(coordinator.email),
            )
            # No list API, so nothing to poll.
            await coordinator.async_shutdown()

    config_entry.async_create_background_task(
        hass, _async_discover(), name=f"{DOMAIN} lists discovery"
    )
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
        description = LIST_DESCRIPTIONS.get(alexa_list.list_type)
        if description:
            self.entity_description = description
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
            version = _version(record, "update the item")
            await self._call(
                "update the item",
                lambda login: AlexaAPI.update_list_item(
                    login,
                    self._list_id,
                    item.uid,
                    version,
                    name=name,
                    completed=completed,
                ),
            )
        finally:
            await self.coordinator.async_refresh_list(self._list_id)

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        """Delete items; a failed item does not stop the others.

        Only the given items are deleted. Clearing the completed items of a
        list whose read stopped before its older completed items leaves those
        in Alexa; the readback shows the next of them, and a warning says so.
        """
        records = {uid: self._item(uid) for uid in uids}
        alexa_list = self._list
        shown = alexa_list.items if alexa_list and alexa_list.items else {}
        completed = {
            uid
            for uid, record in shown.items()
            if record.get("itemStatus") == ITEM_COMPLETE
        }
        older_completed_left = bool(
            alexa_list
            and alexa_list.older_completed
            and completed
            and completed.issubset(records)
        )
        failed: list[str] = []
        try:
            for uid, record in records.items():
                try:
                    version = _version(record, "delete the item")
                    await self._call(
                        "delete the item",
                        lambda login, uid=uid, version=version: (
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
        if older_completed_left:
            _LOGGER.warning(
                "%s: Removed the %d completed items that the list showed. Alexa "
                "keeps older completed items, which Home Assistant does not "
                "read; the next of them show up now. Remove them the same way, "
                "or in the Alexa app",
                self.entity_id,
                len(completed),
            )
