"""Tests for the create, enable, disable and delete alarm services."""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from alexapy import AlexaAPI
import pytest
import voluptuous as vol

from custom_components.alexa_media.const import DATA_ALEXAMEDIA
from custom_components.alexa_media.services import (
    CREATE_ALARM_SCHEMA,
    AlexaMediaServices,
    next_alarm_time,
)

EMAIL = "test@example.com"
SERIAL = "G090XXXXXXXXXXXX"
DEVICE_TYPE = "A4ZXE0RM7LQ7A"
ENTITY_ID = "media_player.kitchen_echo"
# A Tuesday.
NOW = datetime.datetime(2026, 10, 20, 7, 0)
ALARM = {
    "id": f"{DEVICE_TYPE}-{SERIAL}-idx-1",
    "notificationIndex": "idx-1",
    "type": "Alarm",
    "originalTime": "06:30:00.000",
    "originalDate": "2026-10-01",
    "recurringPattern": None,
    "status": "OFF",
    "sound": {"id": "system_alerts_melodic_02"},
    "date_time": datetime.datetime(2026, 10, 1, 6, 30),
}


@pytest.fixture(autouse=True)
def frozen_now():
    with patch("custom_components.alexa_media.services.dt_util.now", return_value=NOW):
        yield


def make_services(alarm=ALARM):
    login = MagicMock(email=EMAIL)
    hass = MagicMock()
    hass.data = {
        DATA_ALEXAMEDIA: {
            "accounts": {
                EMAIL: {"notifications": {SERIAL: {"Alarm": {"idx-1": alarm}}}}
            }
        }
    }
    schedule = MagicMock()
    services = AlexaMediaServices(
        hass, functions={"schedule_notifications_refresh": schedule}
    )
    services._resolve_device = MagicMock(return_value=(login, SERIAL, DEVICE_TYPE))
    return services, login, schedule


def call(**data):
    return MagicMock(data={"entity_id": ENTITY_ID, **data})


@pytest.mark.parametrize(
    ("alarm_time", "days", "start", "expected"),
    [
        (datetime.time(7, 30), [], None, "2026-10-20T07:30:00"),
        (datetime.time(6, 30), [], None, "2026-10-21T06:30:00"),
        (datetime.time(7, 0), [], None, "2026-10-21T07:00:00"),
        (datetime.time(6, 30), ["tue"], None, "2026-10-27T06:30:00"),
        (datetime.time(6, 30), ["sat", "sun"], None, "2026-10-24T06:30:00"),
        (datetime.time(6, 30), [], datetime.date(2026, 10, 1), "2026-10-21T06:30:00"),
        (datetime.time(6, 30), [], datetime.date(2026, 10, 30), "2026-10-30T06:30:00"),
    ],
)
def test_next_alarm_time(alarm_time, days, start, expected):
    assert next_alarm_time(alarm_time, days, start) == expected


def test_create_schema():
    data = CREATE_ALARM_SCHEMA({"entity_id": ENTITY_ID, "time": "06:30"})
    assert data["time"] == datetime.time(6, 30)
    assert data["days"] == []
    with pytest.raises(vol.Invalid):
        CREATE_ALARM_SCHEMA(
            {"entity_id": ENTITY_ID, "time": "06:30", "days": ["monday"]}
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("days", "when", "recurrence"),
    [
        ([], "2026-10-21T06:30:00", None),
        (
            ["fri", "mon"],
            "2026-10-23T06:30:00",
            {"freq": "WEEKLY", "byDay": ["MO", "FR"], "interval": 1},
        ),
        (
            ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            "2026-10-21T06:30:00",
            {"freq": "DAILY", "byDay": [], "interval": 1},
        ),
    ],
)
async def test_create_alarm(days, when, recurrence):
    services, login, schedule = make_services()
    with patch.object(AlexaAPI, "create_alarm", AsyncMock(return_value=True)) as create:
        assert await services.create_alarm(call(time=datetime.time(6, 30), days=days))

    create.assert_awaited_once_with(login, SERIAL, DEVICE_TYPE, when, recurrence)
    schedule.assert_called_once_with(
        services.hass, EMAIL, device_serial=SERIAL, reason="create_alarm"
    )


@pytest.mark.asyncio
async def test_create_alarm_failed():
    services, _, schedule = make_services()
    with patch.object(AlexaAPI, "create_alarm", AsyncMock(return_value=False)):
        assert not await services.create_alarm(call(time=datetime.time(6, 30), days=[]))
    schedule.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("changes", "when", "sound_id"),
    [
        ({}, "2026-10-21T06:30:00", "system_alerts_melodic_02"),
        (
            {"originalDate": "2026-10-30"},
            "2026-10-30T06:30:00",
            "system_alerts_melodic_02",
        ),
        (
            {"recurringPattern": "XXXX-WD"},
            "2026-10-21T06:30:00",
            "system_alerts_melodic_02",
        ),
        (
            {"recurringPattern": "XXXX-WE"},
            "2026-10-24T06:30:00",
            "system_alerts_melodic_02",
        ),
        (
            {
                "recurringPattern": "XXXX-WXX-1",
                "rRuleData": {"byWeekDays": ["MO", "WE"]},
            },
            "2026-10-21T06:30:00",
            "system_alerts_melodic_02",
        ),
        ({"musicAlarmId": "music-1"}, "2026-10-21T06:30:00", "MUSIC-music-1"),
    ],
)
async def test_enable_alarm(changes, when, sound_id):
    services, login, schedule = make_services({**ALARM, **changes})
    with patch.object(AlexaAPI, "enable_alarm", AsyncMock(return_value=True)) as enable:
        assert await services.enable_alarm(call(alarm_id="idx-1"))

    enable.assert_awaited_once_with(login, "idx-1", when, sound_id)
    schedule.assert_called_once_with(
        services.hass, EMAIL, device_serial=SERIAL, reason="enable_alarm"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("missing", ["originalTime", "originalDate"])
async def test_enable_alarm_without_time(missing):
    alarm = {k: v for k, v in ALARM.items() if k != missing}
    services, _, schedule = make_services(alarm)
    with patch.object(AlexaAPI, "enable_alarm", AsyncMock()) as enable:
        assert not await services.enable_alarm(call(alarm_id="idx-1"))
    enable.assert_not_awaited()
    schedule.assert_not_called()


@pytest.mark.asyncio
async def test_disable_alarm_by_id():
    services, login, schedule = make_services()
    with patch.object(
        AlexaAPI, "disable_alarm", AsyncMock(return_value=True)
    ) as disable:
        assert await services.disable_alarm(call(alarm_id=ALARM["id"]))

    disable.assert_awaited_once_with(login, "idx-1")
    schedule.assert_called_once()


@pytest.mark.asyncio
async def test_delete_alarm_drops_date_time():
    services, login, schedule = make_services()
    with patch.object(
        AlexaAPI, "delete_notification", AsyncMock(return_value=True)
    ) as delete:
        assert await services.delete_alarm(call(alarm_id="idx-1"))

    sent = delete.call_args.args[1]
    assert delete.call_args.args[0] is login
    assert "date_time" not in sent
    assert sent["id"] == ALARM["id"]
    schedule.assert_called_once_with(
        services.hass, EMAIL, device_serial=SERIAL, reason="delete_alarm"
    )


@pytest.mark.asyncio
async def test_delete_alarm_failed():
    services, _, schedule = make_services()
    with patch.object(AlexaAPI, "delete_notification", AsyncMock(return_value=False)):
        assert not await services.delete_alarm(call(alarm_id="idx-1"))
    schedule.assert_not_called()


@pytest.mark.asyncio
async def test_unknown_alarm():
    services, _, schedule = make_services()
    with patch.object(AlexaAPI, "disable_alarm", AsyncMock()) as disable:
        assert not await services.disable_alarm(call(alarm_id="missing"))
    disable.assert_not_awaited()
    schedule.assert_not_called()


@pytest.mark.asyncio
async def test_unknown_device():
    services, _, _ = make_services()
    services._resolve_device.return_value = (None, None, None)
    with patch.object(AlexaAPI, "create_alarm", AsyncMock()) as create:
        assert not await services.create_alarm(call(time=datetime.time(6, 30), days=[]))
    create.assert_not_awaited()
