"""Alexa shopping, to-do and custom lists as to-do list entities."""

from copy import deepcopy
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from alexapy.errors import (
    AlexapyConnectionError,
    AlexapyLoginError,
    AlexapyTooManyRequestsError,
)
from homeassistant.components.todo import DOMAIN as TODO_DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_EMAIL, STATE_UNAVAILABLE
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

import custom_components.alexa_media as alexa_media
from custom_components.alexa_media import (
    _register_account_device,
    account_device_identifier,
)
from custom_components.alexa_media.const import DATA_ALEXAMEDIA, DOMAIN
from custom_components.alexa_media.todo import (
    ACCOUNT_KEY,
    LISTS_REFRESH_COOLDOWN,
    LISTS_SCAN_INTERVAL,
    LISTS_SCAN_INTERVAL_WITHOUT_PUSH,
)

EMAIL = "test@example.com"

LISTS = [
    {"listId": "shop-1", "listType": "SHOP", "version": 3},
    {"listId": "todo-1", "listType": "TODO", "version": 1},
    {
        "listId": "custom-1",
        "listType": "CUSTOM",
        "listName": "Hardware store",
        "version": 2,
    },
    {
        "listId": "old-1",
        "listType": "CUSTOM",
        "listName": "Old",
        "listStatus": "ARCHIVED",
        "version": 9,
    },
]
ITEMS = {
    "shop-1": [
        {"itemId": "milk", "itemName": "milk", "itemStatus": "ACTIVE", "version": 7},
        {"itemId": "eggs", "itemName": "eggs", "itemStatus": "COMPLETE", "version": 2},
    ],
    "todo-1": [],
    "custom-1": [
        {"itemId": "screws", "itemName": "screws", "itemStatus": "ACTIVE", "version": 1}
    ],
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Allow Home Assistant to load the custom integration."""
    yield


@pytest.fixture
def api():
    """Patch the Alexa list API of AlexaPy."""
    items = deepcopy(ITEMS)
    mock = MagicMock()
    mock.items = items
    mock.get_lists = AsyncMock(side_effect=lambda login, **kwargs: deepcopy(LISTS))
    # The test's source of items; get_list_items_page serves them as one page.
    mock.read_items = AsyncMock(
        side_effect=lambda login, list_id, **kwargs: deepcopy(items[list_id])
    )

    async def _page(login, list_id, *, limit=100, next_token=None):
        records = await mock.read_items(login, list_id)
        return None if records is None else {"itemInfoList": records}

    mock.get_list_items_page = AsyncMock(side_effect=_page)
    mock.add_list_item = AsyncMock(
        return_value={"itemInfoList": [{"itemId": "new"}], "failures": []}
    )
    mock.update_list_item = AsyncMock(return_value={"itemInfo": {"itemId": "milk"}})
    mock.delete_list_item = AsyncMock(return_value=True)
    with patch("custom_components.alexa_media.todo.AlexaAPI", mock):
        yield mock


@pytest.fixture
def account():
    """Return the account record that the integration keeps for one login."""
    return {
        "login_obj": MagicMock(
            email=EMAIL, url="amazon.com", status={"login_successful": True}
        )
    }


@pytest.fixture
async def entry(hass, account):
    """Set up only the to-do platform of an Alexa account."""
    hass.config.components.update({"http", "persistent_notification"})

    async def _setup_entry(hass, config_entry):
        hass.data.setdefault(DATA_ALEXAMEDIA, {}).setdefault("accounts", {})[
            EMAIL
        ] = account
        _register_account_device(hass, config_entry)
        await hass.config_entries.async_forward_entry_setups(config_entry, ["todo"])
        return True

    async def _unload_entry(hass, config_entry):
        return await hass.config_entries.async_unload_platforms(config_entry, ["todo"])

    config_entry = MockConfigEntry(domain=DOMAIN, data={CONF_EMAIL: EMAIL})
    config_entry.add_to_hass(hass)
    with (
        patch.object(alexa_media, "async_setup", AsyncMock(return_value=True)),
        patch.object(alexa_media, "async_setup_entry", _setup_entry),
        patch.object(alexa_media, "async_unload_entry", _unload_entry),
    ):
        yield config_entry
        if config_entry.state is ConfigEntryState.LOADED:
            assert await hass.config_entries.async_unload(config_entry.entry_id)
            await hass.async_block_till_done()


async def _load(hass, config_entry):
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()


def _entity_id(hass, config_entry, list_id):
    return er.async_get(hass).async_get_entity_id(
        TODO_DOMAIN, DOMAIN, f"{config_entry.entry_id}_list_{list_id}"
    )


async def _items(hass, entity_id):
    response = await hass.services.async_call(
        TODO_DOMAIN,
        "get_items",
        {},
        target={"entity_id": entity_id},
        blocking=True,
        return_response=True,
    )
    return response[entity_id]["items"]


async def test_lists_become_entities_on_the_account_device(hass, api, entry):
    """Each active list is one entity; archived lists are skipped."""
    await _load(hass, entry)

    registry = er.async_get(hass)
    shop = _entity_id(hass, entry, "shop-1")
    todo = _entity_id(hass, entry, "todo-1")
    custom = _entity_id(hass, entry, "custom-1")
    assert _entity_id(hass, entry, "old-1") is None
    assert shop.endswith("_shopping_list")
    assert todo.endswith("_to_do_list")
    assert custom.endswith("_hardware_store")

    assert registry.async_get(shop).translation_key == "shopping_list"
    assert registry.async_get(todo).translation_key == "to_do_list"
    assert registry.async_get(custom).translation_key is None
    assert hass.states.get(shop).attributes["friendly_name"].endswith("Shopping list")
    assert (
        hass.states.get(custom).attributes["friendly_name"].endswith("Hardware store")
    )

    device = registry.async_get(shop).device_id
    assert device is not None
    from homeassistant.helpers import device_registry as dr

    assert dr.async_get(hass).async_get(device).identifiers == {
        account_device_identifier(entry)
    }

    # The state counts the items that still need action.
    assert hass.states.get(shop).state == "1"
    assert hass.states.get(todo).state == "0"
    assert await _items(hass, shop) == [
        {"uid": "milk", "summary": "milk", "status": "needs_action"},
        {"uid": "eggs", "summary": "eggs", "status": "completed"},
    ]


async def test_add_rename_check_off_and_delete(hass, api, entry, account):
    """Writes pass the item version and read the list again."""
    await _load(hass, entry)
    shop = _entity_id(hass, entry, "shop-1")
    login = account["login_obj"]

    await hass.services.async_call(
        TODO_DOMAIN,
        "add_item",
        {"item": "bread"},
        target={"entity_id": shop},
        blocking=True,
    )
    api.add_list_item.assert_awaited_once_with(login, "shop-1", "bread")

    api.get_list_items_page.reset_mock()
    await hass.services.async_call(
        TODO_DOMAIN,
        "update_item",
        {"item": "milk", "rename": "oat milk", "status": "completed"},
        target={"entity_id": shop},
        blocking=True,
    )
    # A rename and a status change go out as one request.
    api.update_list_item.assert_awaited_once_with(
        login, "shop-1", "milk", 7, name="oat milk", completed=True
    )
    api.get_list_items_page.assert_awaited_once_with(
        login, "shop-1", limit=100, next_token=None
    )

    await hass.services.async_call(
        TODO_DOMAIN,
        "remove_item",
        {"item": ["eggs"]},
        target={"entity_id": shop},
        blocking=True,
    )
    api.delete_list_item.assert_awaited_once_with(login, "shop-1", "eggs", 2)


async def test_update_without_a_change_sends_nothing(hass, api, entry):
    """Setting an item to what it already is makes no request."""
    await _load(hass, entry)
    shop = _entity_id(hass, entry, "shop-1")

    await hass.services.async_call(
        TODO_DOMAIN,
        "update_item",
        {"item": "milk", "status": "needs_action"},
        target={"entity_id": shop},
        blocking=True,
    )
    api.update_list_item.assert_not_awaited()

    await hass.services.async_call(
        TODO_DOMAIN,
        "update_item",
        {"item": "eggs", "status": "needs_action"},
        target={"entity_id": shop},
        blocking=True,
    )
    api.update_list_item.assert_awaited_once()
    assert api.update_list_item.await_args.kwargs == {
        "name": None,
        "completed": False,
    }


@pytest.mark.parametrize(
    "add_result",
    [
        pytest.param(None, id="rejected"),
        pytest.param({"itemInfoList": [], "failures": [{"x": 1}]}, id="item-failed"),
        pytest.param(AlexapyConnectionError("down"), id="connection"),
        pytest.param(AlexapyTooManyRequestsError("slow down"), id="throttled"),
    ],
)
async def test_failed_add_raises_and_reads_the_list(hass, api, entry, add_result):
    """A failed write is reported, and the list is read again."""
    await _load(hass, entry)
    shop = _entity_id(hass, entry, "shop-1")
    if isinstance(add_result, Exception):
        api.add_list_item.side_effect = add_result
    else:
        api.add_list_item.return_value = add_result
    api.read_items.reset_mock()

    with pytest.raises(HomeAssistantError, match="Unable to add the item"):
        await hass.services.async_call(
            TODO_DOMAIN,
            "add_item",
            {"item": "bread"},
            target={"entity_id": shop},
            blocking=True,
        )
    api.read_items.assert_awaited_once()
    assert hass.states.get(shop).state == "1"


async def test_failed_update_raises(hass, api, entry):
    """Alexa rejecting an update is an error."""
    await _load(hass, entry)
    shop = _entity_id(hass, entry, "shop-1")
    api.update_list_item.return_value = None

    with pytest.raises(HomeAssistantError, match="Unable to update the item"):
        await hass.services.async_call(
            TODO_DOMAIN,
            "update_item",
            {"item": "milk", "rename": "oat milk"},
            target={"entity_id": shop},
            blocking=True,
        )


async def test_one_failed_delete_does_not_stop_the_others(hass, api, entry):
    """Every item is tried; the error names how many failed."""
    await _load(hass, entry)
    shop = _entity_id(hass, entry, "shop-1")
    api.delete_list_item.side_effect = [False, True]

    with pytest.raises(HomeAssistantError, match="Unable to delete 1 of 2 items"):
        await hass.services.async_call(
            TODO_DOMAIN,
            "remove_item",
            {"item": ["milk", "eggs"]},
            target={"entity_id": shop},
            blocking=True,
        )
    assert api.delete_list_item.await_count == 2


async def test_transient_failures_keep_the_cached_lists(hass, api, entry, account):
    """Failed or malformed reads keep the last good items and availability."""
    await _load(hass, entry)
    coordinator = account[ACCOUNT_KEY]
    shop = _entity_id(hass, entry, "shop-1")
    custom = _entity_id(hass, entry, "custom-1")

    for failure in (
        AlexapyConnectionError("down"),
        AlexapyTooManyRequestsError("slow down"),
    ):
        api.get_lists.side_effect = failure
        await coordinator.async_refresh()
        assert hass.states.get(shop).state == "1"

    api.get_lists.side_effect = None
    api.get_lists.return_value = None  # malformed or unsuccessful response
    await coordinator.async_refresh()
    assert hass.states.get(shop).state == "1"

    # One list failing keeps its items; another list still updates.
    api.get_lists.side_effect = lambda login, **kwargs: deepcopy(LISTS)
    api.items["custom-1"].append(
        {"itemId": "nails", "itemName": "nails", "itemStatus": "ACTIVE", "version": 1}
    )
    api.read_items.side_effect = lambda login, list_id, **kwargs: (
        None if list_id == "shop-1" else deepcopy(api.items[list_id])
    )
    await coordinator.async_refresh()
    assert hass.states.get(shop).state == "1"
    assert hass.states.get(custom).state == "2"

    # Recovery: the next good read updates the list.
    api.items["shop-1"].pop(0)
    api.read_items.side_effect = lambda login, list_id, **kwargs: deepcopy(
        api.items[list_id]
    )
    await coordinator.async_refresh()
    assert hass.states.get(shop).state == "0"


async def test_lists_appear_after_a_failed_first_read(hass, api, entry, account):
    """A failed first read creates nothing; a later read adds the lists."""
    api.get_lists.side_effect = AlexapyConnectionError("down")
    await _load(hass, entry)
    assert _entity_id(hass, entry, "shop-1") is None

    api.get_lists.side_effect = lambda login, **kwargs: deepcopy(LISTS)
    await account[ACCOUNT_KEY].async_refresh()
    await hass.async_block_till_done()
    shop = _entity_id(hass, entry, "shop-1")
    assert shop is not None
    assert hass.states.get(shop).state == "1"


async def test_a_list_without_items_yet_is_unavailable(hass, api, entry):
    """A list whose items could never be read is unavailable, not empty."""
    api.read_items.side_effect = lambda login, list_id, **kwargs: (
        None if list_id == "todo-1" else deepcopy(ITEMS[list_id])
    )
    await _load(hass, entry)
    assert hass.states.get(_entity_id(hass, entry, "todo-1")).state == (
        STATE_UNAVAILABLE
    )
    assert hass.states.get(_entity_id(hass, entry, "shop-1")).state == "1"


async def test_new_and_removed_lists(hass, api, entry, account):
    """A new list is added; a list deleted in the app becomes unavailable."""
    await _load(hass, entry)
    coordinator = account[ACCOUNT_KEY]
    custom = _entity_id(hass, entry, "custom-1")

    lists = [record for record in LISTS if record["listId"] != "custom-1"]
    lists.append({"listId": "custom-2", "listType": "CUSTOM", "listName": "Party"})
    api.get_lists.side_effect = lambda login, **kwargs: deepcopy(lists)
    api.items["custom-2"] = []
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get(custom).state == STATE_UNAVAILABLE
    party = _entity_id(hass, entry, "custom-2")
    assert party.endswith("_party")
    assert hass.states.get(party).state == "0"


async def test_disabled_lists_are_not_read(hass, api, entry, account):
    """Disabling a list entity stops reading its items."""
    await _load(hass, entry)
    er.async_get(hass).async_update_entity(
        _entity_id(hass, entry, "custom-1"),
        disabled_by=er.RegistryEntryDisabler.USER,
    )
    api.read_items.reset_mock()

    await account[ACCOUNT_KEY].async_refresh()

    read = {call.args[1] for call in api.read_items.await_args_list}
    assert read == {"shop-1", "todo-1"}


async def test_unsupported_marketplace_creates_nothing(hass, api, entry, account):
    """A marketplace without the list API gets no entities and no requests."""
    account["login_obj"].url = "amazon.nl"
    await _load(hass, entry)
    assert _entity_id(hass, entry, "shop-1") is None
    assert account[ACCOUNT_KEY].unsupported is True

    async_fire_time_changed(hass, dt_util.utcnow() + LISTS_SCAN_INTERVAL * 2)
    await hass.async_block_till_done()
    api.get_lists.assert_not_awaited()


async def test_rejected_retail_endpoints_keep_the_cached_lists(
    hass, api, entry, account
):
    """A ValueError on a supported marketplace is a failed read, not unsupported."""
    await _load(hass, entry)
    shop = _entity_id(hass, entry, "shop-1")
    api.get_lists.side_effect = ValueError("Invalid Amazon retail URL")

    await account[ACCOUNT_KEY].async_refresh()

    assert account[ACCOUNT_KEY].unsupported is False
    assert hass.states.get(shop).state == "1"


async def test_polling_and_push_refresh(hass, api, entry, account):
    """Poll slowly while push is up, faster without it; push asks for a read."""
    account["http2"] = MagicMock()
    await _load(hass, entry)
    coordinator = account[ACCOUNT_KEY]
    assert coordinator.update_interval == LISTS_SCAN_INTERVAL

    account["http2"] = None
    await coordinator.async_refresh()
    assert coordinator.update_interval == LISTS_SCAN_INTERVAL_WITHOUT_PUSH

    api.get_lists.reset_mock()
    await coordinator.async_request_refresh()
    await coordinator.async_request_refresh()
    async_fire_time_changed(
        hass, dt_util.utcnow() + timedelta(seconds=LISTS_REFRESH_COOLDOWN + 1)
    )
    await hass.async_block_till_done()
    # Two push events within the cooldown cause one read.
    api.get_lists.assert_awaited_once()


async def test_unload_stops_the_lists(hass, api, entry, account):
    """Unloading removes the coordinator and stops polling."""
    await _load(hass, entry)
    assert ACCOUNT_KEY in account

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert ACCOUNT_KEY not in account
    api.get_lists.reset_mock()

    async_fire_time_changed(hass, dt_util.utcnow() + LISTS_SCAN_INTERVAL * 2)
    await hass.async_block_till_done()
    api.get_lists.assert_not_awaited()


async def test_relogin_uses_the_new_login(hass, api, entry, account):
    """The coordinator reads the login of the account at each request."""
    await _load(hass, entry)
    new_login = MagicMock(email=EMAIL, url="amazon.com")
    account["login_obj"] = new_login

    await account[ACCOUNT_KEY].async_refresh()

    assert api.get_lists.await_args.args[0] is new_login


@pytest.mark.parametrize("forwarded", [True, False])
async def test_entry_unload_unloads_the_lists_only_when_loaded(forwarded):
    """The account unload unloads the to-do platform it forwarded, and only then."""
    hass = MagicMock()
    hass.config_entries.async_forward_entry_unload = AsyncMock(return_value=True)
    account = {"login_obj": MagicMock()}
    if forwarded:
        account["todo_forwarded"] = True
    hass.data = {
        DATA_ALEXAMEDIA: {"services": MagicMock(), "accounts": {EMAIL: account}}
    }
    config_entry = MagicMock(data={"email": EMAIL})
    with (
        patch("custom_components.alexa_media.ALEXA_COMPONENTS", []),
        patch("custom_components.alexa_media.DEPENDENT_ALEXA_COMPONENTS", []),
        patch(
            "custom_components.alexa_media.close_connections", new_callable=AsyncMock
        ),
    ):
        assert await alexa_media.async_unload_entry(hass, config_entry)

    unloaded = [
        call.args
        for call in hass.config_entries.async_forward_entry_unload.await_args_list
    ]
    assert unloaded == ([(config_entry, "todo")] if forwarded else [])
    assert "todo_forwarded" not in account


async def test_item_read_errors_keep_the_cached_items(hass, api, entry, account):
    """An exception while reading items, or a missing login, keeps the cache."""
    await _load(hass, entry)
    coordinator = account[ACCOUNT_KEY]
    shop = _entity_id(hass, entry, "shop-1")

    api.items["shop-1"].clear()
    api.read_items.side_effect = AlexapyConnectionError("down")
    await coordinator.async_refresh()
    assert hass.states.get(shop).state == "1"

    api.read_items.side_effect = lambda login, list_id, **kwargs: deepcopy(
        api.items[list_id]
    )
    account["login_obj"] = None
    await coordinator.async_refresh()
    assert hass.states.get(shop).state == "1"
    api.get_lists.reset_mock()
    with pytest.raises(HomeAssistantError, match="not loaded"):
        await hass.services.async_call(
            TODO_DOMAIN,
            "add_item",
            {"item": "bread"},
            target={"entity_id": shop},
            blocking=True,
        )
    api.add_list_item.assert_not_awaited()


async def test_a_write_on_an_item_that_is_gone_raises(hass, api, entry):
    """An item missing from the cache has no version to write with."""
    from homeassistant.components.todo import TodoItem

    await _load(hass, entry)
    entity = hass.data["entity_components"][TODO_DOMAIN].get_entity(
        _entity_id(hass, entry, "shop-1")
    )

    with pytest.raises(HomeAssistantError, match="not on the Alexa list"):
        await entity.async_update_todo_item(TodoItem(uid="gone", summary="gone"))
    api.update_list_item.assert_not_awaited()


async def test_login_errors_report_relogin_once_per_episode(hass, api, entry, account):
    """Reads and writes report a list API login failure once per episode."""
    await _load(hass, entry)
    coordinator = account[ACCOUNT_KEY]
    shop = _entity_id(hass, entry, "shop-1")
    login = account["login_obj"]

    with patch(
        "custom_components.alexa_media.todo.report_relogin_required",
        return_value=True,
    ) as report:
        api.get_lists.side_effect = AlexapyLoginError("401")
        await coordinator.async_refresh()
        await coordinator.async_refresh()
        report.assert_called_once_with(hass, login, EMAIL, require_status=False)
        # Cached lists stay available during the episode.
        assert hass.states.get(shop).state == "1"

        api.add_list_item.side_effect = AlexapyLoginError("401")
        with pytest.raises(HomeAssistantError, match="Unable to add the item"):
            await hass.services.async_call(
                TODO_DOMAIN,
                "add_item",
                {"item": "bread"},
                target={"entity_id": shop},
                blocking=True,
            )
        report.assert_called_once()

        # A good read ends the episode; the next failure reports again.
        api.get_lists.side_effect = lambda login, **kwargs: deepcopy(LISTS)
        await coordinator.async_refresh()
        api.read_items.side_effect = AlexapyLoginError("401")
        await coordinator.async_refresh()
        assert report.call_count == 2
        assert hass.states.get(shop).state == "1"


async def test_a_readback_keeps_a_pending_push_refresh(hass, api, entry, account):
    """A write to one list does not cancel a refresh that a push requested."""
    await _load(hass, entry)
    coordinator = account[ACCOUNT_KEY]
    shop = _entity_id(hass, entry, "shop-1")
    api.get_lists.reset_mock()

    await coordinator.async_request_refresh()
    await hass.services.async_call(
        TODO_DOMAIN,
        "add_item",
        {"item": "bread"},
        target={"entity_id": shop},
        blocking=True,
    )
    async_fire_time_changed(
        hass, dt_util.utcnow() + timedelta(seconds=LISTS_REFRESH_COOLDOWN + 1)
    )
    await hass.async_block_till_done()

    api.get_lists.assert_awaited_once()


def _paged(records, size=100):
    """Serve records like the list API: pages of `size` with a continuation token."""

    async def _page(login, list_id, *, limit=100, next_token=None):
        start = int(next_token or 0)
        end = start + size
        return {
            "itemInfoList": deepcopy(records[start:end]),
            "nextToken": str(end) if end < len(records) else None,
        }

    return _page


def _records(status, count, prefix):
    return [
        {
            "itemId": f"{prefix}{index}",
            "itemName": f"{prefix} {index}",
            "itemStatus": status,
            "version": 1,
        }
        for index in range(count)
    ]


async def test_a_long_history_of_completed_items_is_not_read(hass, api, entry):
    """Paging stops after the first page of only completed items."""
    # Open items come first, as the list API returns them.
    records = _records("ACTIVE", 30, "open") + _records("COMPLETE", 3588, "done")
    api.get_list_items_page.side_effect = _paged(records)
    await _load(hass, entry)
    shop = _entity_id(hass, entry, "shop-1")

    shop_reads = [
        call
        for call in api.get_list_items_page.await_args_list
        if call.args[1] == "shop-1"
    ]
    assert len(shop_reads) == 2
    assert hass.states.get(shop).state == "30"
    items = await _items(hass, shop)
    assert len([item for item in items if item["status"] == "completed"]) == 170


async def test_open_items_on_later_pages_are_read(hass, api, entry):
    """Pages that still hold open items are read to the end of the open items."""
    records = _records("ACTIVE", 105, "open") + _records("COMPLETE", 500, "done")
    api.get_list_items_page.side_effect = _paged(records)
    await _load(hass, entry)

    shop_reads = [
        call
        for call in api.get_list_items_page.await_args_list
        if call.args[1] == "shop-1"
    ]
    # Page 2 holds the last 5 open items, page 3 only completed ones.
    assert len(shop_reads) == 3
    assert hass.states.get(_entity_id(hass, entry, "shop-1")).state == "105"


@pytest.mark.parametrize(
    "page",
    [
        pytest.param(None, id="no-page"),
        pytest.param({"itemInfoList": "milk"}, id="not-a-list"),
        pytest.param({"itemInfoList": [{"itemName": "milk"}]}, id="no-item-id"),
        pytest.param({"itemInfoList": ["milk"]}, id="not-a-record"),
        pytest.param(
            {"itemInfoList": _records("ACTIVE", 1, "x"), "nextToken": 5},
            id="bad-token",
        ),
    ],
)
async def test_a_malformed_item_page_keeps_the_cached_items(
    hass, api, entry, account, page
):
    """A malformed page is a failed read of that list, not a shorter list."""
    await _load(hass, entry)
    shop = _entity_id(hass, entry, "shop-1")
    custom = _entity_id(hass, entry, "custom-1")
    api.get_list_items_page.side_effect = lambda login, list_id, **kwargs: (
        deepcopy(page) if list_id == "shop-1" else {"itemInfoList": []}
    )

    await account[ACCOUNT_KEY].async_refresh()

    assert hass.states.get(shop).state == "1"
    assert hass.states.get(custom).state == "0"


async def test_a_repeated_token_keeps_the_cached_items(hass, api, entry, account):
    """A continuation token that comes back again ends the read as a failure."""
    await _load(hass, entry)
    shop = _entity_id(hass, entry, "shop-1")
    api.get_list_items_page.side_effect = lambda login, list_id, **kwargs: {
        "itemInfoList": _records("ACTIVE", 1, list_id),
        "nextToken": "same",
    }

    await account[ACCOUNT_KEY].async_refresh()

    assert hass.states.get(shop).state == "1"
    assert api.get_list_items_page.await_count < 20
