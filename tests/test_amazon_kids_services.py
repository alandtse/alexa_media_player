"""Tests for the Amazon Kids services refreshing the shared state."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.alexa_media.const import DATA_ALEXAMEDIA
from custom_components.alexa_media.services import AlexaMediaServices


@pytest.fixture
def setup():
    """Provide services for two accounts with mocked Amazon Kids state."""
    login = MagicMock(email="kids@example.com")
    other_login = MagicMock(email="other@example.com")
    kids_state = MagicMock(async_refresh=AsyncMock())
    other_state = MagicMock(async_refresh=AsyncMock())
    hass = MagicMock()
    hass.data = {
        DATA_ALEXAMEDIA: {
            "accounts": {
                "other@example.com": {
                    "login_obj": other_login,
                    "amazon_kids": other_state,
                },
                "kids@example.com": {"login_obj": login, "amazon_kids": kids_state},
            }
        }
    }
    services = AlexaMediaServices(hass, {})
    with (
        patch("custom_components.alexa_media.services.AlexaAPI") as api,
        patch.object(
            AlexaMediaServices,
            "_resolve_device",
            return_value=(login, "SERIAL", "TYPE"),
        ),
    ):
        api.enable_child_mode = AsyncMock()
        api.disable_child_mode = AsyncMock()
        yield services, api, login, kids_state, other_state


async def test_enable_refreshes_kids_state_of_account(setup):
    """Enabling shows on the switch and select without waiting for a poll."""
    services, api, login, kids_state, other_state = setup
    call = MagicMock(
        data={"entity_id": "media_player.kids_room", "child": "amzn1.account.CHILD"}
    )

    assert await services.amazon_kids_enable(call) is True

    api.enable_child_mode.assert_awaited_once_with(
        login, "SERIAL", "TYPE", "amzn1.account.CHILD"
    )
    kids_state.async_refresh.assert_awaited_once_with()
    other_state.async_refresh.assert_not_awaited()


async def test_disable_refreshes_kids_state_of_account(setup):
    """Disabling shows on the switch and select without waiting for a poll."""
    services, api, login, kids_state, other_state = setup
    call = MagicMock(data={"entity_id": "media_player.kids_room"})

    assert await services.amazon_kids_disable(call) is True

    api.disable_child_mode.assert_awaited_once_with(login, "SERIAL", "TYPE")
    kids_state.async_refresh.assert_awaited_once_with()
    other_state.async_refresh.assert_not_awaited()


async def test_unknown_child_changes_and_refreshes_nothing(setup):
    """A child that cannot be resolved leaves the device and state alone."""
    services, api, _login, kids_state, _other_state = setup
    api.get_child_profiles = AsyncMock(return_value=[])
    call = MagicMock(data={"entity_id": "media_player.kids_room", "child": "Nobody"})

    assert await services.amazon_kids_enable(call) is False

    api.enable_child_mode.assert_not_awaited()
    kids_state.async_refresh.assert_not_awaited()


async def test_service_works_before_kids_state_exists(setup):
    """Without Kids entities set up there is no shared state to refresh."""
    services, api, _login, _kids_state, _other_state = setup
    services.hass.data[DATA_ALEXAMEDIA]["accounts"]["kids@example.com"][
        "amazon_kids"
    ] = None
    call = MagicMock(data={"entity_id": "media_player.kids_room"})

    assert await services.amazon_kids_disable(call) is True

    api.disable_child_mode.assert_awaited_once()
