"""Tests for account-scoped GraphQL smart-home routing."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from homeassistant.exceptions import HomeAssistantError

from custom_components.alexa_media.alexa_entity import sensor_polling_endpoints
from custom_components.alexa_media.smart_home_control import (
    AlexaAPI,
    DATA_ALEXAMEDIA,
    async_control_gql,
)


def test_smart_home_mapping_opt_in():
    """Preserve the sensor-only path on published AlexaPy."""
    entities = {
        "light": [{"id": "bulb"}],
        "smart_switch": [{"id": "plug"}],
        "temperature": [{"id": "echo"}],
    }
    rows = [
        {"id": f"endpoint-{item}", "legacyAppliance": {"entityId": item}}
        for item in ("bulb", "plug", "echo")
    ]
    assert sensor_polling_endpoints(rows, entities) == rows[2:]
    assert sensor_polling_endpoints(rows, entities, include_controls=True) == rows


def test_graphql_control_and_reconciliation():
    """Always reconcile a confirmed or partially rejected operation."""
    login = SimpleNamespace(email="test")
    rows = [{"id": "endpoint", "legacyAppliance": {"entityId": "bulb"}}]
    refresh = AsyncMock()
    account = {
        "login_obj": login,
        "control_endpoint_snapshot": (login, rows),
        "confirm_refresh_debouncer": SimpleNamespace(async_call=refresh),
    }
    entity = SimpleNamespace(
        _login=login,
        alexa_entity_id="bulb",
        hass=SimpleNamespace(data={DATA_ALEXAMEDIA: {"accounts": {"test": account}}}),
    )
    with patch.object(AlexaAPI, "set_light_state_gql", None, create=True):
        assert asyncio.run(async_control_gql(entity, False)) is False

    setter = AsyncMock(side_effect=[True, False])
    with patch.object(AlexaAPI, "set_light_state_gql", setter, create=True):
        assert asyncio.run(async_control_gql(entity, False, brightness=0))
        setter.assert_called_once_with(login, "bulb", False, endpoints=rows, brightness=0)

        try:
            asyncio.run(async_control_gql(entity, True))
        except HomeAssistantError:
            pass
        else:
            raise AssertionError("Alexa did not acknowledge the command")
        assert refresh.await_count == 2

        account["login_obj"] = SimpleNamespace(email="test")
        try:
            asyncio.run(async_control_gql(entity, True))
        except HomeAssistantError:
            pass
        else:
            raise AssertionError("A stale login must never control a device")
        assert setter.call_count == 2
