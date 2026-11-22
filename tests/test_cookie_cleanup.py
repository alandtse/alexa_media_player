"""Regression tests for cookie cleanup without a Home Assistant runtime."""

import ast
import logging
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from alexapy import AlexaLogin, hide_email
from alexapy.helpers import delete_cookie
import pytest


@pytest.fixture
def removal_context(tmp_path):
    """Load the removal hook in isolation from unrelated HA startup imports."""
    source = Path(__file__).parents[1] / "custom_components/alexa_media/__init__.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    hooks = {
        node.name: node
        for node in tree.body
        if getattr(node, "name", "") in ("async_remove_entry", "_stop_display_recovery")
    }
    namespace = {
        "AlexaLogin": Mock(return_value=SimpleNamespace(delete_cookiefile=AsyncMock())),
        "hide_email": hide_email,
        "DOMAIN": "alexa_media",
        "_LOGGER": logging.getLogger("cookie_removal_test"),
        "os": os,
        "alexapy_delete_cookie": delete_cookie,
        # Account listeners are unrelated to cookie cleanup; the hook only
        # calls this helper when an entry is removed.
        "_pop_relogin_listeners": lambda *_: None,
        "_retire_runtime_account": AsyncMock(),
    }
    namespace["AlexaLogin"].delete_cookiefile = AsyncMock()
    exec(  # nosec B102: execute only the repository hook to isolate HA imports
        compile(
            ast.Module(
                body=[hooks["_stop_display_recovery"], hooks["async_remove_entry"]],
                type_ignores=[],
            ),
            str(source),
            "exec",
        ),
        namespace,
    )
    hass = SimpleNamespace(
        config=SimpleNamespace(path=lambda path: str(tmp_path / path))
    )
    entry = SimpleNamespace(data={"email": "test@example.com"})
    cookie = tmp_path / ".storage/alexa_media.test@example.com.cookies"
    cookie.parent.mkdir()
    cookie.write_text('{"format": "alexapy.cookies", "version": 1, "cookies": []}')
    return namespace, hass, entry, cookie


@pytest.mark.asyncio
async def test_remove_delegates_to_alexapy(removal_context, caplog):
    """Use alexapy's deletion API and report the current, obscured path."""
    namespace, hass, entry, cookie = removal_context
    delete = namespace["AlexaLogin"].return_value.delete_cookiefile
    delete.side_effect = lambda: cookie.unlink()
    with caplog.at_level(logging.DEBUG):
        assert await namespace["async_remove_entry"](hass, entry)
    delete.assert_awaited_once_with()
    assert not cookie.exists()
    assert ".cookies" in caplog.text
    assert all(
        entry.data["email"] not in record.getMessage()
        for record in caplog.records
        if record.name == "cookie_removal_test"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("raises", [True, False])
async def test_remove_failure_reports_current_path(removal_context, caplog, raises):
    """Manual cleanup guidance names the JSON file without exposing the account."""
    namespace, hass, entry, cookie = removal_context
    delete = namespace["AlexaLogin"].return_value.delete_cookiefile
    if raises:
        delete.side_effect = OSError("denied")
    with caplog.at_level(logging.DEBUG):
        assert await namespace["async_remove_entry"](hass, entry)
    delete.assert_awaited_once_with()
    assert cookie.exists()
    assert "Cookiefile %s deleted." not in [record.msg for record in caplog.records]
    assert any(record.levelno == logging.ERROR for record in caplog.records)
    assert "Manually delete cookiefile" in caplog.text
    assert f"alexa_media.{hide_email(entry.data['email'])}.cookies" in caplog.text
    assert all(
        entry.data["email"] not in record.getMessage()
        for record in caplog.records
        if record.name == "cookie_removal_test"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("exists", [True, False])
async def test_remove_fallback_targets_json_file(removal_context, caplog, exists):
    """The compatibility fallback removes the JSON file or reports it missing."""
    namespace, hass, entry, cookie = removal_context
    namespace["AlexaLogin"].delete_cookiefile = None
    if not exists:
        cookie.unlink()
    with caplog.at_level(logging.DEBUG):
        assert await namespace["async_remove_entry"](hass, entry)
    assert not cookie.exists()
    assert ("Successfully deleted" if exists else "Cookiefile not found") in caplog.text
    assert ".cookies" in caplog.text
    assert all(
        entry.data["email"] not in record.getMessage()
        for record in caplog.records
        if record.name == "cookie_removal_test"
    )


@pytest.mark.asyncio
async def test_alexapy_deletes_current_cookie_file(tmp_path):
    """Verify the pinned dependency deletes its persisted JSON file."""
    cookie = tmp_path / ".storage/alexa_media.test@example.com.cookies"
    cookie.parent.mkdir()
    cookie.write_text('{"format": "alexapy.cookies", "version": 1, "cookies": []}')
    login = AlexaLogin(
        "amazon.com", "test@example.com", "", lambda path: str(tmp_path / path)
    )
    try:
        await login.delete_cookiefile()
        assert not cookie.exists()
    finally:
        await login.close()


@pytest.mark.asyncio
async def test_remove_clears_display_recovery_state(removal_context):
    """Removing an entry stops display polling and drops its recovery state."""
    namespace, hass, entry, cookie = removal_context
    namespace["DATA_ALEXAMEDIA"] = "alexa_media"
    entry.entry_id = "entry"
    display_state = Mock()
    probe = Mock()
    probe.done.return_value = False
    setup_task = Mock()
    setup_task.done.return_value = False
    unsub = Mock()
    hass.data = {
        "alexa_media": {
            "accounts": {
                "test@example.com": {
                    "config_entry": entry,
                    "display_states": {"SERIAL": display_state},
                    "display_probes": {"SERIAL": probe},
                    "display_setup_tasks": {setup_task},
                    "display_reload_unsub": unsub,
                }
            },
            "display_entry_states": {"entry": {"pending": {"SERIAL"}}},
            "display_reload_budget": {"entry": 1},
            "display_relogin_reported": {"test@example.com"},
        }
    }
    delete = namespace["AlexaLogin"].return_value.delete_cookiefile
    delete.side_effect = lambda: cookie.unlink()

    assert await namespace["async_remove_entry"](hass, entry)

    display_state.async_stop.assert_called_once()
    probe.cancel.assert_called_once()
    setup_task.cancel.assert_called_once()
    unsub.assert_called_once()
    integration_data = hass.data["alexa_media"]
    assert "entry" not in integration_data["display_entry_states"]
    assert "entry" not in integration_data["display_reload_budget"]
    assert "test@example.com" not in integration_data["display_relogin_reported"]
