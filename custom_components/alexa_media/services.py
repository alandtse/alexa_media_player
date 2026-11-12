"""
Alexa Services.

SPDX-License-Identifier: Apache-2.0

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""

import asyncio
from dataclasses import dataclass
import datetime
import logging
from typing import Any, Callable

from alexapy import AlexaAPI, AlexapyLoginError, hide_email
from alexapy.errors import AlexapyConnectionError, AlexapyTooManyRequestsError
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv, entity_registry as er
from homeassistant.util import dt as dt_util, slugify
import voluptuous as vol

from .const import (
    ATTR_ALARM_ID,
    ATTR_CHILD,
    ATTR_DAYS,
    ATTR_EMAIL,
    ATTR_ENTITY_ID,
    ATTR_NUM_ENTRIES,
    ATTR_TIME,
    DATA_ALEXAMEDIA,
    DOMAIN,
    RECURRING_PATTERN_ISO_SET,
    SERVICE_AMAZON_KIDS_DISABLE,
    SERVICE_AMAZON_KIDS_ENABLE,
    SERVICE_CREATE_ALARM,
    SERVICE_DELETE_ALARM,
    SERVICE_DISABLE_ALARM,
    SERVICE_ENABLE_ALARM,
    SERVICE_ENABLE_NETWORK_DISCOVERY,
    SERVICE_FORCE_LOGOUT,
    SERVICE_GET_HISTORY_RECORDS,
    SERVICE_RESTORE_VOLUME,
    SERVICE_SKIP_NEXT_ALARM,
    SERVICE_UPDATE_LAST_CALLED,
)
from .helpers import _catch_login_errors, report_relogin_required, safe_get

_LOGGER = logging.getLogger(__name__)


FORCE_LOGOUT_SCHEMA = vol.Schema(
    {vol.Optional(ATTR_EMAIL, default=[]): vol.All(cv.ensure_list, [cv.string])}
)
LAST_CALL_UPDATE_SCHEMA = vol.Schema(
    {vol.Optional(ATTR_EMAIL, default=[]): vol.All(cv.ensure_list, [cv.string])}
)
RESTORE_VOLUME_SCHEMA = vol.Schema({vol.Required(ATTR_ENTITY_ID): cv.entity_id})

GET_HISTORY_RECORDS_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_id,
        vol.Optional(ATTR_NUM_ENTRIES, default=5): cv.positive_int,
    }
)

ENABLE_NETWORK_DISCOVERY_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_EMAIL, default=[]): vol.All(
            cv.ensure_list,
            [cv.string],
        ),
    }
)

AMAZON_KIDS_ENABLE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_id,
        vol.Required(ATTR_CHILD): cv.string,
    }
)
AMAZON_KIDS_DISABLE_SCHEMA = vol.Schema({vol.Required(ATTR_ENTITY_ID): cv.entity_id})

ALARM_DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
ALARM_DAY_PRESETS = {
    "weekdays": ("mon", "tue", "wed", "thu", "fri"),
    "weekends": ("sat", "sun"),
    "everyday": ALARM_DAYS,
}
ALARM_DATE_PRESETS = ("today", "tomorrow")
ALARM_DAY_OPTIONS = (*ALARM_DAYS, *ALARM_DAY_PRESETS, *ALARM_DATE_PRESETS)
MUSIC_ALARM_TYPES = ("default", "music")
LIST_ALARMS_SCHEMA = vol.Schema({vol.Required(ATTR_ENTITY_ID): cv.entity_id})

CREATE_ALARM_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_id,
        vol.Required(ATTR_TIME): cv.time,
        vol.Optional(ATTR_DAYS, default=[]): vol.All(
            cv.ensure_list, [vol.In(ALARM_DAY_OPTIONS)]
        ),
        vol.Optional("alarm_type", default="default"): vol.In(MUSIC_ALARM_TYPES),
        vol.Optional("music_provider"): cv.string,
        vol.Optional("music_entity"): cv.string,
    }
)
ALARM_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_id,
        vol.Required(ATTR_ALARM_ID): cv.string,
    }
)


def alarm_days(alarm: dict[str, Any]) -> list[str]:
    """Return the days an alarm repeats on, empty if it doesn't repeat."""
    # recurringPattern only names the first day when an alarm repeats on a few.
    week_days = safe_get(alarm, ["rRuleData", "byWeekDays"])
    if week_days:
        return [day for day in ALARM_DAYS if day[:2].upper() in week_days]
    iso_days = RECURRING_PATTERN_ISO_SET.get(alarm.get("recurringPattern")) or ()
    return [day for iso, day in enumerate(ALARM_DAYS, 1) if iso in iso_days]


def _validate_local_alarm_time(
    when: datetime.datetime, time_zone: datetime.tzinfo | None
) -> None:
    """Reject nonexistent and ambiguous Echo-local DST times.

    Alexa's alarm API receives local timestamps without an offset or fold.
    Explicitly reject times we cannot represent unambiguously.
    """
    if time_zone is None:
        return
    valid_offsets = set()
    for fold in (0, 1):
        aware = when.replace(tzinfo=time_zone, fold=fold)
        round_trip = aware.astimezone(datetime.timezone.utc).astimezone(time_zone)
        if round_trip.replace(tzinfo=None) == when:
            valid_offsets.add(aware.utcoffset())
    if not valid_offsets:
        raise ServiceValidationError(
            "Alarm time does not exist in the Echo's timezone (DST transition)"
        )
    if len(valid_offsets) > 1:
        raise ServiceValidationError(
            "Alarm time is ambiguous in the Echo's timezone (DST transition)"
        )


def resolve_alarm_schedule(
    alarm_time: datetime.time,
    requested_days: list[str],
    time_zone: datetime.tzinfo | None,
) -> tuple[str, dict[str, Any] | None]:
    """Resolve days/presets to an Alexa-local alarm time and repeat rule."""
    presets = set(ALARM_DAY_PRESETS) | set(ALARM_DATE_PRESETS)
    selected = set(requested_days)
    if selected & presets:
        if len(requested_days) != 1:
            raise ServiceValidationError(
                "Use today, tomorrow, weekdays, weekends or everyday alone; "
                "do not combine a preset with other days"
            )
        preset = requested_days[0]
        if preset in ALARM_DAY_PRESETS:
            days = list(ALARM_DAY_PRESETS[preset])
            return next_alarm_time(
                alarm_time, days, time_zone=time_zone
            ), alarm_recurrence(days)

        # One-off dates require the Echo's own timezone, not HA's fallback.
        if time_zone is None:
            raise ServiceValidationError(
                "The Echo's timezone is unavailable; cannot schedule today or tomorrow. "
                "Check the Echo's timezone settings or use a recurring schedule."
            )
        now = dt_util.now(time_zone).replace(tzinfo=None)
        date = now.date() + datetime.timedelta(days=1 if preset == "tomorrow" else 0)
        when = datetime.datetime.combine(date, alarm_time)
        _validate_local_alarm_time(when, time_zone)
        if when <= now:
            raise ServiceValidationError(
                f"The requested time for {preset} has already passed in the Echo's local timezone"
            )
        return when.isoformat(timespec="seconds"), None

    # Preserve v1.3.1 behaviour for empty days and individual weekdays.
    return (
        next_alarm_time(alarm_time, requested_days, time_zone=time_zone),
        alarm_recurrence(requested_days),
    )


def alarm_recurrence(days: list[str]) -> dict[str, Any] | None:
    """Return the alarms API repeat rule for days, None for a one-off."""
    if set(days) == set(ALARM_DAYS):
        return {"freq": "DAILY", "byDay": [], "interval": 1}
    if days:
        by_day = [day[:2].upper() for day in ALARM_DAYS if day in days]
        return {"freq": "WEEKLY", "byDay": by_day, "interval": 1}
    return None


def alarm_sound(alarm: dict[str, Any]) -> str | None:
    """Return the tone id to send back when changing an alarm."""
    if alarm.get("musicAlarmId"):
        return f"MUSIC-{alarm['musicAlarmId']}"
    return safe_get(alarm, ["sound", "id"])


def next_alarm_time(
    alarm_time: datetime.time,
    days: list[str],
    start: datetime.date | None = None,
    time_zone: datetime.tzinfo | None = None,
) -> str:
    """Return the next ring on one of days (any day if empty), not before start.

    Amazon reads the time in the Echo's own time zone, so pass that if known.
    """
    now = dt_util.now(time_zone).replace(tzinfo=None)
    when = datetime.datetime.combine(max(start or now.date(), now.date()), alarm_time)
    while when <= now or (days and ALARM_DAYS[when.weekday()] not in days):
        when += datetime.timedelta(days=1)
    _validate_local_alarm_time(when, time_zone)
    return when.isoformat(timespec="seconds")


@dataclass(frozen=True)
class AlexaServiceDef:
    """Definition for an Alexa Media custom service."""

    name: str  # service name as exposed in HA: alexa_media.<name>
    schema: vol.Schema  # voluptuous schema
    handler: str  # method name on AlexaMediaServices


SERVICE_DEFS: tuple[AlexaServiceDef, ...] = (
    AlexaServiceDef(
        name=SERVICE_FORCE_LOGOUT,
        schema=FORCE_LOGOUT_SCHEMA,
        handler="force_logout",
    ),
    AlexaServiceDef(
        name=SERVICE_UPDATE_LAST_CALLED,
        schema=LAST_CALL_UPDATE_SCHEMA,
        handler="last_call_handler",
    ),
    AlexaServiceDef(
        name=SERVICE_RESTORE_VOLUME,
        schema=RESTORE_VOLUME_SCHEMA,
        handler="restore_volume",
    ),
    AlexaServiceDef(
        name=SERVICE_GET_HISTORY_RECORDS,
        schema=GET_HISTORY_RECORDS_SCHEMA,
        handler="get_history_records",
    ),
    AlexaServiceDef(
        name=SERVICE_ENABLE_NETWORK_DISCOVERY,
        schema=ENABLE_NETWORK_DISCOVERY_SCHEMA,
        handler="enable_network_discovery",
    ),
    AlexaServiceDef(
        name=SERVICE_AMAZON_KIDS_ENABLE,
        schema=AMAZON_KIDS_ENABLE_SCHEMA,
        handler="amazon_kids_enable",
    ),
    AlexaServiceDef(
        name=SERVICE_AMAZON_KIDS_DISABLE,
        schema=AMAZON_KIDS_DISABLE_SCHEMA,
        handler="amazon_kids_disable",
    ),
    AlexaServiceDef(
        name=SERVICE_CREATE_ALARM,
        schema=CREATE_ALARM_SCHEMA,
        handler="create_alarm",
    ),
    AlexaServiceDef(
        name="list_alarms",
        schema=LIST_ALARMS_SCHEMA,
        handler="list_alarms",
    ),
    AlexaServiceDef(
        name=SERVICE_ENABLE_ALARM,
        schema=ALARM_SCHEMA,
        handler="enable_alarm",
    ),
    AlexaServiceDef(
        name=SERVICE_DISABLE_ALARM,
        schema=ALARM_SCHEMA,
        handler="disable_alarm",
    ),
    AlexaServiceDef(
        name=SERVICE_DELETE_ALARM,
        schema=ALARM_SCHEMA,
        handler="delete_alarm",
    ),
    AlexaServiceDef(
        name=SERVICE_SKIP_NEXT_ALARM,
        schema=ALARM_SCHEMA,
        handler="skip_next_alarm",
    ),
)


class AlexaMediaServices:
    def __init__(self, hass: HomeAssistant, functions: dict[str, Callable[..., Any]]):
        self.hass = hass
        self._functions = functions

    async def register(self) -> None:
        """Register Alexa Media custom services."""
        for service_def in SERVICE_DEFS:
            handler = getattr(self, service_def.handler)
            self.hass.services.async_register(
                DOMAIN,
                service_def.name,
                handler,
                schema=service_def.schema,
                supports_response=(
                    SupportsResponse.ONLY
                    if service_def.name == "list_alarms"
                    else SupportsResponse.NONE
                ),
            )

    async def unregister(self) -> None:
        """Unregister Alexa Media custom services."""
        for service_def in SERVICE_DEFS:
            self.hass.services.async_remove(DOMAIN, service_def.name)

    async def force_logout(self, call: ServiceCall) -> bool:
        """Handle force logout service request.

        Arguments
            call.ATTR_EMAIL {List[str] | None}: List of case-sensitive Alexa emails.
                                                If None, all accounts are logged out.

        Returns
            bool -- True if at least one account was marked for relogin.
        """
        requested_emails = call.data.get(ATTR_EMAIL)
        _LOGGER.debug("Service force_logout called for: %s", requested_emails)

        accounts = self.hass.data[DATA_ALEXAMEDIA]["accounts"]
        success = False

        for email, account_dict in accounts.items():
            if requested_emails and email not in requested_emails:
                continue

            login_obj = account_dict["login_obj"]

            # This is the effective “force logout” for this account: mark it as
            # requiring reauthentication and notify the user/UI.
            report_relogin_required(self.hass, login_obj, email)
            success = True
            _LOGGER.debug(
                "Marked Alexa Media account %s for relogin via force_logout service",
                hide_email(email),
            )

        if requested_emails and not success:
            _LOGGER.warning(
                "force_logout called for %s but no matching Alexa Media accounts were found",
                requested_emails,
            )

        return success

    @_catch_login_errors
    async def last_call_handler(self, call: ServiceCall) -> None:
        """Handle last call service request.

        Arguments
            call.ATTR_EMAIL: {List[str: None]}: List of case-sensitive Alexa emails.
                                                If None, all accounts are updated.
        """
        requested_emails = call.data.get(ATTR_EMAIL)
        update_last_called = self._functions.get("update_last_called")

        if not callable(update_last_called):
            _LOGGER.error(
                "update_last_called function not registered; cannot update last_called"
            )
            return

        _LOGGER.debug("Service update_last_called called for: %s", requested_emails)

        for email, account_dict in self.hass.data[DATA_ALEXAMEDIA]["accounts"].items():
            if requested_emails and email not in requested_emails:
                continue

            login_obj = account_dict["login_obj"]

            async def _run_update_last_called(email: str, login_obj) -> None:
                try:
                    await update_last_called(login_obj)
                except asyncio.CancelledError:
                    raise
                except AlexapyLoginError:
                    report_relogin_required(self.hass, login_obj, email)
                except AlexapyConnectionError:
                    _LOGGER.error(
                        "Unable to connect to Alexa for %s;"
                        " check your network connection and try again",
                        hide_email(email),
                    )
                except Exception:  # pragma: no cover
                    _LOGGER.exception(
                        "Unexpected error updating last_called for %s",
                        hide_email(email),
                    )
                finally:
                    # Clean up task reference when done
                    if email in self.hass.data[DATA_ALEXAMEDIA]["accounts"]:
                        self.hass.data[DATA_ALEXAMEDIA]["accounts"][email].pop(
                            "service_update_last_called_task", None
                        )

            # Cancel any existing task for this account before creating a new one
            existing_task = account_dict.get("service_update_last_called_task")
            if existing_task and not existing_task.done():
                existing_task.cancel()

            # Store task handle for proper cleanup on unload
            task = self.hass.async_create_task(
                _run_update_last_called(email, login_obj),
                name=f"alexa_media.update_last_called.{hide_email(email)}",
            )
            account_dict["service_update_last_called_task"] = task

    async def restore_volume(self, call: ServiceCall) -> bool:
        """Handle restore volume service request.

        Arguments:
            call.ATTR_ENTITY_ID {str: None} -- Alexa Media Player entity.

        """
        entity_id = call.data.get(ATTR_ENTITY_ID)
        _LOGGER.debug("Service restore_volume called for: %s", entity_id)

        # Retrieve the entity registry and entity entry
        entity_registry = er.async_get(self.hass)
        entity_entry = entity_registry.async_get(entity_id)

        if not entity_entry:
            _LOGGER.error("Entity %s not found in registry", entity_id)
            return False

        # Retrieve the state and attributes
        state = self.hass.states.get(entity_id)
        if not state:
            _LOGGER.warning("Entity %s has no state; cannot restore volume", entity_id)
            return False

        previous_volume = state.attributes.get("previous_volume")
        current_volume = state.attributes.get("volume_level")

        if previous_volume is None:
            _LOGGER.warning(
                "Previous volume not found for %s; attempting to use current volume level: %s",
                entity_id,
                current_volume,
            )
            previous_volume = current_volume

        if previous_volume is None:
            _LOGGER.warning(
                "No valid volume levels found for entity %s; cannot restore volume",
                entity_id,
            )
            return False

        # Call the volume_set service with the retrieved volume
        await self.hass.services.async_call(
            domain="media_player",
            service="volume_set",
            service_data={
                "volume_level": previous_volume,
            },
            target={"entity_id": entity_id},
            blocking=True,
        )

        _LOGGER.debug("Volume restored to %s for entity %s", previous_volume, entity_id)
        return True

    def _resolve_device(self, entity_id):
        """Resolve a media_player entity_id to (login_obj, serial, device_type)."""
        entity_registry = er.async_get(self.hass)
        entity_entry = entity_registry.async_get(entity_id)
        if not entity_entry or entity_entry.platform != DOMAIN:
            _LOGGER.error("Entity %s not found or not part of %s", entity_id, DOMAIN)
            return None, None, None
        unique_id = entity_entry.unique_id
        accounts = self.hass.data[DATA_ALEXAMEDIA]["accounts"]
        for email, account_dict in accounts.items():
            for device in AlexaAPI.devices.get(email, []):
                serial = device.get("serialNumber")
                if not serial:
                    continue
                # Match the media_player unique id convention: raw serial for the
                # primary account, slugify("<serial>_<email>") for secondaries.
                if unique_id in (serial, slugify(f"{serial}_{email}")):
                    return account_dict["login_obj"], serial, device.get("deviceType")
        _LOGGER.error("No Alexa Media account/device found for entity %s", entity_id)
        return None, None, None

    async def _resolve_child_id(self, login_obj, child):
        """Resolve a child (directedId or first name) to its directedId."""
        if child and child.startswith("amzn1.account"):
            return child
        profiles = await AlexaAPI.get_child_profiles(login_obj) or []
        for profile in profiles:
            if (profile.get("firstName") or "").lower() == (child or "").lower():
                return profile.get("directedId")
        _LOGGER.error("Child profile '%s' not found in household", child)
        return None

    async def _async_refresh_kids(self, login_obj) -> None:
        """Refresh the shared Amazon Kids state of the account."""
        for account_dict in self.hass.data[DATA_ALEXAMEDIA]["accounts"].values():
            if account_dict.get("login_obj") is not login_obj:
                continue
            kids_state = account_dict.get("amazon_kids")
            if kids_state is not None:
                await kids_state.async_refresh()
            return

    @_catch_login_errors
    async def amazon_kids_enable(self, call: ServiceCall) -> bool:
        """Enable Amazon Kids on a device by assigning it to a child profile.

        Arguments:
            call.ATTR_ENTITY_ID {str} -- Alexa Media Player entity.
            call.ATTR_CHILD {str} -- Child first name or directedId.

        """
        entity_id = call.data.get(ATTR_ENTITY_ID)
        child = call.data.get(ATTR_CHILD)
        login_obj, serial, device_type = self._resolve_device(entity_id)
        if not login_obj:
            return False
        child_id = await self._resolve_child_id(login_obj, child)
        if not child_id:
            return False
        await AlexaAPI.enable_child_mode(login_obj, serial, device_type, child_id)
        _LOGGER.debug("Enabled Amazon Kids on %s for child %s", entity_id, child)
        await self._async_refresh_kids(login_obj)
        return True

    @_catch_login_errors
    async def amazon_kids_disable(self, call: ServiceCall) -> bool:
        """Disable Amazon Kids on a device (unassign it from any child).

        Arguments:
            call.ATTR_ENTITY_ID {str} -- Alexa Media Player entity.

        """
        entity_id = call.data.get(ATTR_ENTITY_ID)
        login_obj, serial, device_type = self._resolve_device(entity_id)
        if not login_obj:
            return False
        await AlexaAPI.disable_child_mode(login_obj, serial, device_type)
        _LOGGER.debug("Disabled Amazon Kids on %s", entity_id)
        await self._async_refresh_kids(login_obj)
        return True

    def _resolve_alarm_device(self, entity_id):
        """Resolve a media_player entity_id to (login_obj, serial, device_type, time_zone)."""
        login_obj, serial, device_type = self._resolve_device(entity_id)
        if not login_obj:
            raise ServiceValidationError(f"{entity_id} is not an Alexa Media device")
        time_zone_id = safe_get(
            self.hass.data[DATA_ALEXAMEDIA]["accounts"],
            [login_obj.email, "devices", "media_player", serial, "timeZoneId"],
        )
        time_zone = dt_util.get_time_zone(time_zone_id) if time_zone_id else None
        return login_obj, serial, device_type, time_zone

    def _resolve_alarm(self, entity_id, alarm_id):
        """Resolve a media_player entity_id and alarm id to (login_obj, serial, alarm, time_zone)."""
        login_obj, serial, _, time_zone = self._resolve_alarm_device(entity_id)
        alarms = safe_get(
            self.hass.data[DATA_ALEXAMEDIA]["accounts"],
            [login_obj.email, "notifications", serial, "Alarm"],
            {},
        )
        for index, alarm in alarms.items():
            if alarm_id in (index, alarm.get("id")):
                return login_obj, serial, alarm, time_zone
        raise ServiceValidationError(f"Alarm {alarm_id} not found on {entity_id}")

    async def _change_alarm(
        self, request, login_obj, serial, entity_id, service
    ) -> bool:
        """Send an alarm change and refresh the alarm list, or raise if it failed."""
        try:
            success = await request
        except AlexapyLoginError as err:
            if not await login_obj.test_loggedin():
                report_relogin_required(self.hass, login_obj, login_obj.email)
            raise HomeAssistantError(
                f"Alexa login failed during {service} for {entity_id}"
            ) from err
        except (
            AlexapyConnectionError,
            AlexapyTooManyRequestsError,
            TimeoutError,
        ) as err:
            raise HomeAssistantError(
                f"Couldn't reach Amazon for {service} on {entity_id}"
            ) from err
        if not success:
            raise HomeAssistantError(f"Amazon refused {service} for {entity_id}")
        schedule_refresh = self._functions.get("schedule_notifications_refresh")
        if callable(schedule_refresh):
            schedule_refresh(
                self.hass, login_obj.email, device_serial=serial, reason=service
            )
        return True

    @staticmethod
    def _music_key(provider: str, entity: str) -> str:
        """Use an exact, case-insensitive provider and content match."""
        return f"{provider.strip().casefold()}\n{entity.strip().casefold()}"

    def _cached_music_assets(self, login_obj) -> dict[str, str]:
        """Read valid music assets from currently known account notifications."""
        import uuid

        result = {}
        notifications = (
            self.hass.data[DATA_ALEXAMEDIA]["accounts"]
            .get(login_obj.email, {})
            .get("notifications", {})
        )
        for device_notifications in notifications.values():
            if not isinstance(device_notifications, dict):
                continue
            alarms = device_notifications.get("Alarm", {})
            if not isinstance(alarms, dict):
                continue
            for alarm in alarms.values():
                if not isinstance(alarm, dict):
                    continue
                provider = alarm.get("provider")
                entity = alarm.get("musicEntity")
                asset_id = alarm.get("musicAlarmId")
                if not all(
                    isinstance(v, str) and v.strip()
                    for v in (provider, entity, asset_id)
                ):
                    continue
                try:
                    uuid.UUID(asset_id)
                except ValueError:
                    continue
                result[self._music_key(provider, entity)] = asset_id
        return result

    async def create_alarm(self, call: ServiceCall) -> bool:
        """Create an alarm on a device.

        Arguments:
            call.ATTR_ENTITY_ID {str} -- Alexa Media Player entity.
            call.ATTR_TIME {time} -- Time the alarm rings.
            call.ATTR_DAYS {list[str]} -- Days to repeat on, empty for a one-off.

        """
        entity_id = call.data.get(ATTR_ENTITY_ID)
        days = call.data.get(ATTR_DAYS)
        alarm_type = call.data.get("alarm_type", "default")
        music_provider = call.data.get("music_provider")
        music_entity = call.data.get("music_entity")
        if alarm_type == "music":
            if not music_provider or not music_entity:
                raise ServiceValidationError(
                    "Music alarms require both music_provider and music_entity"
                )
        elif music_provider or music_entity:
            raise ServiceValidationError("Music parameters require alarm_type: music")
        login_obj, serial, device_type, time_zone = self._resolve_alarm_device(
            entity_id
        )
        alarm_when, alarm_repeat = resolve_alarm_schedule(
            call.data.get(ATTR_TIME), days, time_zone
        )
        if alarm_type == "music":
            import uuid

            # Read only current Alexa notification metadata; never persist IDs.
            cached = self._cached_music_assets(login_obj)
            music_alarm_id = cached.get(self._music_key(music_provider, music_entity))
            if not music_alarm_id:
                raise ServiceValidationError(
                    f"No cached Alexa music alarm for '{music_entity}' on "
                    f"'{music_provider}'. Create the selection in Alexa first "
                    "and refresh Alexa Media Player notifications. No alarm created."
                )
            try:
                uuid.UUID(music_alarm_id)
            except (ValueError, TypeError, AttributeError) as err:
                raise ServiceValidationError(
                    "Cached music alarm ID is invalid"
                ) from err
        return await self._change_alarm(
            AlexaAPI.create_alarm(
                login_obj,
                serial,
                device_type,
                alarm_when,
                alarm_repeat,
                f"MUSIC-{music_alarm_id}" if alarm_type == "music" else None,
            ),
            login_obj,
            serial,
            entity_id,
            SERVICE_CREATE_ALARM,
        )

    async def list_alarms(self, call: ServiceCall) -> dict[str, Any]:
        """Return cached Alexa alarm metadata without exposing serials or IDs."""
        entity_id = call.data[ATTR_ENTITY_ID]
        login_obj, serial, _, _ = self._resolve_alarm_device(entity_id)
        alarms = (
            safe_get(
                self.hass.data[DATA_ALEXAMEDIA]["accounts"],
                [login_obj.email, "notifications", serial, "Alarm"],
                {},
            )
            or {}
        )
        result = []
        for alarm in alarms.values():
            result.append(
                {
                    "date": alarm.get("originalDate"),
                    "time": alarm.get("originalTime"),
                    "status": alarm.get("status"),
                    "recurring_pattern": alarm.get("recurringPattern"),
                    "days": alarm_days(alarm),
                    "is_music": bool(alarm.get("musicAlarmId")),
                    "music_entity": alarm.get("musicEntity"),
                    "provider": alarm.get("provider"),
                    "sound": safe_get(alarm, ["sound", "displayName"]),
                }
            )
        result.sort(key=lambda a: (a["date"] or "", a["time"] or ""))
        return {"entity_id": entity_id, "alarms": result, "count": len(result)}

    async def enable_alarm(self, call: ServiceCall) -> bool:
        """Turn an alarm on.

        Arguments:
            call.ATTR_ENTITY_ID {str} -- Alexa Media Player entity.
            call.ATTR_ALARM_ID {str} -- Alarm id or notificationIndex.

        """
        entity_id = call.data.get(ATTR_ENTITY_ID)
        login_obj, serial, alarm, time_zone = self._resolve_alarm(
            entity_id, call.data.get(ATTR_ALARM_ID)
        )
        try:
            alarm_time = datetime.time.fromisoformat(alarm["originalTime"][:8])
            start = datetime.date.fromisoformat(alarm["originalDate"])
        except (KeyError, TypeError, ValueError) as err:
            raise ServiceValidationError(
                f"Alarm {alarm.get('id')} on {entity_id} has no time"
            ) from err
        days = alarm_days(alarm)
        if alarm.get("recurringPattern") and not days:
            raise ServiceValidationError(
                f"Can't tell when alarm {alarm.get('id')} on {entity_id} repeats"
            )
        when = next_alarm_time(alarm_time, days, start, time_zone)
        return await self._change_alarm(
            AlexaAPI.enable_alarm(
                login_obj, alarm["notificationIndex"], when, alarm_sound(alarm)
            ),
            login_obj,
            serial,
            entity_id,
            SERVICE_ENABLE_ALARM,
        )

    async def disable_alarm(self, call: ServiceCall) -> bool:
        """Turn an alarm off without deleting it.

        Arguments:
            call.ATTR_ENTITY_ID {str} -- Alexa Media Player entity.
            call.ATTR_ALARM_ID {str} -- Alarm id or notificationIndex.

        """
        entity_id = call.data.get(ATTR_ENTITY_ID)
        login_obj, serial, alarm, _ = self._resolve_alarm(
            entity_id, call.data.get(ATTR_ALARM_ID)
        )
        return await self._change_alarm(
            AlexaAPI.disable_alarm(login_obj, alarm["notificationIndex"]),
            login_obj,
            serial,
            entity_id,
            SERVICE_DISABLE_ALARM,
        )

    async def skip_next_alarm(self, call: ServiceCall) -> bool:
        """Request skipping the next occurrence of an active recurring alarm."""
        entity_id = call.data[ATTR_ENTITY_ID]
        login_obj, serial, alarm, _ = self._resolve_alarm(
            entity_id, call.data[ATTR_ALARM_ID]
        )
        index = alarm.get("notificationIndex")
        if not isinstance(index, str) or not index:
            raise ServiceValidationError(
                f"Alarm on {entity_id} has no notification index"
            )
        if alarm.get("status") != "ON" or not alarm_days(alarm):
            raise ServiceValidationError(
                f"Only active recurring alarms can be skipped on {entity_id}"
            )
        return await self._change_alarm(
            AlexaAPI.skip_next_alarm(login_obj, index),
            login_obj,
            serial,
            entity_id,
            SERVICE_SKIP_NEXT_ALARM,
        )

    async def delete_alarm(self, call: ServiceCall) -> bool:
        """Delete an alarm.

        Arguments:
            call.ATTR_ENTITY_ID {str} -- Alexa Media Player entity.
            call.ATTR_ALARM_ID {str} -- Alarm id or notificationIndex.

        """
        entity_id = call.data.get(ATTR_ENTITY_ID)
        login_obj, serial, alarm, _ = self._resolve_alarm(
            entity_id, call.data.get(ATTR_ALARM_ID)
        )
        # Send Amazon's own fields back. date_time is ours, and the sensors turn
        # a snoozed alarm's snoozedToTime into a datetime, which isn't JSON.
        notification = {
            k: v
            for k, v in alarm.items()
            if k != "date_time" and not isinstance(v, datetime.datetime)
        }
        return await self._change_alarm(
            AlexaAPI.delete_notification(login_obj, notification),
            login_obj,
            serial,
            entity_id,
            SERVICE_DELETE_ALARM,
        )

    async def get_history_records(self, call: ServiceCall) -> bool:
        """Handle request to get history records and store them on the entity."""
        entity_id = call.data.get(ATTR_ENTITY_ID)
        number_of_entries = call.data.get(ATTR_NUM_ENTRIES)

        # Validate number_of_entries
        try:
            number_of_entries_int = int(number_of_entries)
        except (TypeError, ValueError):
            _LOGGER.exception(
                "Service get_history_records for %s has invalid entries value: %s",
                entity_id,
                number_of_entries,
            )
            return False

        if number_of_entries_int <= 0:
            _LOGGER.error(
                "Service get_history_records for %s with %s entries is invalid; must be > 0",
                entity_id,
                number_of_entries_int,
            )
            return False

        _LOGGER.debug(
            "Service get_history_records for: %s with %s entries",
            entity_id,
            number_of_entries_int,
        )

        # Validate the target entity
        entity_registry = er.async_get(self.hass)
        entity_entry = entity_registry.async_get(entity_id)
        if not entity_entry or entity_entry.platform != DOMAIN:
            _LOGGER.error("Entity %s not found or not part of %s", entity_id, DOMAIN)
            return False
        target_serial_number = entity_entry.unique_id

        history_data_total: list[dict[str, Any]] = []

        async def _collect_history_for_account(login_obj) -> None:
            """Collect history entries for a single account matching the target device."""
            # Get the history records. Input: time_from, time_to (both None here).
            history_data = await AlexaAPI.get_customer_history_records(
                login_obj, None, None
            )
            if not history_data:
                return

            for item in history_data:
                summary = safe_get(item, ["description", "summary"], "")
                device_serial_number = item.get("deviceSerialNumber")
                timestamp = item.get("creationTimestamp")

                if (
                    not summary
                    or summary == ","
                    or device_serial_number != target_serial_number
                    or timestamp is None
                ):
                    continue

                entry = {
                    "timestamp": timestamp,
                    "summary": summary,
                    "response": item.get("alexaResponse", ""),
                }
                history_data_total.append(entry)

        # Iterate accounts and collect history
        for email, account_dict in self.hass.data[DATA_ALEXAMEDIA]["accounts"].items():
            login_obj = account_dict["login_obj"]
            try:
                await _collect_history_for_account(login_obj)
            except AlexapyConnectionError:
                _LOGGER.exception(
                    "Error retrieving history for %s",
                    hide_email(email),
                )
            except AlexapyLoginError:
                _LOGGER.exception(
                    "Login error retrieving history for %s",
                    hide_email(email),
                )
                report_relogin_required(self.hass, login_obj, email)

            except asyncio.CancelledError:
                # Let HA cancellation propagate
                raise
            except Exception:
                # Fallback for truly unexpected errors
                _LOGGER.exception(
                    "Unexpected error retrieving history for %s",
                    hide_email(email),
                )

        # Sort and limit entries
        history_data_total.sort(key=lambda x: x["timestamp"], reverse=True)
        history_data_total = history_data_total[:number_of_entries_int]

        # Update the entity's attributes
        state = self.hass.states.get(entity_id)
        if state is not None:
            new_attributes = dict(state.attributes)
            new_attributes["history_records"] = history_data_total
            self.hass.states.async_set(entity_id, state.state, new_attributes)
            return True

        _LOGGER.error("Entity %s state not found", entity_id)
        return False

    async def enable_network_discovery(self, call: ServiceCall) -> None:
        """Re-enable network discovery for one or more Alexa accounts."""
        data = call.data or {}
        target_emails: list[str] = data.get(ATTR_EMAIL, [])

        accounts = self.hass.data[DATA_ALEXAMEDIA]["accounts"]
        any_matched = False

        for email, account_dict in accounts.items():
            if target_emails and email not in target_emails:
                continue

            any_matched = True

            if "should_get_network" not in account_dict:
                _LOGGER.debug(
                    "Account %s has no 'should_get_network' flag; skipping",
                    hide_email(email),
                )
                continue

            account_dict["should_get_network"] = True
            _LOGGER.debug(
                "Re-enabled network discovery for Alexa Media account %s",
                hide_email(email),
            )

        if target_emails and not any_matched:
            _LOGGER.warning(
                "enable_network_discovery called for %s but no matching Alexa Media accounts were found",
                target_emails,
            )
