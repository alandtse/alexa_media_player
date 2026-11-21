"""Tests for per-entity authorization of Alexa Media services."""

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.auth.permissions.const import POLICY_CONTROL, POLICY_READ
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import Context
from homeassistant.exceptions import Unauthorized, UnknownUser
import pytest

from custom_components.alexa_media.const import DATA_ALEXAMEDIA, DOMAIN
from custom_components.alexa_media.services import AlexaMediaServices

ENTITY_ID = "media_player.kitchen_echo"
EMAIL = "test@example.com"
SERIAL = "SERIAL"


@pytest.mark.parametrize(
    ("service", "data", "permission", "api_method"),
    [
        ("create_alarm", {"time": "06:30"}, POLICY_CONTROL, "create_alarm"),
        ("list_alarms", {}, POLICY_READ, None),
        ("enable_alarm", {"alarm_id": "idx"}, POLICY_CONTROL, "enable_alarm"),
        ("disable_alarm", {"alarm_id": "idx"}, POLICY_CONTROL, "disable_alarm"),
        ("skip_next_alarm", {"alarm_id": "idx"}, POLICY_CONTROL, "skip_next_alarm"),
        ("delete_alarm", {"alarm_id": "idx"}, POLICY_CONTROL, "delete_notification"),
        ("amazon_kids_enable", {"child": "Alex"}, POLICY_CONTROL, "enable_child_mode"),
        ("amazon_kids_disable", {}, POLICY_CONTROL, "disable_child_mode"),
        ("restore_volume", {}, POLICY_CONTROL, None),
        ("get_history_records", {}, POLICY_CONTROL, "get_customer_history_records"),
    ],
)
@pytest.mark.parametrize(
    "caller", ["denied", "unknown", "read_only", "authorized", "userless"]
)
async def test_service_entity_permissions(
    hass, service, data, permission, api_method, caller
):
    """Exercise registered handlers with both permitted and forbidden contexts."""
    login = MagicMock(email=EMAIL)
    alarm = {
        "notificationIndex": "idx",
        "originalDate": "2026-01-01",
        "originalTime": "06:30:00.000",
        "recurringPattern": "XXXX-WD",
        "status": "ON",
    }
    hass.data[DATA_ALEXAMEDIA] = {
        "accounts": {
            EMAIL: {
                "config_entry": MagicMock(state=ConfigEntryState.LOADED),
                "login_obj": login,
                "notifications": {SERIAL: {"Alarm": {"idx": alarm}}},
            },
        },
    }
    hass.states.async_set(ENTITY_ID, "idle", {"previous_volume": 0.25})
    volume_set = AsyncMock()
    hass.services.async_register("media_player", "volume_set", volume_set)
    await AlexaMediaServices(hass).register()

    context = Context(
        user_id=None if caller == "userless" else "caller", parent_id="parent"
    )
    user = MagicMock()
    user.permissions.check_entity.side_effect = lambda entity_id, policy: (
        entity_id == ENTITY_ID
        and (
            caller == "authorized" or (caller == "read_only" and policy == POLICY_READ)
        )
    )
    denied = caller == "denied" or (
        caller == "read_only" and permission == POLICY_CONTROL
    )

    async def invoke():
        return await hass.services.async_call(
            DOMAIN,
            service,
            {"entity_id": ENTITY_ID, **data},
            blocking=True,
            context=context,
            return_response=service == "list_alarms",
        )

    with (
        patch.object(
            hass.auth,
            "async_get_user",
            return_value=None if caller == "unknown" else user,
        ) as get_user,
        patch("custom_components.alexa_media.services.er.async_get") as registry,
        patch(
            "custom_components.alexa_media.services.AlexaAPI", autospec=True
        ) as amazon,
    ):
        registry.return_value.async_get.return_value = MagicMock(
            platform=DOMAIN, unique_id=SERIAL
        )
        amazon.devices = {EMAIL: [{"serialNumber": SERIAL, "deviceType": "ECHO"}]}
        amazon.get_child_profiles.return_value = [
            {"firstName": "Alex", "directedId": "profile"}
        ]
        amazon.get_customer_history_records.return_value = [
            {
                "deviceSerialNumber": SERIAL,
                "creationTimestamp": 123,
                "description": {"summary": "Test"},
            },
        ]
        if denied or caller == "unknown":
            with pytest.raises(Unauthorized if denied else UnknownUser) as error:
                await invoke()
            assert error.value.context is context
            if denied:
                assert error.value.entity_id == ENTITY_ID
                assert error.value.permission == permission
            registry.assert_not_called()
            assert amazon.mock_calls == []
            volume_set.assert_not_called()
            assert "history_records" not in hass.states.get(ENTITY_ID).attributes
        else:
            response = await invoke()
            registry.return_value.async_get.assert_called_once_with(ENTITY_ID)
            if api_method:
                getattr(amazon, api_method).assert_awaited_once()
            else:
                assert amazon.mock_calls == []
            if service == "list_alarms":
                assert response["count"] == 1
            if service == "get_history_records":
                assert (
                    hass.states.get(ENTITY_ID).attributes["history_records"][0][
                        "summary"
                    ]
                    == "Test"
                )
            if service == "restore_volume":
                volume_set.assert_awaited_once()
                nested_call = volume_set.await_args.args[0]
                assert nested_call.context is context
                assert nested_call.data == {
                    "entity_id": ENTITY_ID,
                    "volume_level": 0.25,
                }

    if caller == "userless":
        get_user.assert_not_awaited()
    else:
        get_user.assert_awaited_once_with(context.user_id)
    if caller in ("userless", "unknown"):
        user.permissions.check_entity.assert_not_called()
    else:
        user.permissions.check_entity.assert_called_once_with(ENTITY_ID, permission)
