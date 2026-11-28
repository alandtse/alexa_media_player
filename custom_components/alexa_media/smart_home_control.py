"""Account-scoped GraphQL control for smart-home entities."""

from alexapy import AlexaAPI
from homeassistant.exceptions import HomeAssistantError

from .const import DATA_ALEXAMEDIA


async def async_control_gql(entity, power_on, **kwargs):
    """Send a GraphQL command and reconcile it through coordinator state.

    Return False when the installed AlexaPy predates the GraphQL API.
    """
    setter = getattr(AlexaAPI, "set_light_state_gql", None)
    if not callable(setter):
        return False
    account = entity.hass.data[DATA_ALEXAMEDIA]["accounts"].get(entity._login.email)
    snapshot = account and account.get("control_endpoint_snapshot")
    if (
        not snapshot
        or snapshot[0] is not entity._login
        or account.get("login_obj") is not entity._login
    ):
        raise HomeAssistantError("Alexa GraphQL endpoint discovery is unavailable")
    try:
        accepted = await setter(
            entity._login,
            entity.alexa_entity_id,
            power_on,
            endpoints=snapshot[1],
            **kwargs,
        )
    finally:
        debouncer = account.get("confirm_refresh_debouncer")
        if debouncer:
            await debouncer.async_call()
        else:
            await entity.coordinator.async_request_refresh()
    if accepted is not True:
        raise HomeAssistantError("Alexa did not confirm every smart-home operation")
    return True
