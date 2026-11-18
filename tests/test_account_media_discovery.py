"""Regression coverage for Echo discovery after account-only startup."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.alexa_media.const import DOMAIN
from custom_components.alexa_media.media_player import async_setup_platform


@pytest.mark.asyncio
async def test_late_echo_uses_existing_entity_adder_without_platform_forward() -> None:
    """Add the first Echo after account diagnostics have loaded, without forwarding."""
    email = "account@example.com"
    existing_callback = MagicMock()
    discovery_callback = MagicMock()
    account = {
        "entities": {"media_player": {}},
        "devices": {
            "media_player": {
                "SERIAL1": {
                    "accountName": "Kitchen Echo",
                    "serialNumber": "SERIAL1",
                }
            }
        },
        "login_obj": SimpleNamespace(email=email),
        "second_account_index": 0,
        "media_player_add_entities": existing_callback,
        "media_player_platform_loaded": True,
        "account_diagnostic_platforms_loaded": {"sensor", "binary_sensor"},
    }
    hass = MagicMock(data={DOMAIN: {"accounts": {email: account}}})
    client = SimpleNamespace(
        name="Kitchen Echo",
        unique_id="SERIAL1",
        init=AsyncMock(),
        entity_id=None,
    )

    with (
        patch(
            "custom_components.alexa_media.media_player.create_www_directory",
            new_callable=AsyncMock,
        ),
        patch(
            "custom_components.alexa_media.media_player.AlexaClient",
            return_value=client,
        ) as client_factory,
    ):
        assert await async_setup_platform(
            hass, {"email": email}, discovery_callback, discover_only=True
        )
        client_factory.assert_called_once()
        client.init.assert_awaited_once()
        discovery_callback.assert_called_once_with([client])
        existing_callback.assert_not_called()
        assert account["entities"]["media_player"]["SERIAL1"] is client
        assert account["media_player_add_entities"] is existing_callback

        # A later inventory refresh must not duplicate the Echo.
        assert await async_setup_platform(
            hass, {"email": email}, existing_callback, discover_only=True
        )
        discovery_callback.assert_called_once()
        existing_callback.assert_not_called()
        hass.async_create_task.assert_not_called()
