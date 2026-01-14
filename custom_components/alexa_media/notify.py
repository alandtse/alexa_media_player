"""
Alexa Devices notification service.

SPDX-License-Identifier: Apache-2.0

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""

import asyncio
import json
import logging
import time

from alexapy.helpers import hide_email, hide_serial
from homeassistant.components.notify import (
    ATTR_DATA,
    ATTR_TARGET,
    ATTR_TITLE,
    ATTR_TITLE_DEFAULT,
    SERVICE_NOTIFY,
    BaseNotificationService,
)
from homeassistant.const import CONF_EMAIL
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.group import expand_entity_ids
import voluptuous as vol

from .const import (
    CONF_QUEUE_DELAY,
    DATA_ALEXAMEDIA,
    DEFAULT_QUEUE_DELAY,
    DOMAIN,
    NOTIFY_URL,
)
from .helpers import retry_async

_LOGGER = logging.getLogger(__name__)


@retry_async(limit=5, delay=2, catch_exceptions=True)
async def async_get_service(hass, config, discovery_info=None):
    # pylint: disable=unused-argument
    """Get the demo notification service."""
    result = False
    for account, account_dict in hass.data[DATA_ALEXAMEDIA]["accounts"].items():
        for key, _ in account_dict["devices"]["media_player"].items():
            if key not in account_dict["entities"]["media_player"]:
                _LOGGER.debug(
                    "%s: Media player %s not loaded yet; delaying load",
                    hide_email(account),
                    hide_serial(key),
                )
                return False
    result = hass.data[DATA_ALEXAMEDIA]["notify_service"] = AlexaNotificationService(
        hass
    )
    return result


async def async_unload_entry(hass, entry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Attempting to unload notify")
    target_account = entry.data[CONF_EMAIL]
    other_accounts = False
    for account, account_dict in hass.data[DATA_ALEXAMEDIA]["accounts"].items():
        if account == target_account:
            if "entities" not in account_dict:
                continue
            for device in account_dict["entities"]["media_player"].values():
                if device.entity_id:
                    entity_id = device.entity_id.split(".")
                    hass.services.async_remove(
                        SERVICE_NOTIFY, f"{DOMAIN}_{entity_id[1]}"
                    )
        else:
            other_accounts = True
    if not other_accounts:
        hass.services.async_remove(SERVICE_NOTIFY, f"{DOMAIN}")
        if hass.data[DATA_ALEXAMEDIA].get("notify_service"):
            hass.data[DATA_ALEXAMEDIA].pop("notify_service")
    return True


class AlexaNotificationService(BaseNotificationService):
    """Implement Alexa Media Player notification service."""

    def __init__(self, hass):
        """Initialize the service."""
        self.hass = hass
        self.last_called = True

        # Cache to keep the last_called target service stable (per account)
        # email -> {"unique_id": str, "ts": int}
        self._last_called_cache: dict[str, dict[str, object]] = {}

    def convert(self, names, type_="entities", filter_matches=False):
        """Return a list of converted Alexa devices based on names.

        Names may be matched either by serialNumber, accountName, or
        Homeassistant entity_id and can return any of the above plus entities

        Parameters
        ----------
        names : list(string)
            A list of names to convert
        type_ : string
            The type to return entities, entity_ids, serialnumbers, names
        filter_matches : bool
            Whether non-matching items are removed from the returned list.

        Returns
        -------
        list(string)
            List of home assistant entity_ids

        """
        devices = []
        if isinstance(names, str):
            names = [names]
        for item in names:
            matched = False
            for alexa in self.devices:
                # _LOGGER.debug(
                #     "Testing item: %s against (%s, %s, %s, %s)",
                #     item,
                #     alexa,
                #     alexa.name,
                #     hide_serial(alexa.unique_id),
                #     alexa.entity_id,
                # )
                if item in (
                    alexa,
                    alexa.name,
                    alexa.unique_id,
                    alexa.entity_id,
                    alexa.device_serial_number,
                ):
                    if type_ == "entities":
                        converted = alexa
                    elif type_ == "serialnumbers":
                        converted = alexa.device_serial_number
                    elif type_ == "names":
                        converted = alexa.name
                    elif type_ == "entity_ids":
                        converted = alexa.entity_id
                    devices.append(converted)
                    matched = True
                    # _LOGGER.debug("Converting: %s to (%s): %s", item, type_, converted)
            if not filter_matches and not matched:
                devices.append(item)
        return devices

    @property
    def targets(self):
        """Return a dictionary of Alexa devices."""
        devices: dict[str, str] = {}

        global_newest_entity_id: str | None = None
        global_newest_ts: int = -1

        for email, account_dict in self.hass.data[DATA_ALEXAMEDIA]["accounts"].items():
            if "entities" not in account_dict:
                continue

            last_called_entity = None
            last_called_ts = -1

            for entity in account_dict["entities"]["media_player"].values():
                if entity is None or entity.entity_id is None:
                    continue

                entity_name = entity.entity_id.split(".")[1]
                devices[entity_name] = entity.entity_id

                if self.last_called and (entity.extra_state_attributes or {}).get("last_called"):
                    ts = int((entity.extra_state_attributes or {}).get("last_called_timestamp") or 0)
                    if ts > last_called_ts:
                        last_called_entity = entity
                        last_called_ts = ts

            acct_key = f"last_called_{self._account_index(email)}"

            if last_called_entity is not None:
                devices[acct_key] = last_called_entity.entity_id

                self._last_called_cache[email] = {
                    "entity_id": last_called_entity.entity_id,
                    "ts": last_called_ts,
                    "acct_key": acct_key,
                }

                if last_called_ts > global_newest_ts:
                    global_newest_ts = last_called_ts
                    global_newest_entity_id = last_called_entity.entity_id

            else:
                cached = self._last_called_cache.get(email)
                if cached and cached.get("entity_id") and cached.get("acct_key"):
                    devices[str(cached["acct_key"])] = str(cached["entity_id"])

        # Global target: newest overall
        if global_newest_entity_id:
            devices["last_called"] = global_newest_entity_id
            self._last_called_cache["_global"] = {
                "entity_id": global_newest_entity_id,
                "ts": global_newest_ts,
            }
        else:
            # Fallback: pick newest cached per-account ts
            best_entity_id = None
            best_ts = -1
            for k, cached in self._last_called_cache.items():
                if k == "_global":
                    continue
                ts = int(cached.get("ts") or 0)
                eid = cached.get("entity_id")
                if eid and ts > best_ts:
                    best_ts = ts
                    best_entity_id = str(eid)

            if best_entity_id:
                devices["last_called"] = best_entity_id
            else:
                cached_global = self._last_called_cache.get("_global")
                if cached_global and cached_global.get("entity_id"):
                    devices["last_called"] = str(cached_global["entity_id"])

        return devices

    @property
    def devices(self):
        """Return a list of Alexa devices."""
        devices = []
        if (
            "accounts" not in self.hass.data[DATA_ALEXAMEDIA]
            and not self.hass.data[DATA_ALEXAMEDIA]["accounts"].items()
        ):
            return devices
        for _, account_dict in self.hass.data[DATA_ALEXAMEDIA]["accounts"].items():
            devices = devices + list(account_dict["entities"]["media_player"].values())
        return devices

    def _get_current_last_called_entity(self, email: str):
        """Return the current last_called media_player entity for an account.

        Picks the entity with the newest last_called_timestamp.
        """
        account_dict = self.hass.data[DATA_ALEXAMEDIA]["accounts"].get(email)
        if not account_dict or "entities" not in account_dict:
            return None

        newest = None
        newest_ts = -1
        for ent in account_dict["entities"]["media_player"].values():
            if ent is None or ent.entity_id is None:
                continue
            attrs = ent.extra_state_attributes or {}
            if not attrs.get("last_called"):
                continue
            ts = int(attrs.get("last_called_timestamp") or 0)
            if ts > newest_ts:
                newest = ent
                newest_ts = ts

        return newest

    def _account_index(self, email: str) -> int:
        """Return 1-based stable account index for service-safe naming."""
        account_dict = self.hass.data[DATA_ALEXAMEDIA]["accounts"].get(email) or {}
        raw = account_dict.get("second_account_index", 0)
        try:
            base = int(raw)
        except (TypeError, ValueError):
            base = 0
        return base + 1


    def _email_for_account_index(self, idx: int) -> str | None:
        """Reverse lookup: 1-based index -> email."""
        try:
            idx = int(idx)
        except (TypeError, ValueError):
            return None
    
        for email, account_dict in self.hass.data[DATA_ALEXAMEDIA]["accounts"].items():
            raw = (account_dict or {}).get("second_account_index", 0)
            try:
                base = int(raw)
            except (TypeError, ValueError):
                base = 0
            if base + 1 == idx:
                return email
        return None

    def _get_newest_last_called_entity_global(self):
        """Return the newest last_called entity across *all* accounts."""
        newest = None
        newest_ts = -1
        for email in self.hass.data[DATA_ALEXAMEDIA]["accounts"].keys():
            ent = self._get_current_last_called_entity(email)
            if not ent:
                continue
            ts = int((ent.extra_state_attributes or {}).get("last_called_timestamp") or 0)
            if ts > newest_ts:
                newest = ent
                newest_ts = ts
        return newest

    async def async_send_message(self, message="", **kwargs):
        # pylint: disable=too-many-branches
        """Send a message to a Alexa device."""
        _LOGGER.debug("Message: %s, kwargs: %s", message, kwargs)
        _LOGGER.debug("Target type: %s", type(kwargs.get(ATTR_TARGET)))

        kwargs["message"] = message
        raw_targets = kwargs.get(ATTR_TARGET) or []
        title = kwargs.get(ATTR_TITLE, ATTR_TITLE_DEFAULT)

        data = kwargs.get(ATTR_DATA, {})
        data = data if data is not None else {}
        data_type = data.get("type", "tts")

        # HA can pass a JSON-encoded string for target
        if isinstance(raw_targets, str):
            try:
                raw_targets = json.loads(raw_targets)
            except json.JSONDecodeError:
                _LOGGER.error("Target must be valid JSON when passed as a string")
                return

        processed_targets: list[object] = []

        # Normalize all incoming target formats into a flat list
        for target in raw_targets:
            _LOGGER.debug("Processing: %s", target)

            if not isinstance(target, str):
                processed_targets.append(target)
                continue

            # Some callers pass a JSON list as a string element, e.g. '["a","b"]'
            try:
                loaded = json.loads(target)
                if isinstance(loaded, list):
                    processed_targets += loaded
                else:
                    processed_targets.append(loaded)
                _LOGGER.debug("Processed Target by json: %s", processed_targets)
                continue
            except (json.JSONDecodeError, TypeError):
                pass

            # Comma-separated string list
            if "," in target:
                processed_targets += [x.strip() for x in target.split(",") if x.strip()]
                _LOGGER.debug("Processed Target by string: %s", processed_targets)
            else:
                processed_targets.append(target.strip())
                _LOGGER.debug(
                    "Processed Target by single string: %s",
                    processed_targets,
                )

        _LOGGER.debug("Processed targets: %s", processed_targets)

        # --- Dynamic routing for last_called targets (no re-register needed) ---
        resolved_targets: list[object] = []
        for t in processed_targets:
            if not isinstance(t, str):
                resolved_targets.append(t)
                continue

            if t == "last_called":
                ent = self._get_newest_last_called_entity_global()
                if ent and ent.entity_id:
                    _LOGGER.debug(
                        "Dynamic last_called routing (global newest) -> %s",
                        ent.entity_id,
                    )
                    resolved_targets.append(ent.entity_id)
                else:
                    resolved_targets.append(t)
                continue

            if t.startswith("last_called_"):
                suffix = t[len("last_called_") :]

                try:
                    idx = int(suffix)
                except ValueError:
                    resolved_targets.append(t)
                    continue

                email = self._email_for_account_index(idx)
                if not email:
                    resolved_targets.append(t)
                    continue

                ent = self._get_current_last_called_entity(email)
                if ent and ent.entity_id:
                    _LOGGER.debug(
                        "%s: Dynamic last_called routing (account #%s) -> %s",
                        hide_email(email),
                        idx,
                        ent.entity_id,
                    )
                    resolved_targets.append(ent.entity_id)
                else:
                    resolved_targets.append(t)
                continue

            resolved_targets.append(t)

        # Expand groups / entity IDs safely (strings only)
        entity_ids = [t for t in resolved_targets if isinstance(t, str)]
        try:
            entity_ids = list(set(entity_ids + expand_entity_ids(self.hass, entity_ids)))
        except ValueError:
            _LOGGER.debug("Invalid Home Assistant entity in %s", entity_ids)

        # Convert to entity objects once
        entities = self.convert(entity_ids, type_="entities")
        _LOGGER.debug("Converted entities: %s", entities)
        _LOGGER.debug(
            "Known serials: %s",
            [hide_serial(getattr(d, "device_serial_number", None)) for d in self.devices if d],
        )

        targets_entities = self.convert(entities, type_="entities", filter_matches=True)
        targets_serials = self.convert(entities, type_="serialnumbers", filter_matches=True)

        # --- NEW: synthesize last_called for single-device sends (no HTTP2 push) ---
        # If a call explicitly targets one device (e.g. notify.alexa_media_kitchen_echo_dot),
        # treat that as "last_called" immediately so automations/scripts have a stable signal.
        synthetic_serial: str | None = None

        if data_type in ("tts", "push", "dropin_notification") and len(targets_entities) == 1:
            synthetic_serial = getattr(targets_entities[0], "device_serial_number", None)

        elif data_type == "announce" and len(targets_serials) == 1:
            synthetic_serial = targets_serials[0]

        if synthetic_serial:
            now_ms = int(time.time() * 1000)
            last_called_payload = {
                "serialNumber": synthetic_serial,
                "timestamp": now_ms,
                # Keep behavior consistent with what Amazon often returns for TTS/announce
                "summary": ",",
            }

            # Find which account owns this serial and dispatch the same signal AMP uses
            for email, account_dict in self.hass.data[DATA_ALEXAMEDIA]["accounts"].items():
                ents = (account_dict.get("entities") or {}).get("media_player") or {}
                if any(
                    getattr(ent, "device_serial_number", None) == synthetic_serial
                    for ent in ents.values()
                    if ent
                ):
                    _LOGGER.debug(
                        "%s: Synthesizing last_called from notify (%s) -> %s",
                        hide_email(email),
                        data_type,
                        hide_serial(synthetic_serial),
                    )
                    async_dispatcher_send(
                        self.hass,
                        f"{DOMAIN}_{hide_email(email)}"[0:32],
                        {"last_called_change": last_called_payload},
                    )
                    self.hass.data[DATA_ALEXAMEDIA]["accounts"][email]["last_called"] = last_called_payload
                    break

        tasks = []

        for account, account_dict in self.hass.data[DATA_ALEXAMEDIA]["accounts"].items():
            for alexa in account_dict["entities"]["media_player"].values():
                if data_type == "tts":
                    if alexa in targets_entities and alexa.available:
                        _LOGGER.debug("TTS by %s : %s", alexa, message)
                        tasks.append(
                            alexa.async_send_tts(
                                message,
                                queue_delay=self.hass.data[DATA_ALEXAMEDIA]["accounts"][account][
                                    "options"
                                ].get(CONF_QUEUE_DELAY, DEFAULT_QUEUE_DELAY),
                            )
                        )

                elif data_type == "announce":
                    if alexa.device_serial_number in targets_serials and alexa.available:
                        _LOGGER.debug(
                            "%s: Announce by %s to targets: %s: %s",
                            hide_email(account),
                            alexa,
                            list(map(hide_serial, targets_serials)),
                            message,
                        )
                        tasks.append(
                            alexa.async_send_announcement(
                                message,
                                targets=targets_serials,
                                title=title,
                                method=(data["method"] if "method" in data else "all"),
                                queue_delay=self.hass.data[DATA_ALEXAMEDIA]["accounts"][account][
                                    "options"
                                ].get(CONF_QUEUE_DELAY, DEFAULT_QUEUE_DELAY),
                            )
                        )
                        break

                elif data_type == "push":
                    if alexa in targets_entities and alexa.available:
                        _LOGGER.debug("Push by %s: %s %s", alexa, title, message)
                        tasks.append(
                            alexa.async_send_mobilepush(
                                message,
                                title=title,
                                queue_delay=self.hass.data[DATA_ALEXAMEDIA]["accounts"][account][
                                    "options"
                                ].get(CONF_QUEUE_DELAY, DEFAULT_QUEUE_DELAY),
                            )
                        )

                elif data_type == "dropin_notification":
                    if alexa in targets_entities and alexa.available:
                        _LOGGER.debug("Notification dropin by %s: %s %s", alexa, title, message)
                        tasks.append(
                            alexa.async_send_dropin_notification(
                                message,
                                title=title,
                                queue_delay=self.hass.data[DATA_ALEXAMEDIA]["accounts"][account][
                                    "options"
                                ].get(CONF_QUEUE_DELAY, DEFAULT_QUEUE_DELAY),
                            )
                        )

                else:
                    errormessage = (
                        f"{account}: Data value `type={data_type}` is not implemented. "
                        f"See {NOTIFY_URL}"
                    )
                    _LOGGER.debug(errormessage)
                    raise vol.Invalid(errormessage)

        await asyncio.gather(*tasks)
