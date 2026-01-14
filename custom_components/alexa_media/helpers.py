"""
Helper functions for Alexa Media Player.

SPDX-License-Identifier: Apache-2.0

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""

import asyncio
import functools
import hashlib
import logging
from typing import Any, Callable, Optional, TypeVar, overload

from alexapy import AlexapyLoginCloseRequested, AlexapyLoginError, hide_email
from alexapy.alexalogin import AlexaLogin
from dictor import dictor
from homeassistant.const import CONF_EMAIL, CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConditionErrorMessage
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.instance_id import async_get as async_get_instance_id
import wrapt

from .const import DATA_ALEXAMEDIA, EXCEPTION_TEMPLATE

_LOGGER = logging.getLogger(__name__)
ArgType = TypeVar("ArgType")


async def add_devices(
    account: str,
    devices: list[Entity],
    add_devices_callback: Callable[[list[Entity], bool], None],
    include_filter: Optional[list[str]] = None,
    exclude_filter: Optional[list[str]] = None,
) -> bool:
    """Add devices using add_devices_callback."""
    include_filter = include_filter or []
    exclude_filter = exclude_filter or []

    def _device_name(dev: Entity) -> str | None:
        """Best-effort name before entity_id is assigned."""
        return (
            getattr(dev, "name", None)
            or getattr(dev, "_attr_name", None)
            or getattr(dev, "_name", None)
            or getattr(dev, "_device_name", None)
            or getattr(dev, "_friendly_name", None)
        )

    def _device_label(dev: Entity) -> str:
        """Return a compact, stable identifier for logging."""
        name = _device_name(dev)
        entity_id = getattr(dev, "entity_id", None)  # often not set yet
        dev_type = type(dev).__name__

        if name and entity_id:
            return f"{name} ({dev_type}, {entity_id})"
        if name:
            return f"{name} ({dev_type})"
        return f"<unnamed> ({dev_type})"

    def _devices_preview(devs: list[Entity]) -> str:
        max_items = 8
        labels = [_device_label(d) for d in devs[:max_items]]
        suffix = f" …(+{len(devs) - max_items} more)" if len(devs) > max_items else ""
        return ", ".join(labels) + suffix

    new_devices: list[Entity] = []
    for device in devices:
        dev_name = _device_name(device)

        if (include_filter and dev_name not in include_filter) or (
            exclude_filter and dev_name in exclude_filter
        ):
            _LOGGER.debug("%s: Excluding device: %s", account, _device_label(device))
            continue

        new_devices.append(device)

    devices = new_devices
    if not devices:
        return True

    _LOGGER.debug(
        "%s: Adding %d device(s): %s",
        account,
        len(devices),
        _devices_preview(devices),
    )

    try:
        add_devices_callback(devices, False)
    except ConditionErrorMessage as exception_:
        message: str = exception_.message
        if message.startswith("Entity id already exists"):
            _LOGGER.debug("%s: Device already added: %s", account, message)
        else:
            _LOGGER.debug(
                "%s: Unable to add %d device(s): %s",
                account,
                len(devices),
                message,
            )
    except Exception as ex:  # pylint: disable=broad-except
        _LOGGER.debug(
            "%s: Unable to add %d device(s): %s",
            account,
            len(devices),
            EXCEPTION_TEMPLATE.format(type(ex).__name__, ex.args),
        )
    else:
        return True

    return False


def retry_async(
    limit: int = 5, delay: float = 1, catch_exceptions: bool = True
) -> Callable:
    """Wrap function with retry logic.

    The function will retry until true or the limit is reached. It will delay
    for the period of time specified exponentially increasing the delay.

    Parameters
    ----------
    limit : int
        The max number of retries.
    delay : float
        The delay in seconds between retries.
    catch_exceptions : bool
        Whether exceptions should be caught and treated as failures or thrown.

    Returns
    -------
    def
        Wrapped function.

    """

    def wrap(func) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            _LOGGER.debug(
                "%s.%s: Trying with limit %s delay %s catch_exceptions %s",
                func.__module__[func.__module__.find(".") + 1 :],
                func.__name__,
                limit,
                delay,
                catch_exceptions,
            )
            retries: int = 0
            result: bool = False
            next_try: int = 0
            while not result and retries < limit:
                if retries != 0:
                    next_try = delay * 2**retries
                    await asyncio.sleep(next_try)
                retries += 1
                try:
                    result = await func(*args, **kwargs)
                except Exception as ex:  # pylint: disable=broad-except
                    if not catch_exceptions:
                        raise
                    _LOGGER.debug(
                        "%s.%s: failure caught due to exception: %s",
                        func.__module__[func.__module__.find(".") + 1 :],
                        func.__name__,
                        EXCEPTION_TEMPLATE.format(type(ex).__name__, ex.args),
                    )
                _LOGGER.debug(
                    "%s.%s: Try: %s/%s after waiting %s seconds result: %s",
                    func.__module__[func.__module__.find(".") + 1 :],
                    func.__name__,
                    retries,
                    limit,
                    next_try,
                    result,
                )
            return result

        return wrapper

    return wrap


@wrapt.decorator
async def _catch_login_errors(func, instance, args, kwargs) -> Any:
    """Detect AlexapyLoginError and attempt relogin."""

    result = None
    if instance is None and args:
        instance = args[0]
    if hasattr(instance, "check_login_changes"):
        # _LOGGER.debug(
        #     "%s checking for login changes", instance,
        # )
        instance.check_login_changes()
    try:
        result = await func(*args, **kwargs)
    except AlexapyLoginCloseRequested:
        _LOGGER.debug(
            "%s.%s: Ignoring attempt to access Alexa after HA shutdown",
            func.__module__[func.__module__.find(".") + 1 :],
            func.__name__,
        )
        return None
    except AlexapyLoginError as ex:
        login = None
        email = None
        all_args = list(args) + list(kwargs.values())
        # _LOGGER.debug("Func %s instance %s %s %s", func, instance, args, kwargs)
        if instance:
            if hasattr(instance, "_login"):
                login = instance._login  # pylint: disable=protected-access
                hass = instance.hass
        else:
            for arg in all_args:
                _LOGGER.debug("Checking %s", arg)

                if isinstance(arg, AlexaLogin):
                    login = arg
                    break
                if hasattr(arg, "_login"):
                    login = instance._login
                    hass = instance.hass
                    break

        if login:
            # Try to re-login
            email = login.email
            if await login.test_loggedin():
                _LOGGER.info(
                    "%s.%s: Successfully re-login after a login error for %s",
                    func.__module__[func.__module__.find(".") + 1 :],
                    func.__name__,
                    hide_email(email),
                )
                return None
            _LOGGER.debug(
                "%s.%s: detected bad login for %s: %s",
                func.__module__[func.__module__.find(".") + 1 :],
                func.__name__,
                hide_email(email),
                EXCEPTION_TEMPLATE.format(type(ex).__name__, ex.args),
            )
        try:
            hass
        except NameError:
            hass = None
        report_relogin_required(hass, login, email)
        return None
    return result


def report_relogin_required(hass, login, email) -> bool:
    """Send message for relogin required."""
    if hass and login and email:
        if login.status:
            _LOGGER.debug(
                "Reporting need to relogin to %s with %s stats: %s",
                login.url,
                hide_email(email),
                login.stats,
            )
            hass.bus.async_fire(
                "alexa_media_relogin_required",
                event_data={
                    "email": hide_email(email),
                    "url": login.url,
                    "stats": login.stats,
                },
            )
            return True
    return False


def _existing_serials(hass, login_obj) -> list:
    """Retrieve existing serial numbers for a given login object."""
    email: str = login_obj.email
    if (
        DATA_ALEXAMEDIA in hass.data
        and "accounts" in hass.data[DATA_ALEXAMEDIA]
        and email in hass.data[DATA_ALEXAMEDIA]["accounts"]
    ):
        existing_serials = list(
            hass.data[DATA_ALEXAMEDIA]["accounts"][email]["entities"][
                "media_player"
            ].keys()
        )
        device_data = (
            hass.data[DATA_ALEXAMEDIA]["accounts"][email]
            .get("devices", {})
            .get("media_player", {})
        )
        for serial in existing_serials[:]:
            device = device_data.get(serial, {})
            if "appDeviceList" in device and device["appDeviceList"]:
                apps = [
                    x["serialNumber"]
                    for x in device["appDeviceList"]
                    if "serialNumber" in x
                ]
                existing_serials.extend(apps)
    else:
        _LOGGER.warning(
            "No accounts data found for %s. Skipping serials retrieval.", email
        )
        existing_serials = []
    return existing_serials


async def calculate_uuid(hass, email: str, url: str) -> dict:
    """Return uuid and index of email/url.

    Args
        hass (bool): Hass entity
        url (str): url for account
        email (str): email for account

    Returns
        dict: dictionary with uuid and index

    """
    result = {}
    return_index = 0
    if hass.config_entries.async_entries(DATA_ALEXAMEDIA):
        for index, entry in enumerate(
            hass.config_entries.async_entries(DATA_ALEXAMEDIA)
        ):
            if entry.data.get(CONF_EMAIL) == email and entry.data.get(CONF_URL) == url:
                return_index = index
                break
    uuid = await async_get_instance_id(hass)
    result["uuid"] = hex(
        int(uuid, 16)
        # increment uuid for second accounts
        + return_index
        # hash email/url in case HA uuid duplicated
        + int(
            hashlib.sha256((email.lower() + url.lower()).encode()).hexdigest(),
            16,  # nosec
        )
    )[-32:]
    result["index"] = return_index
    _LOGGER.debug("%s: Returning uuid %s", hide_email(email), result)
    return result


def alarm_just_dismissed(
    alarm: dict[str, Any],
    previous_status: Optional[str],
    previous_version: Optional[str],
) -> bool:
    """Given the previous state of an alarm, determine if it has just been dismissed."""

    if (
        previous_status not in ("SNOOZED", "ON")
        # The alarm had to be in a status that supported being dismissed
        or previous_version is None
        # The alarm was probably just created
        or not alarm
        # The alarm that was probably just deleted.
        or alarm.get("status") not in ("OFF", "ON")
        # A dismissed alarm is guaranteed to be turned off(one-off alarm) or left on(recurring alarm)
        or previous_version == alarm.get("version")
        # A dismissal always has a changed version.
        or int(alarm.get("version", "0")) > 1 + int(previous_version)
    ):
        # This is an absurd thing to check, but it solves many, many edge cases.
        # Experimentally, when an alarm is dismissed, the version always increases by 1
        # When an alarm is edited either via app or voice, its version always increases by 2+
        return False

    # It seems obvious that a check involving time should be necessary. It is not.
    # We know there was a change and that it wasn't an edit.
    # We also know the alarm's status rules out a snooze.
    # The only remaining possibility is that this alarm was just dismissed.
    return True


def is_http2_enabled(hass: HomeAssistant | None, login_email: str) -> bool:
    """Whether HTTP2 push is enabled for the current account session"""
    if hass:
        return bool(
            safe_get(
                hass.data,
                [DATA_ALEXAMEDIA, "accounts", login_email, "http2"],
            )
        )
    return False


@overload
def safe_get(
    data: Any,
    path_list: list[str | int] | None = None,
    checknone: bool = False,
    ignorecase: bool = False,
    pathsep: str = ".",
    search: Any = None,
    pretty: bool = False,
    rtype: str | None = None,
) -> Any | None: ...


@overload
def safe_get(
    data: Any, path_list: list[str | int] | None, default: ArgType, *args, **kwargs
) -> ArgType: ...


def safe_get(
    data: Any, path_list: list[str | int] | None = None, *args, **kwargs
) -> None | Any:
    """Safely get nested value using path segments with optional type checking.

    Args:
        data: Source data structure
        path_list: List of path segments (dots in segment names are auto-escaped)
        *args: Positional arguments passed to dictor (e.g., default value)
        **kwargs: Keyword arguments passed to dictor (checknone, ignorecase)

    Returns:
        The value at the specified path, or None if:
        - The path doesn't exist and no default is provided
        or default if:
        - A default is provided and the path doesn't exist
        - A default is provided and the retrieved value's type doesn't match the default's type

    Note:
        - Do not pass 'pathsep' in kwargs as the path is pre-built.
        - Type checking: When a default value is provided and a non-None value is retrieved,
          the result is validated against the default's type. If types don't match, default is returned.
          This prevents silent type errors from malformed data structures.

    Examples:
        >>> safe_get({"a": {"b": "value"}}, ["a", "b"])
        'value'

        >>> safe_get({"a": {"b": 123}}, ["a", "b"], "default")
        'default'  # Type mismatch: int vs str

        >>> safe_get({"a": {"b": "value"}}, ["a", "b"], "default")
        'value'  # Type matches
    """
    if not path_list:
        raise ValueError("path_list cannot be empty")

    if "pathsep" in kwargs:
        kwargs.pop("pathsep")  # Ignore pathsep since we build the path

    escaped_segments = (str(seg).replace(".", "\\.") for seg in path_list)
    path = ".".join(escaped_segments)
    default = args[0] if args else (kwargs.get("default") if kwargs else None)
    result = dictor(data, path, *args, **kwargs)
    if default is not None and result is not None:
        if not isinstance(result, type(default)):
            result = default
    return result
