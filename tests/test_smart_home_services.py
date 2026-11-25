"""Tests for the smart-home group and device services."""

from unittest.mock import MagicMock, patch

from alexapy import AlexapyLoginError
from alexapy.errors import AlexapyConnectionError, AlexapyTooManyRequestsError
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import Context, SupportsResponse
from homeassistant.exceptions import (
    HomeAssistantError,
    ServiceValidationError,
    Unauthorized,
    UnknownUser,
)
import pytest
import voluptuous as vol

from custom_components.alexa_media.const import DATA_ALEXAMEDIA, DOMAIN
from custom_components.alexa_media.services import (
    CREATE_SMART_HOME_GROUP_SCHEMA,
    SET_SMART_HOME_DEVICE_ENABLED_SCHEMA,
    SET_SMART_HOME_GROUP_MEMBERS_SCHEMA,
    AlexaMediaServices,
)

EMAIL = "test@example.com"
OTHER_EMAIL = "other@example.com"
GROUP_ID = "amzn1.HomeAutomation.ApplianceGroup.CUSTOMER.GROUP"
ENDPOINT_ID = "amzn1.alexa.endpoint.LAMP"
APPLIANCE_ID = "AAA_SonarCloudService_LAMP"

GROUPS = [
    {
        "groupId": GROUP_ID,
        "name": "Office",
        "type": "SPACE",
        "applianceIds": [APPLIANCE_ID, None],
        "defaults": [],
    },
    {"groupId": "amzn1.HomeAutomation.ApplianceGroup.CUSTOMER.EMPTY", "name": "attic"},
    {"name": "No ID"},
    "not a group",
]
ENDPOINTS = [
    {
        "id": ENDPOINT_ID,
        "legacyAppliance": {"applianceId": APPLIANCE_ID, "friendlyName": "Lamp"},
    },
    # Renamed in the Alexa app: only the endpoint has the current name.
    {
        "id": "amzn1.alexa.endpoint.LOCK",
        "friendlyName": "Front door",
        "legacyAppliance": {"applianceId": "SKILL_LOCK", "friendlyName": "Door lock"},
    },
    {"id": "amzn1.alexa.endpoint.ECHO", "legacyAppliance": None},
    # The legacy query has no endpoint id.
    {"legacyAppliance": {"applianceId": "SKILL_PLUG", "friendlyName": "Desk plug"}},
    {"legacyAppliance": {"friendlyName": "Nothing to address"}},
    "not an endpoint",
]

# service, data, AlexaAPI method, expected arguments after the login
CHANGES = [
    (
        "rename_smart_home_group",
        {"group_id": GROUP_ID, "name": "Study"},
        "rename_appliance_group",
        (GROUP_ID, "Study"),
    ),
    (
        "set_smart_home_group_members",
        {"group_id": GROUP_ID, "appliance_ids": [APPLIANCE_ID]},
        "set_appliance_group_members",
        (GROUP_ID, [APPLIANCE_ID]),
    ),
    (
        "delete_smart_home_group",
        {"group_id": GROUP_ID},
        "delete_appliance_group",
        (GROUP_ID,),
    ),
    (
        "rename_smart_home_device",
        {"endpoint_id": ENDPOINT_ID, "name": "Desk lamp"},
        "set_endpoint_friendly_name",
        (ENDPOINT_ID, "Desk lamp"),
    ),
    (
        "set_smart_home_device_enabled",
        {"endpoint_id": ENDPOINT_ID, "enabled": False},
        "set_endpoint_enabled",
        (ENDPOINT_ID, False),
    ),
    (
        "forget_smart_home_device",
        {"endpoint_id": ENDPOINT_ID},
        "forget_endpoint",
        (ENDPOINT_ID,),
    ),
    ("discover_smart_home_devices", {}, "discover_appliances", ()),
]
DATA = {
    "get_smart_home_groups": {},
    "create_smart_home_group": {"name": "Office"},
    **{service: data for service, data, *_ in CHANGES},
}
SERVICES = list(DATA)


def _account(state=ConfigEntryState.LOADED, email=EMAIL):
    return {
        "config_entry": MagicMock(state=state),
        "login_obj": MagicMock(email=email),
    }


@pytest.fixture
def accounts(hass):
    """Provide one loaded account and register the services."""
    hass.data[DATA_ALEXAMEDIA] = {"accounts": {EMAIL: _account()}}
    return hass.data[DATA_ALEXAMEDIA]["accounts"]


@pytest.fixture
def amazon():
    """Patch AlexaAPI with the signatures of the installed alexapy."""
    with patch("custom_components.alexa_media.services.AlexaAPI", autospec=True) as api:
        api.get_appliance_groups.return_value = GROUPS
        api.get_devices_gql.return_value = ENDPOINTS
        api.create_appliance_group.return_value = {
            "groupId": GROUP_ID,
            "name": "Office",
            "applianceIds": [APPLIANCE_ID],
        }
        for _service, _data, method, _args in CHANGES:
            getattr(api, method).return_value = True
        yield api


@pytest.fixture
async def call(hass, accounts):
    """Return a helper that calls a registered smart-home service."""
    await AlexaMediaServices(hass).register()

    async def _call(service, data=None, *, context=None, response=None):
        if response is None:
            response = service in ("get_smart_home_groups", "create_smart_home_group")
        return await hass.services.async_call(
            DOMAIN,
            service,
            data or {},
            blocking=True,
            context=context,
            return_response=response,
        )

    return _call


async def test_services_are_registered_with_response_support():
    """Only the services that return data declare response support."""
    hass = MagicMock()
    await AlexaMediaServices(hass).register()

    support = {
        call.args[1]: call.kwargs["supports_response"]
        for call in hass.services.async_register.call_args_list
    }
    assert support["get_smart_home_groups"] is SupportsResponse.ONLY
    assert support["create_smart_home_group"] is SupportsResponse.OPTIONAL
    assert support["list_alarms"] is SupportsResponse.ONLY
    for service, *_ in CHANGES:
        assert support[service] is SupportsResponse.NONE


async def test_get_smart_home_groups_maps_groups_to_devices(call, amazon, accounts):
    """The response lists groups and devices with IDs and current names."""
    login = accounts[EMAIL]["login_obj"]

    response = await call("get_smart_home_groups")

    amazon.get_appliance_groups.assert_awaited_once_with(login)
    amazon.get_devices_gql.assert_awaited_once_with(login)
    assert response == {
        "groups": [
            {
                "id": "amzn1.HomeAutomation.ApplianceGroup.CUSTOMER.EMPTY",
                "name": "attic",
                "appliance_ids": [],
            },
            {"id": GROUP_ID, "name": "Office", "appliance_ids": [APPLIANCE_ID]},
        ],
        "devices": [
            {
                "endpoint_id": "amzn1.alexa.endpoint.ECHO",
                "appliance_id": None,
                "name": None,
            },
            {"endpoint_id": None, "appliance_id": "SKILL_PLUG", "name": "Desk plug"},
            {
                "endpoint_id": "amzn1.alexa.endpoint.LOCK",
                "appliance_id": "SKILL_LOCK",
                "name": "Front door",
            },
            {"endpoint_id": ENDPOINT_ID, "appliance_id": APPLIANCE_ID, "name": "Lamp"},
        ],
    }


@pytest.mark.parametrize(
    ("groups", "endpoints"),
    [(None, ENDPOINTS), (GROUPS, None), ({"groups": []}, ENDPOINTS), (GROUPS, "")],
)
async def test_get_smart_home_groups_rejects_missing_or_broken_data(
    call, amazon, groups, endpoints
):
    """A failed or malformed read is an error, not an empty account."""
    amazon.get_appliance_groups.return_value = groups
    amazon.get_devices_gql.return_value = endpoints

    with pytest.raises(HomeAssistantError, match="did not return"):
        await call("get_smart_home_groups")


async def test_create_smart_home_group_returns_new_group(call, amazon, accounts):
    """The new group comes back with the ID the other services take."""
    response = await call(
        "create_smart_home_group",
        {"name": " Office ", "appliance_ids": APPLIANCE_ID},
    )

    amazon.create_appliance_group.assert_awaited_once_with(
        accounts[EMAIL]["login_obj"], "Office", [APPLIANCE_ID]
    )
    assert response == {
        "id": GROUP_ID,
        "name": "Office",
        "appliance_ids": [APPLIANCE_ID],
    }


async def test_create_smart_home_group_works_without_response(call, amazon, accounts):
    """Automations can create an empty group without asking for the response."""
    assert (
        await call("create_smart_home_group", {"name": "Office"}, response=False)
        is None
    )

    amazon.create_appliance_group.assert_awaited_once_with(
        accounts[EMAIL]["login_obj"], "Office", []
    )


@pytest.mark.parametrize("group", [None, {}, {"name": "Office"}, ["Office"]])
async def test_create_smart_home_group_unconfirmed(call, amazon, group):
    """An unconfirmed group warns against a retry that could duplicate it."""
    amazon.create_appliance_group.return_value = group

    with pytest.raises(HomeAssistantError, match="check get_smart_home_groups"):
        await call("create_smart_home_group", {"name": "Office"})


@pytest.mark.parametrize(("service", "data", "method", "args"), CHANGES)
async def test_change_calls_alexa(call, amazon, accounts, service, data, method, args):
    """Each change passes the login and the IDs to AlexaAPI."""
    assert await call(service, data) is None

    getattr(amazon, method).assert_awaited_once_with(
        accounts[EMAIL]["login_obj"], *args
    )


@pytest.mark.parametrize(("service", "data", "method", "args"), CHANGES)
@pytest.mark.parametrize("result", [False, None])
async def test_rejected_change_raises(
    call, amazon, service, data, method, args, result
):
    """A change Alexa did not accept is reported to the caller."""
    getattr(amazon, method).return_value = result

    with pytest.raises(HomeAssistantError, match="Alexa did not") as error:
        await call(service, data)
    assert not isinstance(error.value, ServiceValidationError)
    assert ("get_smart_home_groups" in str(error.value)) is bool(args)


async def test_rename_smart_home_device_rejects_underscore(call, amazon):
    """Names Amazon rejects are refused before a request is sent."""
    with pytest.raises(ServiceValidationError, match="underscore"):
        await call(
            "rename_smart_home_device",
            {"endpoint_id": ENDPOINT_ID, "name": "ha_desk_lamp"},
        )

    amazon.set_endpoint_friendly_name.assert_not_called()


@pytest.mark.parametrize("service", SERVICES)
async def test_email_selects_account(hass, call, amazon, accounts, service):
    """With several accounts, email picks the one the request uses."""
    accounts[OTHER_EMAIL] = _account(email=OTHER_EMAIL)
    data = DATA[service]

    await call(service, {**data, "email": OTHER_EMAIL})

    logins = {
        mock_call.args[0]
        for mock_call in amazon.mock_calls
        if mock_call.args and isinstance(mock_call.args[0], MagicMock)
    }
    assert logins == {accounts[OTHER_EMAIL]["login_obj"]}


@pytest.mark.parametrize("service", SERVICES)
async def test_several_accounts_need_email(call, amazon, accounts, service):
    """Without email, a call never guesses between accounts."""
    accounts[OTHER_EMAIL] = _account(email=OTHER_EMAIL)
    data = DATA[service]

    with pytest.raises(ServiceValidationError, match="set email"):
        await call(service, data)
    assert amazon.mock_calls == []


@pytest.mark.parametrize(
    "email", [OTHER_EMAIL, "unknown@example.com"], ids=["not_loaded", "unknown"]
)
async def test_unavailable_account_is_rejected(call, amazon, accounts, email):
    """An account that is unknown or not loaded is an invalid target."""
    accounts[OTHER_EMAIL] = _account(ConfigEntryState.SETUP_RETRY, OTHER_EMAIL)

    with pytest.raises(ServiceValidationError, match=email):
        await call("discover_smart_home_devices", {"email": email})
    assert amazon.mock_calls == []


async def test_no_loaded_account_is_rejected(call, amazon, accounts):
    """The services explain when no account can be used."""
    accounts[EMAIL] = _account(ConfigEntryState.SETUP_RETRY)

    with pytest.raises(ServiceValidationError, match="No eligible"):
        await call("get_smart_home_groups")
    assert amazon.mock_calls == []


@pytest.mark.parametrize("service", SERVICES)
@pytest.mark.parametrize("caller", ["admin", "user", "unknown", "userless"])
async def test_only_admins_change_the_account(hass, call, amazon, service, caller):
    """Non-admin users cannot read or change the Alexa account."""
    data = DATA[service]
    context = Context(user_id=None if caller == "userless" else "caller")
    user = None if caller == "unknown" else MagicMock(is_admin=caller == "admin")

    with patch.object(hass.auth, "async_get_user", return_value=user):
        if caller in ("admin", "userless"):
            await call(service, data, context=context)
            assert amazon.mock_calls
        else:
            with pytest.raises(Unauthorized if user else UnknownUser) as error:
                await call(service, data, context=context)
            assert error.value.context is context
            assert amazon.mock_calls == []


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (AlexapyConnectionError, "did not respond"),
        (AlexapyTooManyRequestsError, "did not respond"),
        (AlexapyLoginError, "reauthenticate"),
    ],
)
@pytest.mark.parametrize("service", SERVICES)
async def test_alexa_errors_are_reported(
    hass, call, amazon, accounts, service, error, message
):
    """Transport and login errors fail the call; login errors ask for relogin."""
    data = DATA[service]
    for method in (
        "get_appliance_groups",
        "create_appliance_group",
        *(method for _s, _d, method, _a in CHANGES),
    ):
        getattr(amazon, method).side_effect = error

    with (
        patch(
            "custom_components.alexa_media.services.report_relogin_required"
        ) as relogin,
        pytest.raises(HomeAssistantError, match=message) as raised,
    ):
        await call(service, data)

    assert not isinstance(raised.value, ServiceValidationError)
    assert EMAIL not in str(raised.value)
    if error is AlexapyLoginError:
        relogin.assert_called_once_with(hass, accounts[EMAIL]["login_obj"], EMAIL)
    else:
        relogin.assert_not_called()


@pytest.mark.parametrize(
    ("schema", "data"),
    [
        (CREATE_SMART_HOME_GROUP_SCHEMA, {"name": "  "}),
        (CREATE_SMART_HOME_GROUP_SCHEMA, {"name": "Office", "appliance_ids": [""]}),
        (SET_SMART_HOME_GROUP_MEMBERS_SCHEMA, {"group_id": GROUP_ID}),
        (SET_SMART_HOME_DEVICE_ENABLED_SCHEMA, {"endpoint_id": ENDPOINT_ID}),
        (
            SET_SMART_HOME_DEVICE_ENABLED_SCHEMA,
            {"endpoint_id": " ", "enabled": True},
        ),
    ],
)
def test_schemas_reject_invalid_input(schema, data):
    """Empty names and IDs and missing values never reach Alexa."""
    with pytest.raises(vol.Invalid):
        schema(data)


def test_schemas_normalize_input():
    """Single IDs become lists, members can be emptied and booleans are coerced."""
    assert SET_SMART_HOME_GROUP_MEMBERS_SCHEMA(
        {"group_id": GROUP_ID, "appliance_ids": None}
    ) == {"group_id": GROUP_ID, "appliance_ids": []}
    assert SET_SMART_HOME_DEVICE_ENABLED_SCHEMA(
        {"endpoint_id": ENDPOINT_ID, "enabled": "off"}
    ) == {"endpoint_id": ENDPOINT_ID, "enabled": False}
