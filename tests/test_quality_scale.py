"""Regression tests for integration quality-scale baseline fixes."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import ServiceValidationError
import pytest

from custom_components.alexa_media import async_setup, async_unload_entry
from custom_components.alexa_media.config_flow import OptionsFlowHandler
from custom_components.alexa_media.const import (
    CONF_DEBUG,
    DATA_ALEXAMEDIA,
    DEFAULT_DEBUG,
)
from custom_components.alexa_media.helpers import config_entry_option
from custom_components.alexa_media.services import AlexaMediaServices

EMAIL = "test@example.com"  # noqa: S105


def test_config_entry_option_prefers_options():
    """Options win over legacy values still stored in data."""
    entry = MagicMock()
    entry.options = {CONF_DEBUG: True}
    entry.data = {CONF_DEBUG: False}

    assert config_entry_option(entry, CONF_DEBUG, DEFAULT_DEBUG) is True


def test_config_entry_option_falls_back_to_data():
    """Entries created before the options split keep working."""
    entry = MagicMock()
    entry.options = {}
    entry.data = {CONF_DEBUG: True}

    assert config_entry_option(entry, CONF_DEBUG, DEFAULT_DEBUG) is True


@pytest.mark.asyncio
async def test_options_flow_writes_options_only():
    """The options flow must not overwrite ConfigEntry.data."""
    entry = MagicMock()
    entry.data = {"email": EMAIL}
    entry.options = {}
    entry.entry_id = "entry-id"

    handler = OptionsFlowHandler(entry)
    handler.hass = MagicMock()
    handler._config_entry = entry
    handler.async_create_entry = MagicMock(return_value={"type": "create_entry"})

    user_input = {
        "public_url": "https://example.com",
        "include_devices": " Kitchen ",
        "exclude_devices": " Garage ",
        "scan_interval": 60,
        "queue_delay": 1.5,
        "extended_entity_discovery": True,
        "debug": False,
    }

    result = await handler.async_step_init(user_input)

    handler.hass.config_entries.async_update_entry.assert_not_called()
    handler.async_create_entry.assert_called_once_with(
        title="",
        data={
            "public_url": "https://example.com/",
            "include_devices": "Kitchen",
            "exclude_devices": "Garage",
            "scan_interval": 60,
            "queue_delay": 1.5,
            "extended_entity_discovery": True,
            "debug": False,
        },
    )
    assert result == {"type": "create_entry"}


@pytest.mark.asyncio
async def test_options_flow_keeps_empty_public_url():
    """An empty public URL must stay empty, not become a root URL."""
    entry = MagicMock()
    entry.data = {"email": EMAIL}
    entry.options = {}
    entry.entry_id = "entry-id"

    handler = OptionsFlowHandler(entry)
    handler.hass = MagicMock()
    handler._config_entry = entry
    handler.async_create_entry = MagicMock(return_value={"type": "create_entry"})

    user_input = {
        "public_url": "",
        "include_devices": "",
        "exclude_devices": "",
        "scan_interval": 60,
        "queue_delay": 1.5,
        "extended_entity_discovery": False,
        "debug": False,
    }

    await handler.async_step_init(user_input)

    assert handler.async_create_entry.call_args.kwargs["data"]["public_url"] == ""


@pytest.mark.asyncio
async def test_async_setup_registers_services_once():
    """Services are registered from async_setup, not per config entry."""
    hass = MagicMock()
    hass.data = {}
    metrics = MagicMock()
    services = MagicMock()
    services.register = AsyncMock()

    with (
        patch(
            "custom_components.alexa_media.AlexaMetrics", return_value=metrics
        ) as metrics_cls,
        patch(
            "custom_components.alexa_media.async_get_integration",
            new_callable=AsyncMock,
            return_value=MagicMock(name="Alexa Media Player", version="5.19.0"),
        ),
        patch(
            "custom_components.alexa_media.AlexaMediaServices",
            return_value=services,
        ) as services_cls,
    ):
        assert await async_setup(hass, {})
        assert await async_setup(hass, {})

    metrics_cls.assert_called_with(hass)
    services_cls.assert_called_once()
    callbacks = services_cls.call_args.kwargs["functions"]
    assert callable(callbacks["update_last_called"])
    schedule = MagicMock()
    other_schedule = MagicMock()
    hass.data[DATA_ALEXAMEDIA]["accounts"] = {
        EMAIL: {"schedule_notifications_refresh": schedule},
        "other@example.com": {"schedule_notifications_refresh": other_schedule},
    }
    callbacks["schedule_notifications_refresh"](
        hass, EMAIL, device_serial="serial", reason="create_alarm"
    )
    schedule.assert_called_once_with(
        hass, EMAIL, device_serial="serial", reason="create_alarm"
    )
    other_schedule.assert_not_called()
    callbacks["schedule_notifications_refresh"](hass, "unloaded@example.com")
    # The persistent service must look up the current account after reload.
    replacement = MagicMock()
    hass.data[DATA_ALEXAMEDIA]["accounts"][EMAIL] = {
        "schedule_notifications_refresh": replacement
    }
    callbacks["schedule_notifications_refresh"](hass, EMAIL)
    replacement.assert_called_once_with(hass, EMAIL, device_serial=None, reason="")
    assert schedule.call_count == 1
    del hass.data[DATA_ALEXAMEDIA]["accounts"]
    callbacks["schedule_notifications_refresh"](hass, EMAIL)
    assert replacement.call_count == 1
    services.register.assert_awaited_once()
    assert hass.data[DATA_ALEXAMEDIA]["services"] is services


@pytest.mark.asyncio
async def test_force_logout_without_accounts_raises_service_error():
    """Registered services stay callable but explain that no account is loaded."""
    hass = MagicMock()
    hass.data = {DATA_ALEXAMEDIA: {"accounts": {EMAIL: {}}}}
    services = AlexaMediaServices(hass)
    call = MagicMock()
    call.data = {}

    with pytest.raises(ServiceValidationError):
        await services.force_logout(call)


@pytest.mark.asyncio
async def test_force_logout_rejects_requested_account_not_loaded():
    """A request naming an unloaded account is rejected before any change."""
    hass = MagicMock()
    hass.data = {
        DATA_ALEXAMEDIA: {
            "accounts": {
                EMAIL: {
                    "login_obj": MagicMock(email=EMAIL),
                    "config_entry": MagicMock(state=ConfigEntryState.LOADED),
                }
            }
        }
    }
    services = AlexaMediaServices(hass)
    call = MagicMock()
    call.data = {"email": ["other@example.com"]}

    with pytest.raises(ServiceValidationError):
        await services.force_logout(call)


@pytest.mark.asyncio
async def test_last_called_reports_requested_account_not_loaded():
    """An explicit email that is not loaded is reported, not silently skipped."""
    hass = MagicMock()
    hass.data = {
        DATA_ALEXAMEDIA: {
            "accounts": {
                EMAIL: {
                    "login_obj": MagicMock(email=EMAIL),
                    "config_entry": MagicMock(state=ConfigEntryState.LOADED),
                }
            }
        }
    }
    services = AlexaMediaServices(hass, functions={"update_last_called": AsyncMock()})
    call = MagicMock()
    call.data = {"email": ["other@example.com"]}

    with pytest.raises(ServiceValidationError):
        await services.last_call_handler(call)


@pytest.mark.asyncio
async def test_update_last_called_service_uses_registered_callback():
    """The service calls the injected update_last_called implementation."""
    login = MagicMock(email=EMAIL)
    callback = AsyncMock()
    hass = MagicMock()
    hass.data = {
        DATA_ALEXAMEDIA: {
            "accounts": {
                EMAIL: {
                    "login_obj": login,
                    "config_entry": MagicMock(state=ConfigEntryState.LOADED),
                    "service_update_last_called_task": None,
                }
            }
        }
    }
    tasks = []

    def _create_task(coro, name=None):
        task = asyncio.create_task(coro)
        tasks.append(task)
        return task

    hass.async_create_task.side_effect = _create_task
    services = AlexaMediaServices(hass, functions={"update_last_called": callback})
    call = MagicMock()
    call.data = {"email": [EMAIL]}

    await services.last_call_handler(call)
    await asyncio.gather(*tasks)

    callback.assert_awaited_once_with(login)


@pytest.mark.asyncio
@pytest.mark.parametrize("reload_account", [False, True])
async def test_cancelled_last_called_task_preserves_replacement(reload_account):
    """A cancelled request cannot hide the task that unload still needs to cancel."""
    started = asyncio.Event()
    release = asyncio.Event()

    async def callback(login):
        started.set()
        await release.wait()

    def account():
        return {
            "login_obj": MagicMock(email=EMAIL),
            "config_entry": MagicMock(state=ConfigEntryState.LOADED),
        }

    hass = MagicMock()
    accounts = {EMAIL: account()}
    hass.data = {DATA_ALEXAMEDIA: {"accounts": accounts}}
    hass.async_create_task.side_effect = lambda coro, **kwargs: asyncio.create_task(
        coro
    )
    services = AlexaMediaServices(hass, functions={"update_last_called": callback})
    call = MagicMock(data={"email": [EMAIL]})
    await services.last_call_handler(call)
    old = accounts[EMAIL]["service_update_last_called_task"]
    await started.wait()
    if reload_account:
        old.cancel()
        accounts[EMAIL] = account()
    await services.last_call_handler(call)
    new = accounts[EMAIL]["service_update_last_called_task"]
    try:
        await asyncio.gather(old, return_exceptions=True)
        assert accounts[EMAIL].get("service_update_last_called_task") is new
    finally:
        release.set()
        await asyncio.gather(old, new, return_exceptions=True)
    assert "service_update_last_called_task" not in accounts[EMAIL]


@pytest.mark.asyncio
async def test_services_survive_unloading_last_account():
    """Unloading accounts cancels work but keeps the one-time domain services."""
    hass = MagicMock()
    services = AlexaMediaServices(hass, functions={"update_last_called": AsyncMock()})
    other_email = "other@example.com"
    hass.data = {
        DATA_ALEXAMEDIA: {
            "services": services,
            "accounts": {
                EMAIL: {"login_obj": MagicMock()},
                other_email: {"login_obj": MagicMock()},
            },
            "metrics": MagicMock(),
            "notify_service": MagicMock(),
        }
    }
    await services.register()
    registrations = hass.services.async_register.call_count
    with (
        patch("custom_components.alexa_media.ALEXA_COMPONENTS", []),
        patch("custom_components.alexa_media.DEPENDENT_ALEXA_COMPONENTS", []),
        patch(
            "custom_components.alexa_media.close_connections", new_callable=AsyncMock
        ),
    ):
        assert await async_unload_entry(hass, MagicMock(data={"email": EMAIL}))
        assert other_email in hass.data[DATA_ALEXAMEDIA]["accounts"]
        assert await async_unload_entry(hass, MagicMock(data={"email": other_email}))
    assert hass.data[DATA_ALEXAMEDIA]["services"] is services
    assert "accounts" not in hass.data[DATA_ALEXAMEDIA]
    assert "metrics" not in hass.data[DATA_ALEXAMEDIA]
    assert "notify_service" not in hass.data[DATA_ALEXAMEDIA]
    assert hass.services.async_register.call_count == registrations
    hass.services.async_remove.assert_not_called()
    with pytest.raises(ServiceValidationError):
        await services.last_call_handler(MagicMock(data={}))
