"""
Alexa Config Flow.

SPDX-License-Identifier: Apache-2.0

Secure enrollment (RFC #3523): the user authenticates on Amazon's own login
page in their browser (paste-URL flow, no proxy) and pastes the resulting
redirect URL back. Only the minimized device credentials are persisted, and
they live in a dedicated protected store — never the password or a TOTP seed.

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""

from collections import OrderedDict
import logging
from typing import Any, Optional

import aiohttp
from alexapy import (
    AuthTerminalError,
    AuthTransientError,
    EnrollmentError,
    EnrollmentFlow,
    TokenManager,
    hide_email,
    obfuscate,
)
from awesomeversion import AwesomeVersion
from homeassistant import config_entries
from homeassistant.const import (
    CONF_EMAIL,
    CONF_SCAN_INTERVAL,
    CONF_URL,
    __version__ as HAVERSION,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
import voluptuous as vol

from .const import (
    CONF_DEBUG,
    CONF_EXCLUDE_DEVICES,
    CONF_EXTENDED_ENTITY_DISCOVERY,
    CONF_INCLUDE_DEVICES,
    CONF_OAUTH,
    CONF_PASTE_URL,
    CONF_PUBLIC_URL,
    CONF_QUEUE_DELAY,
    CONF_SECURE,
    DEFAULT_DEBUG,
    DEFAULT_EXTENDED_ENTITY_DISCOVERY,
    DEFAULT_PUBLIC_URL,
    DEFAULT_QUEUE_DELAY,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .secure_store import SecureCredentialStore

_LOGGER = logging.getLogger(__name__)

CONFIG_VERSION = 2


@callback
def configured_instances(hass):
    """Return a set of configured Alexa Media instances."""
    return {entry.title for entry in hass.config_entries.async_entries(DOMAIN)}


@callback
def in_progress_instances(hass):
    """Return a set of in-progress Alexa Media flows."""
    return {
        entry["flow_id"]
        for entry in hass.config_entries.flow.async_progress()
        if entry["handler"] == DOMAIN
    }


@config_entries.HANDLERS.register(DOMAIN)
class AlexaMediaFlowHandler(config_entries.ConfigFlow):
    """Handle an Alexa Media config flow.

    Enrollment is a two-step, credential-minimizing flow: collect the account
    label and region, then have the user log in on Amazon's own page and paste
    back the redirect URL. The password and any MFA are handled entirely by
    Amazon; nothing but the derived device credentials is ever stored.
    """

    VERSION = CONFIG_VERSION

    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize the config flow."""
        self.config: OrderedDict = OrderedDict()
        self._enrollment: Optional[EnrollmentFlow] = None

    async def async_step_user(self, user_input=None):
        """Step 1: collect the account label + region, then show the login URL.

        No password or TOTP seed is entered here or stored. See
        https://github.com/superbeetle1973/alexa-auth-redesign
        """
        self._save_user_input_to_config(user_input=user_input)
        reauth = bool(self.config.get("reauth"))
        if not user_input or not self.config.get(CONF_EMAIL):
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(self._user_schema()),
                description_placeholders={"message": "REAUTH" if reauth else ""},
            )
        try:
            self._enrollment = EnrollmentFlow(domain=self.config[CONF_URL])
        except EnrollmentError as err:
            _LOGGER.debug("Rejected domain %s: %s", self.config.get(CONF_URL), err)
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(self._user_schema()),
                errors={"base": "invalid_domain"},
                description_placeholders={"message": "REAUTH" if reauth else ""},
            )
        return self.async_show_form(
            step_id="paste",
            data_schema=vol.Schema({vol.Required(CONF_PASTE_URL): str}),
            description_placeholders={
                "url": self._enrollment.oauth_url,
                "email": self.config[CONF_EMAIL],
            },
        )

    async def async_step_paste(self, user_input=None):
        """Step 2: accept the pasted maplanding URL and register the device."""
        if self._enrollment is None:
            return await self.async_step_user()
        if not user_input or not user_input.get(CONF_PASTE_URL):
            return self._paste_form("paste_required")
        try:
            code = self._enrollment.parse_redirect_url(user_input[CONF_PASTE_URL])
        except EnrollmentError as err:
            _LOGGER.debug("Paste-URL rejected: %s", err)
            return self._paste_form("paste_invalid")
        try:
            async with aiohttp.ClientSession() as session:
                creds = await self._enrollment.async_register(session, code)
        except EnrollmentError as err:
            _LOGGER.debug("Device registration failed: %s", err)
            return self._paste_form("register_failed")
        # Account binding is mandatory: without a stable Amazon account id we
        # cannot enforce the reauth mismatch / duplicate guards.
        if not creds.customer_id:
            _LOGGER.debug("Registration returned no account id; rejecting")
            return self._paste_form("register_failed")
        # Validate the freshly minted credentials before persisting anything, so
        # a bad registration cannot overwrite a working store (reauth) or create
        # a dead entry.
        try:
            async with aiohttp.ClientSession() as session:
                await TokenManager(creds).async_refresh_access_token(session)
        except AuthTerminalError as err:
            _LOGGER.debug("New credentials rejected on validation: %s", err)
            return self._paste_form("register_failed")
        except AuthTransientError as err:
            _LOGGER.debug("Transient error validating new credentials: %s", err)
            return self._paste_form("try_again")
        return await self._finish_secure_enrollment(creds)

    async def _finish_secure_enrollment(self, creds) -> FlowResult:
        """Persist only the durable device credentials — no password/seed.

        Binds the config entry to the Amazon account id returned by the
        exchange so a reauth can never silently rebind to a different account.
        """
        email = self.config[CONF_EMAIL]
        url = self.config[CONF_URL]
        existing_entry = self._reauth_entry()

        await self.async_set_unique_id(creds.customer_id)
        if existing_entry:
            # A legacy (pre-secure) entry is keyed by "<email> - <region>", not
            # the Amazon account id. Binding it to the account id for the first
            # time is expected; only reject when an already-account-bound entry
            # is being reauthenticated against a different account.
            existing_uid = existing_entry.unique_id or ""
            if existing_uid.startswith("amzn1.account"):
                self._abort_if_unique_id_mismatch(reason="wrong_account")
        else:
            self._abort_if_unique_id_configured()

        # The config entry never holds secrets; the minimized device credentials
        # go to the dedicated protected store.
        self.config[CONF_SECURE] = True
        self.config.pop(CONF_OAUTH, None)
        self.config.pop("reauth", None)
        self.config.setdefault(CONF_DEBUG, DEFAULT_DEBUG)
        self.config.setdefault(CONF_INCLUDE_DEVICES, "")
        self.config.setdefault(CONF_EXCLUDE_DEVICES, "")
        self.config.setdefault(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        self.config.setdefault(CONF_QUEUE_DELAY, DEFAULT_QUEUE_DELAY)
        self.config.setdefault(CONF_PUBLIC_URL, DEFAULT_PUBLIC_URL)
        self.config.setdefault(
            CONF_EXTENDED_ENTITY_DISCOVERY, DEFAULT_EXTENDED_ENTITY_DISCOVERY
        )
        self._enrollment = None

        if existing_entry:
            store = SecureCredentialStore(self.hass, existing_entry.entry_id)
            await store.async_save(creds.as_dict(), pending_validation=False)
            self.hass.config_entries.async_update_entry(
                existing_entry, data=self.config, unique_id=creds.customer_id
            )
            await self.hass.config_entries.async_reload(existing_entry.entry_id)
            _LOGGER.debug("Secure reauth successful for %s", hide_email(email))
            return self.async_abort(reason="reauth_successful")

        # New entry: create it first so we have an entry_id, then attach creds.
        result = self.async_create_entry(title=f"{email} - {url}", data=self.config)
        created = result.get("result")
        if created is not None:
            store = SecureCredentialStore(self.hass, created.entry_id)
            await store.async_save(creds.as_dict(), pending_validation=False)
        return result

    async def async_step_reauth(self, user_input=None):
        """Handle reauth: re-enroll interactively via the paste-URL flow.

        A dead refresh token cannot be recovered unattended — it requires a
        person to log in through Amazon again (the design's product contract),
        so route straight to the secure enrollment form.
        """
        self._save_user_input_to_config(user_input)
        self.config["reauth"] = True
        self._enrollment = None
        _LOGGER.debug("Creating reauth form with %s", obfuscate(self.config))
        return await self.async_step_user()

    def _reauth_entry(self):
        """Return the entry being reauthenticated, if any."""
        if self.source != config_entries.SOURCE_REAUTH:
            return None
        get_entry = getattr(self, "_get_reauth_entry", None)
        if callable(get_entry):
            try:
                return get_entry()
            except Exception:  # noqa: BLE001  # pragma: no cover
                return None
        entry_id = self.context.get("entry_id")
        if entry_id:
            return self.hass.config_entries.async_get_entry(entry_id)
        return None

    def _paste_form(self, error_key: str) -> FlowResult:
        return self.async_show_form(
            step_id="paste",
            data_schema=vol.Schema({vol.Required(CONF_PASTE_URL): str}),
            errors={"base": error_key},
            description_placeholders={
                "url": self._enrollment.oauth_url if self._enrollment else "",
                "email": self.config.get(CONF_EMAIL, ""),
            },
        )

    def _user_schema(self) -> OrderedDict:
        cfg = self.config
        return OrderedDict(
            [
                (vol.Required(CONF_EMAIL, default=cfg.get(CONF_EMAIL, "")), str),
                (vol.Required(CONF_URL, default=cfg.get(CONF_URL, "amazon.com")), str),
                (
                    vol.Optional(
                        CONF_INCLUDE_DEVICES,
                        default=cfg.get(CONF_INCLUDE_DEVICES, ""),
                    ),
                    str,
                ),
                (
                    vol.Optional(
                        CONF_EXCLUDE_DEVICES,
                        default=cfg.get(CONF_EXCLUDE_DEVICES, ""),
                    ),
                    str,
                ),
                (
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=cfg.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                    ),
                    int,
                ),
                (
                    vol.Optional(
                        CONF_QUEUE_DELAY,
                        default=cfg.get(CONF_QUEUE_DELAY, DEFAULT_QUEUE_DELAY),
                    ),
                    float,
                ),
                (
                    vol.Optional(
                        CONF_EXTENDED_ENTITY_DISCOVERY,
                        default=cfg.get(
                            CONF_EXTENDED_ENTITY_DISCOVERY,
                            DEFAULT_EXTENDED_ENTITY_DISCOVERY,
                        ),
                    ),
                    bool,
                ),
                (
                    vol.Optional(
                        CONF_DEBUG, default=cfg.get(CONF_DEBUG, DEFAULT_DEBUG)
                    ),
                    bool,
                ),
            ]
        )

    def _save_user_input_to_config(self, user_input=None) -> None:
        """Fold submitted form values into self.config."""
        if user_input is None:
            return
        for key in (
            CONF_EMAIL,
            CONF_URL,
            CONF_INCLUDE_DEVICES,
            CONF_EXCLUDE_DEVICES,
            CONF_QUEUE_DELAY,
            CONF_EXTENDED_ENTITY_DISCOVERY,
            CONF_DEBUG,
        ):
            if key in user_input:
                self.config[key] = user_input[key]
        if CONF_SCAN_INTERVAL in user_input:
            value = user_input[CONF_SCAN_INTERVAL]
            self.config[CONF_SCAN_INTERVAL] = (
                value.total_seconds() if hasattr(value, "total_seconds") else value
            )
        if CONF_PUBLIC_URL in user_input:
            public_url = user_input[CONF_PUBLIC_URL]
            if public_url and not public_url.endswith("/"):
                public_url = public_url + "/"
            self.config[CONF_PUBLIC_URL] = public_url

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle an options flow for Alexa Media."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config = OrderedDict()
        if AwesomeVersion(HAVERSION) < "2024.12":
            self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        self.options_schema = OrderedDict(
            [
                (
                    vol.Optional(
                        CONF_PUBLIC_URL,
                        default=self.config_entry.data.get(
                            CONF_PUBLIC_URL, DEFAULT_PUBLIC_URL
                        ),
                    ),
                    str,
                ),
                (
                    vol.Optional(
                        CONF_INCLUDE_DEVICES,
                        default=self.config_entry.data.get(CONF_INCLUDE_DEVICES, ""),
                    ),
                    str,
                ),
                (
                    vol.Optional(
                        CONF_EXCLUDE_DEVICES,
                        default=self.config_entry.data.get(CONF_EXCLUDE_DEVICES, ""),
                    ),
                    str,
                ),
                (
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.data.get(CONF_SCAN_INTERVAL, 120),
                    ),
                    int,
                ),
                (
                    vol.Optional(
                        CONF_QUEUE_DELAY,
                        default=self.config_entry.data.get(
                            CONF_QUEUE_DELAY, DEFAULT_QUEUE_DELAY
                        ),
                    ),
                    float,
                ),
                (
                    vol.Optional(
                        CONF_EXTENDED_ENTITY_DISCOVERY,
                        default=self.config_entry.data.get(
                            CONF_EXTENDED_ENTITY_DISCOVERY,
                            DEFAULT_EXTENDED_ENTITY_DISCOVERY,
                        ),
                    ),
                    bool,
                ),
                (
                    vol.Optional(
                        CONF_DEBUG,
                        default=self.config_entry.data.get(CONF_DEBUG, DEFAULT_DEBUG),
                    ),
                    bool,
                ),
            ]
        )

        if user_input is not None:
            # Preserve identity/credential-linkage fields the options form omits.
            for key in (CONF_URL, CONF_EMAIL, CONF_SECURE, CONF_OAUTH):
                if key in self.config_entry.data:
                    user_input[key] = self.config_entry.data[key]
            if (
                CONF_PUBLIC_URL in user_input
                and user_input[CONF_PUBLIC_URL]
                and not user_input[CONF_PUBLIC_URL].endswith("/")
            ):
                user_input[CONF_PUBLIC_URL] = user_input[CONF_PUBLIC_URL] + "/"
            if CONF_INCLUDE_DEVICES in user_input:
                user_input[CONF_INCLUDE_DEVICES] = user_input[
                    CONF_INCLUDE_DEVICES
                ].strip()
            if CONF_EXCLUDE_DEVICES in user_input:
                user_input[CONF_EXCLUDE_DEVICES] = user_input[
                    CONF_EXCLUDE_DEVICES
                ].strip()
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=user_input, options=self.config_entry.options
            )
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(self.options_schema),
            description_placeholders={"message": ""},
        )
