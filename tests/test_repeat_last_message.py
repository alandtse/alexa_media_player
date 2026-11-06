"""Tests for the repeat_last_message service."""

from unittest.mock import AsyncMock, MagicMock

from homeassistant.exceptions import ServiceValidationError
import pytest
from pytest_homeassistant_custom_component.common import MockEntityPlatform

from custom_components.alexa_media.const import (
    CONF_QUEUE_DELAY,
    DATA_ALEXAMEDIA,
    DOMAIN,
    SERVICE_REPEAT_LAST_MESSAGE,
)
from custom_components.alexa_media.media_player import AlexaClient
from custom_components.alexa_media.notify import AlexaNotificationService
from custom_components.alexa_media.services import AlexaMediaServices

EMAIL = "test@example.com"


def _device(serial, name, online=True):
    """Return the device data AlexaClient reads."""
    return {
        "accountName": name,
        "deviceFamily": "ECHO",
        "deviceType": "A3S5BH2HU6VAYF",
        "serialNumber": serial,
        "appDeviceList": [],
        "deviceOwnerCustomerId": "CUSTOMER1",
        "softwareVersion": "1",
        "online": online,
        "capabilities": [],
        "clusterMembers": [],
        "parentClusters": [],
        "auth_info": {
            "authenticated": True,
            "canAccessPrimeMusicContent": False,
            "customerEmail": EMAIL,
            "customerId": "CUSTOMER1",
            "customerName": "Test",
        },
    }


class TestRepeatLastMessage:
    """Test remembering and repeating the last notify message."""

    async def _setup(self, hass, *names):
        """Add a media player for each name and register the services."""
        login = MagicMock(email=EMAIL, url="amazon.com")
        login.session.closed = False
        account = {
            "login_obj": login,
            "options": {CONF_QUEUE_DELAY: 1.5},
            "entities": {"media_player": {}},
            "devices": {"media_player": {}},
        }
        hass.data[DATA_ALEXAMEDIA] = {"accounts": {EMAIL: account}}
        platform = MockEntityPlatform(hass, domain="media_player", platform_name=DOMAIN)
        clients = []
        for index, name in enumerate(names):
            serial = f"SERIAL{index}"
            device = _device(serial, name)
            account["devices"]["media_player"][serial] = device
            client = AlexaClient(device, login)
            client.alexa_api = MagicMock()
            client.alexa_api.update_login.return_value = False
            client.alexa_api.send_tts = AsyncMock()
            client.alexa_api.send_announcement = AsyncMock()
            client.alexa_api.send_mobilepush = AsyncMock()
            await client.init(device)
            account["entities"]["media_player"][serial] = client
            clients.append(client)
        await platform.async_add_entities(clients)
        await AlexaMediaServices(hass, functions={}).register()
        await hass.async_block_till_done()
        return clients

    async def _notify(self, hass, message, targets, data=None):
        """Send a message through the notify service."""
        service = AlexaNotificationService(hass)
        await service.async_send_message(message, target=targets, data=data)
        await hass.async_block_till_done()

    async def _repeat(self, hass, entity_ids):
        """Call the repeat_last_message service."""
        await hass.services.async_call(
            DOMAIN,
            SERVICE_REPEAT_LAST_MESSAGE,
            {"entity_id": entity_ids},
            blocking=True,
        )
        await hass.async_block_till_done()

    async def test_tts_is_remembered_and_repeated(self, hass):
        """A TTS message is stored on its target and sent again as TTS."""
        kitchen, office = await self._setup(hass, "Kitchen", "Office")

        await self._notify(hass, "Dinner is ready", ["media_player.kitchen"])

        state = hass.states.get("media_player.kitchen")
        assert state.attributes["last_message"] == "Dinner is ready"
        assert state.attributes["last_message_type"] == "tts"
        assert "last_message" in state.state_info["unrecorded_attributes"]
        assert hass.states.get("media_player.office").attributes["last_message"] is None

        kitchen.alexa_api.send_tts.reset_mock()
        await self._repeat(hass, "media_player.kitchen")

        kitchen.alexa_api.send_tts.assert_awaited_once_with(
            "Dinner is ready", customer_id="CUSTOMER1", queue_delay=1.5
        )
        office.alexa_api.send_tts.assert_not_called()

    async def test_announcement_is_remembered_and_repeated(self, hass):
        """An announcement is stored on each target and repeated on one only."""
        kitchen, office = await self._setup(hass, "Kitchen", "Office")

        await self._notify(
            hass,
            "Washing is done",
            ["media_player.kitchen", "media_player.office"],
            {"type": "announce", "method": "speak"},
        )

        for entity_id in ("media_player.kitchen", "media_player.office"):
            state = hass.states.get(entity_id)
            assert state.attributes["last_message"] == "Washing is done"
            assert state.attributes["last_message_type"] == "announce"

        kitchen.alexa_api.send_announcement.reset_mock()
        office.alexa_api.send_announcement.reset_mock()
        await self._repeat(hass, "media_player.office")

        office.alexa_api.send_announcement.assert_awaited_once_with(
            "Washing is done",
            customer_id="CUSTOMER1",
            targets=["SERIAL1"],
            title="Home Assistant",
            method="speak",
            queue_delay=1.5,
        )
        kitchen.alexa_api.send_announcement.assert_not_called()

    async def test_group_announcement_is_remembered_on_members(self, hass):
        """An announcement to a group is stored on the group and its members."""
        group, kitchen, office = await self._setup(
            hass, "Everywhere", "Kitchen", "Office"
        )
        group._cluster_members = ["SERIAL1"]

        await self._notify(
            hass,
            "Washing is done",
            ["media_player.everywhere"],
            {"type": "announce", "method": "speak"},
        )

        for entity_id in ("media_player.everywhere", "media_player.kitchen"):
            state = hass.states.get(entity_id)
            assert state.attributes["last_message"] == "Washing is done"
            assert state.attributes["last_message_type"] == "announce"
        assert hass.states.get("media_player.office").attributes["last_message"] is None

        group.alexa_api.send_announcement.reset_mock()
        await self._repeat(hass, "media_player.kitchen")

        kitchen.alexa_api.send_announcement.assert_awaited_once_with(
            "Washing is done",
            customer_id="CUSTOMER1",
            targets=["SERIAL1"],
            title="Home Assistant",
            method="speak",
            queue_delay=1.5,
        )
        group.alexa_api.send_announcement.assert_not_called()
        office.alexa_api.send_announcement.assert_not_called()

    async def test_nothing_to_repeat(self, hass):
        """The service fails when no message has been stored."""
        (kitchen,) = await self._setup(hass, "Kitchen")

        with pytest.raises(ServiceValidationError, match="No message to repeat"):
            await self._repeat(hass, "media_player.kitchen")

        kitchen.alexa_api.send_tts.assert_not_called()
        kitchen.alexa_api.send_announcement.assert_not_called()

    async def test_push_is_not_remembered(self, hass):
        """A push notification doesn't replace the last spoken message."""
        await self._setup(hass, "Kitchen")
        await self._notify(hass, "Dinner is ready", ["media_player.kitchen"])

        await self._notify(
            hass, "Check your phone", ["media_player.kitchen"], {"type": "push"}
        )

        state = hass.states.get("media_player.kitchen")
        assert state.attributes["last_message"] == "Dinner is ready"

    async def test_unavailable_echo_does_not_repeat(self, hass):
        """The message is kept while the Echo is offline but not sent."""
        (kitchen,) = await self._setup(hass, "Kitchen")
        await self._notify(hass, "Dinner is ready", ["media_player.kitchen"])
        kitchen.alexa_api.send_tts.reset_mock()

        await kitchen.refresh(
            _device("SERIAL0", "Kitchen", online=False), skip_api=True
        )
        with pytest.raises(ServiceValidationError, match="is unavailable"):
            await self._repeat(hass, "media_player.kitchen")
        kitchen.alexa_api.send_tts.assert_not_called()

        await kitchen.refresh(_device("SERIAL0", "Kitchen"), skip_api=True)
        await self._repeat(hass, "media_player.kitchen")
        kitchen.alexa_api.send_tts.assert_awaited_once()

    async def test_missing_account_does_not_repeat(self, hass):
        """The service fails cleanly if the Echo's account has gone."""
        (kitchen,) = await self._setup(hass, "Kitchen")
        await self._notify(hass, "Dinner is ready", ["media_player.kitchen"])
        kitchen.alexa_api.send_tts.reset_mock()
        accounts = hass.data[DATA_ALEXAMEDIA]["accounts"]
        accounts["new@example.com"] = accounts.pop(EMAIL)

        with pytest.raises(ServiceValidationError, match="No account found"):
            await self._repeat(hass, "media_player.kitchen")
        kitchen.alexa_api.send_tts.assert_not_called()

    async def test_service_repeats_each_entity(self, hass):
        """Each Echo in the list repeats its own message, then unknown ones fail."""
        kitchen, office = await self._setup(hass, "Kitchen", "Office")
        await self._notify(hass, "Dinner is ready", ["media_player.kitchen"])
        await self._notify(hass, "Meeting in 5", ["media_player.office"])
        kitchen.alexa_api.send_tts.reset_mock()
        office.alexa_api.send_tts.reset_mock()

        with pytest.raises(ServiceValidationError, match=r"media_player\.unknown"):
            await self._repeat(
                hass,
                ["media_player.kitchen", "media_player.unknown", "media_player.office"],
            )

        assert kitchen.alexa_api.send_tts.await_args.args == ("Dinner is ready",)
        assert office.alexa_api.send_tts.await_args.args == ("Meeting in 5",)
