"""Regression coverage for Echo discovery after account-only startup."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.alexa_media.account_platforms import sync_echo_platforms
from custom_components.alexa_media.binary_sensor import async_discover_kids
from custom_components.alexa_media.const import DOMAIN
from custom_components.alexa_media.media_player import async_setup_platform
from custom_components.alexa_media.switch import (
    RepeatSwitch,
    ShuffleSwitch,
    async_discover_music_switches,
)


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
        discovery_callback.assert_called_once_with([client], False)
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


@pytest.mark.asyncio
async def test_kids_binary_sensor_appears_when_echo_added_later() -> None:
    """An account-only binary platform can discover Kids after player creation."""
    email = "account@example.com"
    client = SimpleNamespace(device_serial_number="SERIAL1", unique_id="SERIAL1")
    account = {
        "login_obj": SimpleNamespace(email=email),
        "devices": {
            "media_player": {"SERIAL1": {"deviceFamily": "ECHO", "deviceType": "TYPE1"}}
        },
        "entities": {"media_player": {}, "binary_sensor": []},
    }
    kids = MagicMock()
    kids.async_start = AsyncMock()
    adder = MagicMock()
    with (
        patch(
            "custom_components.alexa_media.binary_sensor.async_get_state",
            return_value=kids,
        ),
        patch(
            "custom_components.alexa_media.binary_sensor.add_devices",
            new_callable=AsyncMock,
            return_value=True,
        ) as add,
        patch(
            "custom_components.alexa_media.binary_sensor.KIDS_CAPABLE_FAMILIES",
            {"ECHO"},
        ),
    ):
        assert await async_discover_kids(None, account, adder)
        add.assert_not_awaited()
        account["entities"]["media_player"]["SERIAL1"] = client
        assert await async_discover_kids(None, account, adder)
        add.assert_awaited_once()
        assert len(account["entities"]["binary_sensor"]) == 1
        kids.async_start.assert_awaited_once()
        assert await async_discover_kids(None, account, adder)
        add.assert_awaited_once()


@pytest.mark.asyncio
async def test_account_only_then_first_and_second_echo_are_reconciled() -> None:
    """Forward media_player once, then use the already-loaded adder."""
    entry = SimpleNamespace(data={"email": "account@example.com"})
    account = {
        "devices": {"media_player": {}},
        "entities": {"media_player": {}},
        "account_diagnostic_platforms_loaded": {"sensor", "binary_sensor"},
    }
    calls = []
    dependent = set()
    adder = MagicMock()

    async def initial_forward(_entry, platforms):
        calls.append(("forward", tuple(platforms)))
        account["media_player_platform_loaded"] = True
        account["media_player_add_entities"] = adder
        for key in account["devices"]["media_player"]:
            account["entities"]["media_player"][key] = object()
            dependent.add((key, "switch"))

    async def late_add(_hass, _config, callback, *, discover_only):
        calls.append(("discover_only", discover_only))
        assert callback is adder
        for key in account["devices"]["media_player"]:
            if key not in account["entities"]["media_player"]:
                account["entities"]["media_player"][key] = object()
                dependent.add((key, "switch"))
        return True

    platforms = SimpleNamespace(
        async_forward_entry_setups=AsyncMock(side_effect=initial_forward),
        async_forward_entry_unload=AsyncMock(),
    )
    hass = SimpleNamespace(config_entries=platforms)
    with patch(
        "custom_components.alexa_media.media_player.async_setup_platform",
        new_callable=AsyncMock,
        side_effect=late_add,
    ):
        await sync_echo_platforms(hass, entry, account)
        platforms.async_forward_entry_setups.assert_not_awaited()

        account["devices"]["media_player"]["SERIAL1"] = {}
        await sync_echo_platforms(hass, entry, account)
        assert account["media_player_platform_loaded"]
        platforms.async_forward_entry_setups.assert_awaited_once()

        account["devices"]["media_player"]["SERIAL2"] = {}
        await sync_echo_platforms(hass, entry, account)
        platforms.async_forward_entry_setups.assert_awaited_once()

    assert set(account["entities"]["media_player"]) == {"SERIAL1", "SERIAL2"}
    assert dependent == {("SERIAL1", "switch"), ("SERIAL2", "switch")}
    assert calls == [("forward", ("media_player",)), ("discover_only", True)]


@pytest.mark.asyncio
async def test_late_echo_creates_real_shuffle_and_repeat_switches() -> None:
    """A second Echo gains actual switch entities without media-player forwarding."""
    player = MagicMock()
    player.device_serial_number = "SERIAL2"
    account = {
        "login_obj": SimpleNamespace(email="a@example.com"),
        "devices": {
            "media_player": {
                "SERIAL1": {"capabilities": []},
                "SERIAL2": {"capabilities": ["MUSIC_SKILL"]},
            }
        },
        "entities": {
            "media_player": {"SERIAL1": MagicMock(), "SERIAL2": player},
            "switch": {"SERIAL1": {}},
        },
    }
    add = AsyncMock(return_value=True)
    with patch("custom_components.alexa_media.switch.add_devices", new=add):
        assert await async_discover_music_switches(account, MagicMock())
        switches = account["entities"]["switch"]["SERIAL2"]
        assert isinstance(switches["shuffle"], ShuffleSwitch)
        assert isinstance(switches["repeat"], RepeatSwitch)
        assert {type(x) for x in add.await_args.args[1]} == {
            ShuffleSwitch, RepeatSwitch
        }

        assert await async_discover_music_switches(account, MagicMock())
        add.assert_awaited_once()


@pytest.mark.asyncio
async def test_dependent_setup_failure_does_not_mark_media_platform_loaded() -> None:
    """An asynchronous dependent loader failure leaves setup retryable."""
    from custom_components.alexa_media import media_player as media_module

    email = "a@example.com"
    account = {"entities": {"switch": {}, "media_player": {}}}
    hass = MagicMock(data={DOMAIN: {"accounts": {email: account}}})
    entry = SimpleNamespace(data={"email": email})
    with (
        patch.object(media_module, "async_setup_platform", new_callable=AsyncMock,
                     return_value=True),
        patch.object(media_module, "config_entry_config",
                     return_value={"email": email}),
        patch.object(media_module, "DEPENDENT_ALEXA_COMPONENTS", ["switch"]),
        patch.object(media_module, "async_load_platform", new_callable=AsyncMock,
                     side_effect=RuntimeError("dependent failed")) as loader,
    ):
        with pytest.raises(RuntimeError, match="dependent failed"):
            await media_module.async_setup_entry(hass, entry, MagicMock())
        assert not account.get("media_player_platform_loaded")
        loader.assert_awaited_once()

        loader.side_effect = None
        assert await media_module.async_setup_entry(hass, entry, MagicMock())
        assert account["media_player_platform_loaded"] is True
