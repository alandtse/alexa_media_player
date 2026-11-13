"""Tests for the create, enable, disable and delete alarm services."""

import datetime
import json
from unittest.mock import AsyncMock, MagicMock, patch

from alexapy import AlexaAPI, AlexapyLoginError
from alexapy.errors import AlexapyConnectionError, AlexapyTooManyRequestsError
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.util import dt as dt_util
import pytest
import voluptuous as vol

from custom_components.alexa_media.const import DATA_ALEXAMEDIA
from custom_components.alexa_media.services import (
    CREATE_ALARM_SCHEMA,
    AlexaMediaServices,
    next_alarm_time,
    resolve_alarm_schedule,
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


RECURRING_ALARM = {
    **ALARM,
    "deviceSerialNumber": SERIAL,
    "deviceType": DEVICE_TYPE,
    "alarmLabel": "Weekday test alarm",
    "originalDate": "2026-10-21",
    "date_time": datetime.datetime(2026, 10, 21, 6, 30),
    "recurringPattern": "XXXX-WD",
    "status": "ON",
}


@pytest.mark.asyncio
@pytest.mark.parametrize("alarm_id", [RECURRING_ALARM["id"], "idx-1"])
async def test_skip_next_alarm_registered(alarm_id):
    """Verify both alarm ID formats through the registered service."""
    services, login, schedule = make_services(RECURRING_ALARM.copy())
    del services._resolve_device
    services.hass.data[DATA_ALEXAMEDIA]["accounts"][EMAIL]["login_obj"] = login
    await services.register()
    registered = {
        args[1]: (args[2], kwargs["schema"])
        for args, kwargs in services.hass.services.async_register.call_args_list
    }
    handler, schema = registered["skip_next_alarm"]
    with (
        patch("custom_components.alexa_media.services.er.async_get") as registry,
        patch.object(
            AlexaAPI,
            "devices",
            {EMAIL: [{"serialNumber": SERIAL, "deviceType": DEVICE_TYPE}]},
        ),
        patch.object(
            AlexaAPI, "skip_next_alarm", autospec=True, return_value=True
        ) as skip,
    ):
        registry.return_value.async_get.return_value = MagicMock(
            platform="alexa_media", unique_id=SERIAL
        )
        assert await handler(MagicMock(data=schema(call(alarm_id=alarm_id).data)))

    registry.return_value.async_get.assert_called_once_with(ENTITY_ID)
    skip.assert_awaited_once_with(login, "idx-1")
    schedule.assert_called_once_with(
        services.hass, EMAIL, device_serial=SERIAL, reason="skip_next_alarm"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("changes", "alarm_id"),
    [
        ({"recurringPattern": None}, "idx-1"),
        ({"status": "OFF"}, "idx-1"),
        ({"notificationIndex": None}, "idx-1"),
        ({}, f"{DEVICE_TYPE}-OTHER-SERIAL-idx-1"),
    ],
)
async def test_skip_next_alarm_rejects_invalid_target(changes, alarm_id):
    """Reject invalid alarm targets before calling Alexa or refreshing notifications."""
    services, _, schedule = make_services({**RECURRING_ALARM, **changes})
    with (
        patch.object(AlexaAPI, "skip_next_alarm", autospec=True) as skip,
        pytest.raises(ServiceValidationError),
    ):
        await services.skip_next_alarm(call(alarm_id=alarm_id))
    skip.assert_not_called()
    schedule.assert_not_called()


@pytest.mark.asyncio
async def test_skip_next_alarm_refused():
    """Report a refused skip without scheduling a notification refresh."""
    services, _, schedule = make_services(RECURRING_ALARM.copy())
    with (
        patch.object(AlexaAPI, "skip_next_alarm", autospec=True, return_value=False),
        pytest.raises(HomeAssistantError),
    ):
        await services.skip_next_alarm(call(alarm_id="idx-1"))
    schedule.assert_not_called()


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
    with patch.object(
        AlexaAPI, "create_alarm", autospec=True, return_value=True
    ) as create:
        assert await services.create_alarm(call(time=datetime.time(6, 30), days=days))

    create.assert_awaited_once_with(login, SERIAL, DEVICE_TYPE, when, recurrence, None)
    schedule.assert_called_once_with(
        services.hass, EMAIL, device_serial=SERIAL, reason="create_alarm"
    )


@pytest.mark.asyncio
async def test_create_alarm_failed():
    services, _, schedule = make_services()
    with (
        patch.object(AlexaAPI, "create_alarm", autospec=True, return_value=False),
        pytest.raises(HomeAssistantError),
    ):
        await services.create_alarm(call(time=datetime.time(6, 30), days=[]))
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
    with patch.object(
        AlexaAPI, "enable_alarm", autospec=True, return_value=True
    ) as enable:
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
    with (
        patch.object(AlexaAPI, "enable_alarm", autospec=True) as enable,
        pytest.raises(ServiceValidationError),
    ):
        await services.enable_alarm(call(alarm_id="idx-1"))
    enable.assert_not_awaited()
    schedule.assert_not_called()


@pytest.mark.asyncio
async def test_enable_alarm_unknown_repeat():
    services, _, schedule = make_services({**ALARM, "recurringPattern": "P1M"})
    with (
        patch.object(AlexaAPI, "enable_alarm", autospec=True) as enable,
        pytest.raises(ServiceValidationError),
    ):
        await services.enable_alarm(call(alarm_id="idx-1"))
    enable.assert_not_awaited()
    schedule.assert_not_called()


@pytest.mark.asyncio
async def test_disable_alarm_by_id():
    services, login, schedule = make_services()
    with patch.object(
        AlexaAPI, "disable_alarm", autospec=True, return_value=True
    ) as disable:
        assert await services.disable_alarm(call(alarm_id=ALARM["id"]))

    disable.assert_awaited_once_with(login, "idx-1")
    schedule.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "date_time", [datetime.datetime(2026, 10, 1, 6, 30), "2026-10-01 06:30:00.000"]
)
async def test_delete_alarm_drops_date_time(date_time):
    services, login, schedule = make_services({**ALARM, "date_time": date_time})
    with patch.object(
        AlexaAPI, "delete_notification", autospec=True, return_value=True
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
async def test_delete_snoozed_alarm():
    """A snoozed alarm's snoozedToTime is a datetime once the sensor has seen it."""
    snoozed = {
        **ALARM,
        "status": "SNOOZED",
        "snoozedToTime": datetime.datetime(2026, 10, 20, 7, 9),
    }
    services, _, _ = make_services(snoozed)
    with patch.object(
        AlexaAPI, "delete_notification", autospec=True, return_value=True
    ) as delete:
        assert await services.delete_alarm(call(alarm_id="idx-1"))

    sent = delete.call_args.args[1]
    assert "snoozedToTime" not in sent
    json.dumps(sent)


@pytest.mark.asyncio
async def test_create_alarm_uses_echo_time_zone():
    """The next ring is worked out in the Echo's time zone, not HA's."""
    services, login, _ = make_services()
    services.hass.data[DATA_ALEXAMEDIA]["accounts"][EMAIL]["devices"] = {
        "media_player": {SERIAL: {"timeZoneId": "Asia/Tokyo"}}
    }
    tokyo = dt_util.get_time_zone("Asia/Tokyo")
    # 07:00 for HA, but already 16:00 on the Echo
    with (
        patch(
            "custom_components.alexa_media.services.dt_util.now",
            side_effect=lambda tz=None: (
                NOW + datetime.timedelta(hours=9) if tz is tokyo else NOW
            ),
        ),
        patch.object(
            AlexaAPI, "create_alarm", autospec=True, return_value=True
        ) as create,
    ):
        await services.create_alarm(call(time=datetime.time(8, 0), days=[]))

    assert create.call_args.args[3] == "2026-10-21T08:00:00"


@pytest.mark.asyncio
async def test_delete_alarm_failed():
    services, _, schedule = make_services()
    with (
        patch.object(
            AlexaAPI, "delete_notification", autospec=True, return_value=False
        ),
        pytest.raises(HomeAssistantError),
    ):
        await services.delete_alarm(call(alarm_id="idx-1"))
    schedule.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("logged_in", [True, False])
async def test_alarm_login_error(logged_in):
    services, login, schedule = make_services()
    login.test_loggedin = AsyncMock(return_value=logged_in)
    with (
        patch.object(
            AlexaAPI, "disable_alarm", autospec=True, side_effect=AlexapyLoginError
        ),
        patch(
            "custom_components.alexa_media.services.report_relogin_required"
        ) as relogin,
        pytest.raises(HomeAssistantError),
    ):
        await services.disable_alarm(call(alarm_id="idx-1"))
    assert relogin.called is not logged_in
    schedule.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error", [AlexapyConnectionError, AlexapyTooManyRequestsError, TimeoutError]
)
async def test_alarm_amazon_unreachable(error):
    services, _, schedule = make_services()
    with (
        patch.object(AlexaAPI, "create_alarm", autospec=True, side_effect=error),
        pytest.raises(HomeAssistantError),
    ):
        await services.create_alarm(call(time=datetime.time(7, 0), days=[]))
    schedule.assert_not_called()


@pytest.mark.asyncio
async def test_unknown_alarm():
    services, _, schedule = make_services()
    with (
        patch.object(AlexaAPI, "disable_alarm", autospec=True) as disable,
        pytest.raises(ServiceValidationError),
    ):
        await services.disable_alarm(call(alarm_id="missing"))
    disable.assert_not_awaited()
    schedule.assert_not_called()


@pytest.mark.asyncio
async def test_unknown_device():
    services, _, _ = make_services()
    services._resolve_device.return_value = (None, None, None)
    with (
        patch.object(AlexaAPI, "create_alarm", autospec=True) as create,
        pytest.raises(ServiceValidationError),
    ):
        await services.create_alarm(call(time=datetime.time(6, 30), days=[]))
    create.assert_not_awaited()


@pytest.mark.parametrize("preset", ["today", "tomorrow"])
def test_date_presets_require_echo_timezone(preset):
    """Do not substitute HA's timezone when Echo timezone is unknown."""
    from custom_components.alexa_media.services import resolve_alarm_schedule

    with pytest.raises(ServiceValidationError, match="Echo's timezone is unavailable"):
        resolve_alarm_schedule(datetime.time(8, 0), [preset], None)


MUSIC_ID = "11111111-1111-4111-8111-111111111111"


@pytest.mark.parametrize(
    ("days", "expected_time", "repeat"),
    [
        (["today"], "2026-10-20T08:00:00", None),
        (["tomorrow"], "2026-10-21T08:00:00", None),
        (
            ["weekdays"],
            "2026-10-20T08:00:00",
            {"freq": "WEEKLY", "byDay": ["MO", "TU", "WE", "TH", "FR"], "interval": 1},
        ),
        (
            ["weekends"],
            "2026-10-24T08:00:00",
            {"freq": "WEEKLY", "byDay": ["SA", "SU"], "interval": 1},
        ),
        (
            ["everyday"],
            "2026-10-20T08:00:00",
            {"freq": "DAILY", "byDay": [], "interval": 1},
        ),
    ],
)
def test_alarm_schedule_presets(days, expected_time, repeat):
    zone = dt_util.get_time_zone("Europe/London")
    assert resolve_alarm_schedule(datetime.time(8, 0), days, zone) == (
        expected_time,
        repeat,
    )


def test_alarm_schedule_expired_today():
    """Only today's alarm time can already have passed."""
    zone = dt_util.get_time_zone("Europe/London")
    with pytest.raises(ServiceValidationError, match="already passed"):
        resolve_alarm_schedule(datetime.time(6, 0), ["today"], zone)


@pytest.mark.parametrize(
    "days",
    [
        ["today", "mon"],
        ["tomorrow", "weekdays"],
        ["weekdays", "weekends"],
    ],
)
def test_alarm_schedule_rejects_mixed_presets(days):
    with pytest.raises(ServiceValidationError, match="do not combine"):
        resolve_alarm_schedule(
            datetime.time(8, 0), days, dt_util.get_time_zone("Europe/London")
        )


@pytest.mark.parametrize(
    ("now", "alarm_time", "days", "message"),
    [
        (
            datetime.datetime(2026, 3, 28, 12),
            datetime.time(1, 30),
            ["tomorrow"],
            "does not exist",
        ),
        (
            datetime.datetime(2026, 10, 24, 12),
            datetime.time(1, 30),
            ["tomorrow"],
            "ambiguous",
        ),
    ],
)
def test_one_off_alarm_rejects_dst_gap_fold(now, alarm_time, days, message):
    zone = dt_util.get_time_zone("Europe/London")
    with patch("custom_components.alexa_media.services.dt_util.now", return_value=now):
        with pytest.raises(ServiceValidationError, match=message):
            resolve_alarm_schedule(alarm_time, days, zone)


@pytest.mark.asyncio
async def test_music_alarm_created_from_current_alexa_cache():
    music_alarm = {
        **ALARM,
        "provider": "Amazon Music",
        "musicEntity": "Enya",
        "musicAlarmId": MUSIC_ID,
    }
    services, login, schedule = make_services(music_alarm)
    with patch.object(
        AlexaAPI, "create_alarm", autospec=True, return_value=True
    ) as create:
        assert await services.create_alarm(
            call(
                time=datetime.time(8, 0),
                days=[],
                alarm_type="music",
                music_provider="Amazon Music",
                music_entity="enya",
            )
        )
    create.assert_awaited_once_with(
        login, SERIAL, DEVICE_TYPE, "2026-10-20T08:00:00", None, f"MUSIC-{MUSIC_ID}"
    )
    schedule.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_id", [123, {"uuid": MUSIC_ID}, "not-a-uuid", None])
async def test_music_alarm_invalid_cached_ids_never_create_alarm(bad_id):
    services, _, schedule = make_services(
        {
            **ALARM,
            "provider": "Amazon Music",
            "musicEntity": "Enya",
            "musicAlarmId": bad_id,
        }
    )
    with (
        patch.object(AlexaAPI, "create_alarm", autospec=True) as create,
        pytest.raises(ServiceValidationError, match="No cached Alexa music alarm"),
    ):
        await services.create_alarm(
            call(
                time=datetime.time(8, 0),
                days=[],
                alarm_type="music",
                music_provider="Amazon Music",
                music_entity="Enya",
            )
        )
    create.assert_not_called()
    schedule.assert_not_called()


@pytest.mark.asyncio
async def test_music_alarm_not_persisted_across_notification_removal():
    services, login, schedule = make_services(
        {
            **ALARM,
            "provider": "Amazon Music",
            "musicEntity": "Enya",
            "musicAlarmId": MUSIC_ID,
        }
    )
    assert (
        services._cached_music_assets(login)[
            services._music_key("Amazon Music", "Enya")
        ]
        == MUSIC_ID
    )
    services.hass.data[DATA_ALEXAMEDIA]["accounts"][EMAIL]["notifications"][SERIAL][
        "Alarm"
    ] = {}
    with (
        patch.object(AlexaAPI, "create_alarm", autospec=True) as create,
        pytest.raises(ServiceValidationError, match="No cached Alexa music alarm"),
    ):
        await services.create_alarm(
            call(
                time=datetime.time(8, 0),
                days=[],
                alarm_type="music",
                music_provider="Amazon Music",
                music_entity="Enya",
            )
        )
    create.assert_not_called()
    schedule.assert_not_called()


@pytest.mark.asyncio
async def test_list_alarms_returns_music_without_ids():
    alarm = {
        **ALARM,
        "provider": "Amazon Music",
        "musicEntity": "Enya",
        "musicAlarmId": MUSIC_ID,
    }
    services, _, _ = make_services(alarm)
    result = await services.list_alarms(call())
    assert result["count"] == 1
    assert result["alarms"][0]["music_entity"] == "Enya"
    assert result["alarms"][0]["is_music"] is True
    assert MUSIC_ID not in str(result)


@pytest.mark.asyncio
async def test_no_music_arguments_on_normal_alarm():
    services, _, _ = make_services()
    with (
        patch.object(AlexaAPI, "create_alarm", autospec=True) as create,
        pytest.raises(ServiceValidationError, match="Music parameters require"),
    ):
        await services.create_alarm(
            call(
                time=datetime.time(8, 0),
                days=[],
                music_entity="Enya",
                music_provider="Amazon Music",
            )
        )
    create.assert_not_called()


def test_next_alarm_time_rejects_dst_transition_gap_and_fold():
    """Non-date-preset alarms must not silently select invalid local times."""
    zone = dt_util.get_time_zone("Europe/London")
    for now, error in [
        (datetime.datetime(2026, 3, 28, 12), "does not exist"),
        (datetime.datetime(2026, 10, 24, 12), "ambiguous"),
    ]:
        with (
            patch(
                "custom_components.alexa_media.services.dt_util.now",
                return_value=now,
            ),
            pytest.raises(ServiceValidationError, match=error),
        ):
            next_alarm_time(datetime.time(1, 30), [], time_zone=zone)


@pytest.mark.parametrize(
    ("now", "days", "expected", "recurrence"),
    [
        (
            datetime.datetime(2026, 3, 28, 12),
            ["everyday"],
            "2026-03-30T01:30:00",
            {"freq": "DAILY", "byDay": [], "interval": 1},
        ),
        (
            datetime.datetime(2026, 3, 28, 12),
            ["weekends"],
            "2026-04-04T01:30:00",
            {"freq": "WEEKLY", "byDay": ["SA", "SU"], "interval": 1},
        ),
        (
            datetime.datetime(2026, 10, 24, 12),
            ["everyday"],
            "2026-10-26T01:30:00",
            {"freq": "DAILY", "byDay": [], "interval": 1},
        ),
        (
            datetime.datetime(2026, 10, 24, 12),
            ["sun"],
            "2026-11-01T01:30:00",
            {"freq": "WEEKLY", "byDay": ["SU"], "interval": 1},
        ),
    ],
)
def test_recurring_alarms_skip_initial_dst_gap_or_fold(now, days, expected, recurrence):
    """Keep the repeat rule while skipping an invalid first local occurrence."""
    zone = dt_util.get_time_zone("Europe/London")
    with patch("custom_components.alexa_media.services.dt_util.now", return_value=now):
        assert resolve_alarm_schedule(datetime.time(1, 30), days, zone) == (
            expected,
            recurrence,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("now", "days", "expected"),
    [
        (datetime.datetime(2026, 3, 28, 12), ["everyday"], "2026-03-30T01:30:00"),
        (datetime.datetime(2026, 10, 24, 12), ["everyday"], "2026-10-26T01:30:00"),
    ],
)
async def test_create_recurring_alarm_across_dst_transition(now, days, expected):
    """DST transition must not prevent submitting a recurring alarm to Alexa."""
    services, login, schedule = make_services()
    zone = dt_util.get_time_zone("Europe/London")
    with (
        patch.object(
            services, "_resolve_alarm_device", return_value=(login, SERIAL, DEVICE_TYPE, zone)
        ),
        patch("custom_components.alexa_media.services.dt_util.now", return_value=now),
        patch.object(
            AlexaAPI, "create_alarm", autospec=True, return_value=True
        ) as create,
    ):
        assert await services.create_alarm(call(time=datetime.time(1, 30), days=days))
    create.assert_awaited_once_with(
        login,
        SERIAL,
        DEVICE_TYPE,
        expected,
        {"freq": "DAILY", "byDay": [], "interval": 1},
        None,
    )
    schedule.assert_called_once()


@pytest.mark.asyncio
async def test_music_selection_is_isolated_between_alexa_accounts():
    """An alarm ID from one Alexa account must not be reused for another."""
    services, _, schedule = make_services(
        {
            **ALARM,
            "musicAlarmId": MUSIC_ID,
            "musicEntity": "Enya",
            "provider": "Amazon Music",
        }
    )
    other_email = "another@example.com"
    other_login = MagicMock(email=other_email)
    services.hass.data[DATA_ALEXAMEDIA]["accounts"][other_email] = {
        "notifications": {SERIAL: {"Alarm": {}}}
    }
    services._resolve_device.return_value = (other_login, SERIAL, DEVICE_TYPE)
    with (
        patch.object(AlexaAPI, "create_alarm", autospec=True) as create,
        pytest.raises(ServiceValidationError, match="No cached Alexa music alarm"),
    ):
        await services.create_alarm(
            call(
                time=datetime.time(8, 0),
                days=[],
                alarm_type="music",
                music_provider="Amazon Music",
                music_entity="Enya",
            )
        )
    create.assert_not_called()
    schedule.assert_not_called()


@pytest.mark.asyncio
async def test_music_alarm_required_arguments():
    services, _, _ = make_services()
    with (
        patch.object(AlexaAPI, "create_alarm", autospec=True) as create,
        pytest.raises(ServiceValidationError, match="both music_provider"),
    ):
        await services.create_alarm(
            call(
                time=datetime.time(8, 0),
                days=[],
                alarm_type="music",
                music_entity="Enya",
            )
        )
    create.assert_not_called()


@pytest.mark.asyncio
async def test_music_cache_ignores_corrupted_notification_entries():
    """Malformed cache records should never generate or persist an identifier."""
    services, login, _ = make_services()
    services.hass.data[DATA_ALEXAMEDIA]["accounts"][EMAIL]["notifications"] = {
        SERIAL: {
            "Alarm": {
                "bad-shape": ["not", "an", "alarm"],
                "bad-id": {
                    "provider": "Amazon Music",
                    "musicEntity": "Enya",
                    "musicAlarmId": {"invalid": MUSIC_ID},
                },
                "valid": {
                    "provider": "Amazon Music",
                    "musicEntity": "Enya",
                    "musicAlarmId": MUSIC_ID,
                },
            }
        },
        "another-device": {"Alarm": "invalid"},
    }
    result = services._cached_music_assets(login)
    assert result == {services._music_key("Amazon Music", "Enya"): MUSIC_ID}
