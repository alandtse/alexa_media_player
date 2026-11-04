"""Instance-aware AQM LED control through Alexa's endpoint feature API."""

from alexapy import AlexaAPI
from homeassistant.exceptions import HomeAssistantError

_ENDPOINT_QUERY = """
query AQMEndpoints {
  endpoints(endpointsQueryParams: {paginationParams: {disablePagination: true}}) {
    items { id legacyAppliance { entityId } }
  }
}
"""

# The legacy entityId used for state polling differs from the endpoint id
# required for control.
_SET_FEATURE = """
mutation setEndpointFeatures($setEndpointFeaturesInput: SetEndpointFeaturesInput!) {
  setEndpointFeatures(setEndpointFeaturesInput: $setEndpointFeaturesInput) {
    featureControlResponses { endpointId featureName instance featureOperationName code }
    errors { code message }
  }
}
"""


async def _graphql(login, query, variables=None):
    """Send a GraphQL request using AMP's authenticated Alexa session."""
    response = await AlexaAPI._static_request(  # pylint: disable=protected-access
        "post",
        login,
        "/nexus/v1/graphql",
        data={"query": query, "variables": variables or {}},
    )
    if response is None:
        raise HomeAssistantError("No response from Alexa LED control")
    body = await response.json(content_type=None)
    if (
        not isinstance(body, dict)
        or body.get("errors")
        or not isinstance(body.get("data"), dict)
    ):
        raise HomeAssistantError("Alexa LED control returned an invalid response")
    return body["data"]


async def resolve_endpoint_id(login, entity_id):
    """Resolve an endpoint without assuming a relationship between Alexa ids."""
    data = await _graphql(login, _ENDPOINT_QUERY)
    endpoints = data.get("endpoints")
    items = endpoints.get("items") if isinstance(endpoints, dict) else None
    if not isinstance(items, list):
        raise HomeAssistantError("Alexa returned an invalid endpoint list")
    for endpoint in items:
        if not isinstance(endpoint, dict):
            continue
        legacy = endpoint.get("legacyAppliance")
        if isinstance(legacy, dict) and legacy.get("entityId") == entity_id:
            endpoint_id = endpoint.get("id")
            if isinstance(endpoint_id, str) and endpoint_id:
                return endpoint_id
    raise HomeAssistantError("Alexa endpoint for AQM LED indicator was not found")


async def set_led_state(login, endpoint_id, instance, power_on):
    """Set only the discovered toggle; require explicit success from Amazon."""
    operation = "turnOn" if power_on else "turnOff"
    data = await _graphql(
        login,
        _SET_FEATURE,
        {
            "setEndpointFeaturesInput": {
                "featureControlRequests": [
                    {
                        "endpointId": endpoint_id,
                        "featureName": "toggle",
                        "featureOperationName": operation,
                        "instance": instance,
                    }
                ]
            }
        },
    )
    result = data.get("setEndpointFeatures")
    if not isinstance(result, dict) or result.get("errors"):
        raise HomeAssistantError("Alexa rejected the LED indicator command")
    responses = result.get("featureControlResponses")
    if not isinstance(responses, list) or len(responses) != 1:
        raise HomeAssistantError("Alexa did not confirm the LED indicator command")
    response = responses[0]
    if not isinstance(response, dict) or any(
        response.get(key) != value
        for key, value in {
            "endpointId": endpoint_id,
            "featureName": "toggle",
            "instance": instance,
            "featureOperationName": operation,
            "code": "SUCCESS",
        }.items()
    ):
        raise HomeAssistantError("Alexa did not confirm the LED indicator command")
