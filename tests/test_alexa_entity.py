"""Test the alexa_entity module utility functions."""

import pytest

from custom_components.alexa_media.alexa_entity import (
    has_capability,
    is_hue_v1,
    is_known_ha_bridge,
    is_local,
    is_skill,
    parse_availability_from_coordinator,
)


class TestHasCapability:
    """Test the has_capability function."""

    def test_has_capability_with_valid_interface(self):
        """Test has_capability returns True when interface and property match."""
        appliance = {
            "capabilities": [
                {
                    "interfaceName": "Alexa.PowerController",
                    "properties": {
                        "retrievable": True,
                        "proactivelyReported": False,
                        "supported": [{"name": "powerState"}],
                    },
                }
            ]
        }

        assert has_capability(appliance, "Alexa.PowerController", "powerState")

    def test_has_capability_with_proactively_reported(self):
        """Test has_capability returns True when proactivelyReported is True."""
        appliance = {
            "capabilities": [
                {
                    "interfaceName": "Alexa.BrightnessController",
                    "properties": {
                        "retrievable": False,
                        "proactivelyReported": True,
                        "supported": [{"name": "brightness"}],
                    },
                }
            ]
        }

        assert has_capability(appliance, "Alexa.BrightnessController", "brightness")

    def test_has_capability_no_matching_interface(self):
        """Test has_capability returns False when interface doesn't match."""
        appliance = {
            "capabilities": [
                {
                    "interfaceName": "Alexa.PowerController",
                    "properties": {
                        "retrievable": True,
                        "proactivelyReported": False,
                        "supported": [{"name": "powerState"}],
                    },
                }
            ]
        }

        assert not has_capability(appliance, "Alexa.BrightnessController", "brightness")

    def test_has_capability_no_matching_property(self):
        """Test has_capability returns False when property doesn't match."""
        appliance = {
            "capabilities": [
                {
                    "interfaceName": "Alexa.PowerController",
                    "properties": {
                        "retrievable": True,
                        "proactivelyReported": False,
                        "supported": [{"name": "powerState"}],
                    },
                }
            ]
        }

        assert not has_capability(appliance, "Alexa.PowerController", "brightness")

    def test_has_capability_no_properties(self):
        """Test has_capability returns False when properties are missing."""
        appliance = {"capabilities": [{"interfaceName": "Alexa.PowerController"}]}

        assert not has_capability(appliance, "Alexa.PowerController", "powerState")

    def test_has_capability_not_retrievable_or_reported(self):
        """Test has_capability returns False when not retrievable or proactively reported."""
        appliance = {
            "capabilities": [
                {
                    "interfaceName": "Alexa.PowerController",
                    "properties": {
                        "retrievable": False,
                        "proactivelyReported": False,
                        "supported": [{"name": "powerState"}],
                    },
                }
            ]
        }

        assert not has_capability(appliance, "Alexa.PowerController", "powerState")

    def test_has_capability_empty_capabilities(self):
        """Test has_capability returns False when capabilities list is empty."""
        appliance = {"capabilities": []}

        assert not has_capability(appliance, "Alexa.PowerController", "powerState")

    def test_has_capability_multiple_properties(self):
        """Test has_capability with multiple supported properties."""
        appliance = {
            "capabilities": [
                {
                    "interfaceName": "Alexa.ColorController",
                    "properties": {
                        "retrievable": True,
                        "proactivelyReported": False,
                        "supported": [
                            {"name": "color"},
                            {"name": "colorTemperatureInKelvin"},
                        ],
                    },
                }
            ]
        }

        assert has_capability(appliance, "Alexa.ColorController", "color")
        assert has_capability(
            appliance, "Alexa.ColorController", "colorTemperatureInKelvin"
        )
        assert not has_capability(appliance, "Alexa.ColorController", "brightness")


class TestIsHueV1:
    """Test the is_hue_v1 function."""

    def test_is_hue_v1_true(self):
        """Test is_hue_v1 returns True for Royal Philips Electronics."""
        appliance = {"manufacturerName": "Royal Philips Electronics"}
        assert is_hue_v1(appliance)

    def test_is_hue_v1_false_different_manufacturer(self):
        """Test is_hue_v1 returns False for different manufacturer."""
        appliance = {"manufacturerName": "Amazon"}
        assert not is_hue_v1(appliance)

    def test_is_hue_v1_false_no_manufacturer(self):
        """Test is_hue_v1 returns False when manufacturerName is missing."""
        appliance = {}
        assert not is_hue_v1(appliance)

    def test_is_hue_v1_false_none_manufacturer(self):
        """Test is_hue_v1 returns False when manufacturerName is None."""
        appliance = {"manufacturerName": None}
        assert not is_hue_v1(appliance)


class TestIsSkill:
    """Test the is_skill function."""

    def test_is_skill_true(self):
        """Test is_skill returns True when namespace is SKILL."""
        appliance = {"driverIdentity": {"namespace": "SKILL"}}
        assert is_skill(appliance)

    def test_is_skill_false_different_namespace(self):
        """Test is_skill returns False for different namespace."""
        appliance = {"driverIdentity": {"namespace": "OTHER"}}
        assert not is_skill(appliance)

    def test_is_skill_false_no_driver_identity(self):
        """Test is_skill returns False when driverIdentity is missing."""
        appliance = {}
        assert not is_skill(appliance)

    def test_is_skill_false_no_namespace(self):
        """Test is_skill returns False when namespace is missing."""
        appliance = {"driverIdentity": {}}
        assert not is_skill(appliance)

    def test_is_skill_false_empty_namespace(self):
        """Test is_skill returns False when namespace is empty."""
        appliance = {"driverIdentity": {"namespace": ""}}
        assert not is_skill(appliance)


class TestIsKnownHaBridge:
    """Test the is_known_ha_bridge function."""

    def test_is_known_ha_bridge_none(self):
        """Test is_known_ha_bridge returns False for None input."""
        assert not is_known_ha_bridge(None)

    def test_is_known_ha_bridge_t0bst4r(self):
        """Test is_known_ha_bridge returns True for t0bst4r manufacturer."""
        appliance = {"manufacturerName": "t0bst4r"}
        assert is_known_ha_bridge(appliance)

    def test_is_known_ha_bridge_matterbridge(self):
        """Test is_known_ha_bridge returns True for Matterbridge manufacturer."""
        appliance = {"manufacturerName": "Matterbridge"}
        assert is_known_ha_bridge(appliance)

    def test_is_known_ha_bridge_false(self):
        """Test is_known_ha_bridge returns False for unknown manufacturer."""
        appliance = {"manufacturerName": "Amazon"}
        assert not is_known_ha_bridge(appliance)

    def test_is_known_ha_bridge_no_manufacturer(self):
        """Test is_known_ha_bridge returns False when manufacturerName is missing."""
        appliance = {}
        assert not is_known_ha_bridge(appliance)


class TestIsLocal:
    """Test the is_local function."""

    def test_is_local_with_connected_via(self):
        """Test is_local returns True when connectedVia is present."""
        appliance = {"connectedVia": "Echo Dot"}
        assert is_local(appliance)

    def test_is_local_voice_enabled_not_skill(self):
        """Test is_local returns True for voice enabled device that's not a skill."""
        appliance = {
            "applianceTypes": ["ALEXA_VOICE_ENABLED"],
            "driverIdentity": {"namespace": "OTHER"},
        }
        assert is_local(appliance)

    def test_is_local_voice_enabled_skill(self):
        """Test is_local returns False for voice enabled device that's a skill."""
        appliance = {
            "applianceTypes": ["ALEXA_VOICE_ENABLED"],
            "driverIdentity": {"namespace": "SKILL"},
        }
        assert not is_local(appliance)

    def test_is_local_ledvance_not_skill(self):
        """Test is_local returns True for Ledvance device that's not a skill."""
        appliance = {
            "manufacturerName": "Ledvance",
            "driverIdentity": {"namespace": "OTHER"},
        }
        assert is_local(appliance)

    def test_is_local_sengled_not_skill(self):
        """Test is_local returns True for Sengled device that's not a skill."""
        appliance = {
            "manufacturerName": "Sengled",
            "driverIdentity": {"namespace": "OTHER"},
        }
        assert is_local(appliance)

    def test_is_local_amazon_not_skill(self):
        """Test is_local returns True for Amazon device that's not a skill."""
        appliance = {
            "manufacturerName": "Amazon",
            "driverIdentity": {"namespace": "OTHER"},
        }
        assert is_local(appliance)

    def test_is_local_ledvance_skill(self):
        """Test is_local returns False for Ledvance device that's a skill."""
        appliance = {
            "manufacturerName": "Ledvance",
            "driverIdentity": {"namespace": "SKILL"},
        }
        assert not is_local(appliance)

    def test_is_local_unknown_manufacturer(self):
        """Test is_local returns False for unknown manufacturer without other flags."""
        appliance = {"manufacturerName": "Unknown"}
        # This should return False as the final zigbee pattern check will fail
        result = is_local(appliance)
        assert result is False

    def test_is_local_empty_appliance(self):
        """Test is_local returns False for empty appliance."""
        appliance = {}
        result = is_local(appliance)
        assert result is False

    def test_is_local_zigbee_pattern_match(self):
        """Test is_local returns True for valid zigbee pattern."""
        appliance = {"applianceId": "AAA_SonarCloudService_AB:CD:EF:12:34:56:78:90"}
        result = is_local(appliance)
        assert result is True

    def test_is_local_zigbee_pattern_no_match(self):
        """Test is_local returns False for invalid zigbee pattern."""
        appliance = {"applianceId": "invalid_pattern"}
        result = is_local(appliance)
        assert result is False

    def test_is_local_third_party_smartlife_skill(self):
        """Test is_local returns True for SmartLife skill-connected device."""
        appliance = {
            "manufacturerName": "SmartLife",
            "driverIdentity": {"namespace": "SKILL"},
        }
        assert is_local(appliance)

    def test_is_local_third_party_smartthings_skill(self):
        """Test is_local returns True for SmartThings skill-connected device."""
        appliance = {
            "manufacturerName": "SmartThings",
            "driverIdentity": {"namespace": "SKILL"},
        }
        assert is_local(appliance)

    def test_is_local_third_party_tuya_skill(self):
        """Test is_local returns True for Tuya skill-connected device."""
        appliance = {
            "manufacturerName": "Tuya",
            "driverIdentity": {"namespace": "SKILL"},
        }
        assert is_local(appliance)

    def test_is_local_loopback_home_assistant(self):
        """Test is_local returns False for Home Assistant bridge loopback."""
        appliance = {
            "manufacturerName": "Home Assistant",
            "driverIdentity": {"namespace": "SKILL"},
        }
        assert not is_local(appliance)

    def test_is_local_loopback_nodered(self):
        """Test is_local returns False for Node-RED bridge loopback."""
        appliance = {
            "manufacturerName": "Node-RED",
            "driverIdentity": {"namespace": "SKILL"},
        }
        assert not is_local(appliance)

    def test_is_local_loopback_matterbridge(self):
        """Test is_local returns False for Matterbridge loopback."""
        appliance = {
            "manufacturerName": "Matterbridge",
            "driverIdentity": {"namespace": "SKILL"},
        }
        assert not is_local(appliance)


class TestParseAvailabilityFromCoordinator:
    """Test the parse_availability_from_coordinator function."""

    class MockCoordinator:
        """Mock DataUpdateCoordinator for availability tests."""

        def __init__(self, data=None, last_update_success=True):
            self.data = data
            self.last_update_success = last_update_success

    def test_coordinator_failed_update(self):
        """Test returns False when coordinator last_update_success is False."""
        coord = self.MockCoordinator(data={"dev1": []}, last_update_success=False)
        assert parse_availability_from_coordinator(coord, "dev1") is False

    def test_coordinator_missing_entity_assumed_available(self):
        """Test returns True (assumed available) when entity is not in coordinator data."""
        coord = self.MockCoordinator(data={"dev1": []})
        assert parse_availability_from_coordinator(coord, "dev2") is True

    def test_coordinator_empty_data(self):
        """Test returns False when coordinator data is None."""
        coord = self.MockCoordinator(data=None)
        assert parse_availability_from_coordinator(coord, "dev1") is False

    def test_entity_with_empty_states(self):
        """Test returns False when entity states list is empty."""
        coord = self.MockCoordinator(data={"dev1": []})
        assert parse_availability_from_coordinator(coord, "dev1") is False

    def test_entity_online_ok(self):
        """Test returns True when EndpointHealth connectivity is OK."""
        coord = self.MockCoordinator(
            data={
                "dev1": [
                    {
                        "namespace": "Alexa.EndpointHealth",
                        "name": "connectivity",
                        "value": {"value": "OK"},
                    },
                    {
                        "namespace": "Alexa.PowerController",
                        "name": "powerState",
                        "value": "ON",
                    },
                ]
            }
        )
        assert parse_availability_from_coordinator(coord, "dev1") is True

    def test_entity_unreachable_endpoint_health(self):
        """Test returns False when EndpointHealth connectivity is UNREACHABLE."""
        coord = self.MockCoordinator(
            data={
                "dev1": [
                    {
                        "namespace": "Alexa.EndpointHealth",
                        "name": "connectivity",
                        "value": {"value": "UNREACHABLE"},
                    }
                ]
            }
        )
        assert parse_availability_from_coordinator(coord, "dev1") is False

    def test_entity_with_hard_error_codes(self):
        """Test returns False when hard unrecoverable error code is present."""
        for error_code in (
            "ENDPOINT_UNREACHABLE",
            "TransientAccessTokenRetrievalException",
            "NO_SUCH_ENDPOINT",
            "DEVICE_DELETED",
            "INVALID_ACCESS_TOKEN_EXCEPTION",
            "DEVICE_OFFLINE",
            "UNREACHABLE",
        ):
            coord = self.MockCoordinator(
                data={
                    "dev1": [
                        {
                            "namespace": "Alexa.EndpointHealth",
                            "name": "connectivity",
                            "value": {"value": "UNREACHABLE"},
                            "error": error_code,
                        }
                    ]
                }
            )
            assert parse_availability_from_coordinator(coord, "dev1") is False
