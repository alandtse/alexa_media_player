"""Regression coverage for service recovery and reauthentication options."""

from contextlib import nullcontext
from datetime import datetime
from importlib import import_module
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import ServiceValidationError
import pytest

from custom_components.alexa_media import test_login_status as check_login_status
from custom_components.alexa_media.config_flow import (
    AlexaMediaFlowHandler,
    OptionsFlowHandler,
)
from custom_components.alexa_media.const import (
    CONF_OTPSECRET,
    CONFIG_ENTRY_OPTION_KEYS,
    DATA_ALEXAMEDIA,
    DOMAIN,
)
from custom_components.alexa_media.helpers import (
    config_entry_config,
    config_entry_option,
)
from custom_components.alexa_media.services import AlexaMediaServices

EMAIL = "test@example.com"
OTHER_EMAIL = "other@example.com"
SETTINGS = {
    "public_url": "",
    "include_devices": "Kitchen",
    "exclude_devices": "Garage",
    "scan_interval": 90,
    "queue_delay": 0.0,
    "extended_entity_discovery": False,
    "debug": False,
}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "state",
    [
        ConfigEntryState.LOADED,
        ConfigEntryState.SETUP_RETRY,
        ConfigEntryState.SETUP_ERROR,
        ConfigEntryState.SETUP_IN_PROGRESS,
        ConfigEntryState.NOT_LOADED,
    ],
)
@pytest.mark.parametrize("targeted", [False, True])
async def test_registered_force_logout_allows_recovery(state, targeted):
    """The registered service can recover accounts outside LOADED state."""
    hass = MagicMock()
    login = MagicMock(email=EMAIL)
    other_login = MagicMock(email=OTHER_EMAIL)
    hass.data = {
        DATA_ALEXAMEDIA: {
            "accounts": {
                EMAIL: {
                    "login_obj": login,
                    "config_entry": MagicMock(state=state),
                    "relogin_unsubs": (MagicMock(),),
                },
                OTHER_EMAIL: {
                    "login_obj": other_login,
                    "config_entry": MagicMock(state=ConfigEntryState.LOADED),
                    "relogin_unsubs": (MagicMock(),),
                },
                "incomplete@example.com": {},
            }
        }
    }
    services = AlexaMediaServices(hass)
    await services.register()
    registration = next(
        call
        for call in hass.services.async_register.call_args_list
        if call.args[:2] == (DOMAIN, "force_logout")
    )
    handler = registration.args[2]
    data = {"email": [EMAIL]} if targeted else {}
    call = MagicMock(data=registration.kwargs["schema"](data))

    with patch(
        "custom_components.alexa_media.services.report_relogin_required"
    ) as report:
        assert await handler(call) is True

    assert report.call_args_list[0].args == (hass, login, EMAIL)
    assert report.call_count == (1 if targeted else 2)
    if not targeted:
        assert report.call_args_list[1].args == (hass, other_login, OTHER_EMAIL)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "accounts",
    [
        {},
        {EMAIL: {}},
        {EMAIL: {"login_obj": None}},
        {EMAIL: {"login_obj": MagicMock()}},
    ],
)
async def test_force_logout_without_login_raises(accounts):
    """An absent login or handler produces a service error, not a false success."""
    hass = MagicMock(data={DATA_ALEXAMEDIA: {"accounts": accounts}})
    with pytest.raises(ServiceValidationError):
        await AlexaMediaServices(hass).force_logout(MagicMock(data={}))


@pytest.mark.asyncio
async def test_force_logout_validates_all_targets_before_reporting():
    """A mixed valid/invalid request must not partially log out accounts."""
    hass = MagicMock(
        data={
            DATA_ALEXAMEDIA: {
                "accounts": {
                    EMAIL: {
                        "login_obj": MagicMock(),
                        "relogin_unsubs": (MagicMock(),),
                    }
                }
            }
        }
    )
    services = AlexaMediaServices(hass)
    with patch(
        "custom_components.alexa_media.services.report_relogin_required"
    ) as report:
        with pytest.raises(ServiceValidationError):
            await services.force_logout(MagicMock(data={"email": [EMAIL, OTHER_EMAIL]}))
    report.assert_not_called()


@pytest.mark.asyncio
async def test_last_called_still_requires_loaded_account():
    """The recovery exception must not relax ordinary account service checks."""
    callback = AsyncMock()
    hass = MagicMock(
        data={
            DATA_ALEXAMEDIA: {
                "accounts": {
                    EMAIL: {
                        "login_obj": MagicMock(email=EMAIL),
                        "config_entry": MagicMock(state=ConfigEntryState.SETUP_RETRY),
                    }
                }
            }
        }
    )
    services = AlexaMediaServices(hass, functions={"update_last_called": callback})
    with pytest.raises(ServiceValidationError):
        await services.last_call_handler(MagicMock(data={"email": [EMAIL]}))
    callback.assert_not_awaited()


def _reauth_flow(data, options):
    """Build a reauth flow with an existing entry and successful login."""
    entry = MagicMock(
        entry_id="entry-id",
        unique_id=f"{EMAIL} - amazon.com",
        data=data,
        options=options,
    )
    flow = AlexaMediaFlowHandler()
    flow.hass = MagicMock()
    flow.hass.data = {DATA_ALEXAMEDIA: {"accounts": {}, "config_flows": {}}}
    flow.hass.config_entries.async_get_entry.return_value = entry
    flow.hass.config_entries.async_entries.return_value = [entry]
    flow.hass.config_entries.async_reload = AsyncMock()
    flow.context = {"entry_id": entry.entry_id}
    flow.login = MagicMock(email=EMAIL, url="amazon.com")
    flow.login.status = {"login_successful": True}
    flow.login.close = AsyncMock()
    flow.login.stats = {"login_timestamp": datetime.now()}
    flow.async_show_form = MagicMock(side_effect=lambda **kw: {"type": "form", **kw})
    flow.async_abort = MagicMock(side_effect=lambda **kw: {"type": "abort", **kw})
    return flow, entry


@pytest.mark.asyncio
@pytest.mark.parametrize("options", [{}, {"debug": False}, {**SETTINGS, "future": 7}])
async def test_reauth_shows_effective_options_and_saves_edits(options):
    """Reauth reconciles legacy, partial and full options without stale copies."""
    legacy = {**SETTINGS, "debug": True, "public_url": "https://old.example/"}
    data = {"email": EMAIL, "url": "amazon.com", "retained": 42, **legacy}
    flow, entry = _reauth_flow(data, options)

    result = await flow.async_step_reauth(dict(data))
    assert result["type"] == "form"
    form_defaults = result["data_schema"](
        {
            "password": "example",
            "hass_url": "http://ha.example",
        }  # nosec B105: dummy form input
    )
    for key in CONFIG_ENTRY_OPTION_KEYS:
        assert form_defaults[key] == options.get(key, legacy[key])

    # Include empty/False/zero values: they are deliberate edits, not missing keys.
    flow._save_user_input_to_config(dict(SETTINGS))
    with patch(
        "custom_components.alexa_media.config_flow.async_dismiss_persistent_notification"
    ):
        result = await flow._test_login()

    assert result == {"type": "abort", "reason": "reauth_successful"}
    updated = flow.hass.config_entries.async_update_entry.call_args.kwargs
    assert updated["options"] == {**options, **SETTINGS}
    assert updated["data"]["retained"] == 42
    assert updated["data"]["email"] == EMAIL
    assert "oauth" in updated["data"]
    assert not set(CONFIG_ENTRY_OPTION_KEYS).intersection(updated["data"])
    flow.hass.config_entries.async_reload.assert_awaited_once_with(entry.entry_id)
    entry.data, entry.options = updated["data"], updated["options"]
    for key, value in SETTINGS.items():
        assert config_entry_option(entry, key) == value


@pytest.mark.asyncio
async def test_credentials_only_reauth_migrates_legacy_without_overwriting_options():
    """Missing flow settings preserve options, migrate legacy data and keep extras."""
    flow, entry = _reauth_flow(
        {"email": EMAIL, **SETTINGS, "debug": True}, {"debug": False, "future": 7}
    )
    flow.reauth_entry = entry
    flow.config = {"email": EMAIL}
    with patch(
        "custom_components.alexa_media.config_flow.async_dismiss_persistent_notification"
    ):
        await flow._test_login()

    updated = flow.hass.config_entries.async_update_entry.call_args.kwargs
    assert updated["options"] == {**SETTINGS, "future": 7}
    assert not set(CONFIG_ENTRY_OPTION_KEYS).intersection(updated["data"])


@pytest.mark.asyncio
@pytest.mark.parametrize("cleared", [False, True])
async def test_reauth_otp_secret_removal_is_respected(cleared):
    """A cleared OTP secret is not restored; an untouched one is kept."""
    flow, entry = _reauth_flow(
        {"email": EMAIL, CONF_OTPSECRET: "OLD-SECRET", "debug": True},
        {"debug": False},
    )
    flow.reauth_entry = entry
    flow.config = {"email": EMAIL, CONF_OTPSECRET: "OLD-SECRET"}
    if cleared:
        flow._save_user_input_to_config({CONF_OTPSECRET: "   "})
    with patch(
        "custom_components.alexa_media.config_flow.async_dismiss_persistent_notification"
    ):
        await flow._test_login()

    updated = flow.hass.config_entries.async_update_entry.call_args.kwargs
    if cleared:
        assert CONF_OTPSECRET not in updated["data"]
        assert CONF_OTPSECRET not in updated["options"]
    else:
        assert updated["data"][CONF_OTPSECRET] == "OLD-SECRET"


@pytest.mark.asyncio
async def test_reauth_payload_uses_effective_settings():
    """Starting reauth reads options after the settings leave entry data."""
    hass = MagicMock()
    hass.data = {DATA_ALEXAMEDIA: {"config_flows": {}}}
    login = MagicMock(email=EMAIL, url="https://alexa.amazon.com")
    login.status = {"login_successful": False}
    login.stats = {"login_timestamp": datetime(1, 1, 1), "api_calls": 0}
    entry = MagicMock(
        data={
            "email": EMAIL,
            "password": "secret",  # noqa: S105  # nosec B105
            "url": "amazon.com",
        },
        options={
            "debug": True,
            "include_devices": "Kitchen",
            "exclude_devices": "Garage",
            "scan_interval": 90,
        },
    )
    entry.async_get_active_flows.return_value = iter([MagicMock()])

    with patch("custom_components.alexa_media.async_create_persistent_notification"):
        assert await check_login_status(hass, entry, login) is False

    payload = entry.async_start_reauth.call_args.kwargs["data"]
    assert payload["email"] == EMAIL
    assert payload["debug"] is True
    assert payload["include_devices"] == "Kitchen"
    assert payload["exclude_devices"] == "Garage"
    assert payload["scan_interval"] == 90


@pytest.mark.asyncio
async def test_failed_reauth_does_not_write_data_or_options():
    """Authentication failure must not persist settings from the reauth form."""
    flow, entry = _reauth_flow({"email": EMAIL, "debug": True}, {"debug": False})
    flow.reauth_entry = entry
    flow.config = {"email": EMAIL, "debug": True}
    flow.login.status = {"login_failed": True}
    await flow._test_login()
    flow.hass.config_entries.async_update_entry.assert_not_called()
    flow.hass.config_entries.async_reload.assert_not_awaited()


@pytest.mark.asyncio
async def test_options_form_uses_precedence_and_returns_normalized_settings():
    """The options path reads options first and returns normalized settings only."""
    entry = MagicMock(
        entry_id="entry-id",
        data={"email": EMAIL, **SETTINGS, "debug": True},
        options={"debug": False, "include_devices": "Office"},
    )
    flow = OptionsFlowHandler(entry)
    flow.hass = MagicMock()
    flow.handler = entry.entry_id
    flow._config_entry = entry
    flow.hass.config_entries.async_get_known_entry.return_value = entry
    flow.async_show_form = MagicMock(side_effect=lambda **kw: {"type": "form", **kw})
    flow.async_create_entry = MagicMock(
        side_effect=lambda **kw: {"type": "create_entry", **kw}
    )

    form = await flow.async_step_init()
    defaults = form["data_schema"]({})
    assert defaults == {**SETTINGS, "include_devices": "Office"}
    result = await flow.async_step_init(
        {
            **defaults,
            "public_url": "https://new.example",
            "include_devices": " Kitchen ",
        }
    )
    assert result["data"] == {
        **SETTINGS,
        "include_devices": "Kitchen",
        "public_url": "https://new.example/",
    }
    flow.hass.config_entries.async_update_entry.assert_not_called()
    assert entry.data["email"] == EMAIL
    assert entry.data["debug"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "platform",
    [
        "alarm_control_panel",
        "binary_sensor",
        "button",
        "light",
        "media_player",
        "number",
        "select",
        "sensor",
        "switch",
    ],
)
async def test_platform_setup_receives_effective_settings(platform):
    """Legacy setup adapters retain filters/options after migration out of data."""
    credential = object()
    data = {"email": EMAIL, "password": credential, "debug": True, "retained": 42}
    # Unknown option keys must not replace credentials or account identity.
    options = {**SETTINGS, "email": OTHER_EMAIL, "password": object()}
    entry = MagicMock(data=data, options=options)
    hass = MagicMock(data={DATA_ALEXAMEDIA: {"accounts": {EMAIL: {"entities": {}}}}})
    add_entities = MagicMock()
    module = import_module(f"custom_components.alexa_media.{platform}")
    context = (
        patch.object(module, "DEPENDENT_ALEXA_COMPONENTS", [])
        if platform == "media_player"
        else nullcontext()
    )
    with (
        context,
        patch.object(
            module, "async_setup_platform", AsyncMock(return_value=True)
        ) as setup,
    ):
        assert await module.async_setup_entry(hass, entry, add_entities)

    setup.assert_awaited_once_with(
        hass, {**data, **SETTINGS}, add_entities, discovery_info=None
    )
    assert entry.data == data
    assert entry.options == options


def test_effective_config_keeps_legacy_fallback_and_does_not_mutate_entry():
    """Combining settings preserves legacy values and returns an independent dict."""
    entry = MagicMock(
        data={"email": EMAIL, "include_devices": "Kitchen"}, options={"debug": False}
    )
    config = config_entry_config(entry)
    assert config == {"email": EMAIL, "include_devices": "Kitchen", "debug": False}
    config["include_devices"] = "Office"
    assert entry.data["include_devices"] == "Kitchen"


@pytest.mark.asyncio
async def test_force_logout_does_not_report_success_without_an_event():
    """The service cannot claim recovery when the handler was not notified."""
    hass = MagicMock(
        data={
            DATA_ALEXAMEDIA: {
                "accounts": {
                    EMAIL: {
                        "login_obj": MagicMock(),
                        "relogin_unsubs": (MagicMock(),),
                    }
                }
            }
        }
    )
    services = AlexaMediaServices(hass)
    with patch(
        "custom_components.alexa_media.services.report_relogin_required",
        return_value=False,
    ):
        assert await services.force_logout(MagicMock(data={})) is False
