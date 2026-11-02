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
    hook = next(
        node for node in tree.body if getattr(node, "name", "") == "async_remove_entry"
    )
    namespace = {
        "AlexaLogin": Mock(return_value=SimpleNamespace(delete_cookiefile=AsyncMock())),
        "hide_email": hide_email,
        "DOMAIN": "alexa_media",
        "_LOGGER": logging.getLogger("cookie_removal_test"),
        "os": os,
        "alexapy_delete_cookie": delete_cookie,
    }
    namespace["AlexaLogin"].delete_cookiefile = AsyncMock()
    exec(  # nosec B102: execute only the repository hook to isolate HA imports
        compile(ast.Module(body=[hook], type_ignores=[]), str(source), "exec"),
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
async def test_remove_failure_reports_current_path(removal_context, caplog):
    """Manual cleanup guidance names the JSON file without exposing the account."""
    namespace, hass, entry, cookie = removal_context
    namespace["AlexaLogin"].return_value.delete_cookiefile.side_effect = OSError(
        "denied"
    )
    assert await namespace["async_remove_entry"](hass, entry)
    assert cookie.exists()
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
