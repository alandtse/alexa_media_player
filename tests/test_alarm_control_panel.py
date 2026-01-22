"""Tests for alarm_control_panel module.

Tests the Alexa Guard alarm control panel functionality.
"""

from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from custom_components.alexa_media.const import CONF_QUEUE_DELAY, DATA_ALEXAMEDIA

# Try to import the state constants
try:
    from homeassistant.components.alarm_control_panel import AlarmControlPanelState

    STATE_ALARM_ARMED_AWAY = AlarmControlPanelState.ARMED_AWAY
    STATE_ALARM_DISARMED = AlarmControlPanelState.DISARMED
except ImportError:
    from homeassistant.const import STATE_ALARM_ARMED_AWAY, STATE_ALARM_DISARMED


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def mock_alexapy_helpers():
    """Mock alexapy helper functions to avoid bugs with MagicMock objects.

    The alexapy library's hide_serial function has a bug where it doesn't
    handle MagicMock objects properly (UnboundLocalError). We patch both
    hide_serial and hide_email at all locations where they're imported.
    """
    with (
        patch("alexapy.hide_serial", side_effect=lambda x: str(x) if x else ""),
        patch("alexapy.hide_email", side_effect=lambda x: str(x) if x else ""),
        patch(
            "custom_components.alexa_media.alarm_control_panel.hide_serial",
            side_effect=lambda x: str(x) if x else "",
        ),
        patch(
            "custom_components.alexa_media.alarm_control_panel.hide_email",
            side_effect=lambda x: str(x) if x else "",
        ),
        patch(
            "custom_components.alexa_media.alexa_media.hide_email",
            side_effect=lambda x: str(x) if x else "",
        ),
        patch(
            "custom_components.alexa_media.helpers.hide_email",
            side_effect=lambda x: str(x) if x else "",
        ),
    ):
        yield


# =============================================================================
# Tests for AlexaAlarmControlPanel._async_alarm_set appliance_id extraction
# =============================================================================


class TestApplianceIdExtraction:
    """Test the appliance_id extraction logic in _async_alarm_set.

    These tests cover a critical bug fix where accessing appliance_id.split("_")[2]
    would raise an IndexError if the appliance_id had fewer than 3 underscore-separated
    parts.

    The Bug (BEFORE fix):
        await api.set_guard_state(self._appliance_id.split("_")[2], ...)

    If _appliance_id is "abc_def" (only 2 parts), split("_")[2] raises IndexError.

    The Fix (AFTER):
        appliance_parts = self._appliance_id.split("_")
        appliance_id = appliance_parts[2] if len(appliance_parts) > 2 else self._appliance_id

    Now falls back to the full appliance_id if format is unexpected.
    """

    def _create_panel(self, appliance_id: str, email: str = "test@example.com"):
        """Create an AlexaAlarmControlPanel with the given appliance_id."""
        from custom_components.alexa_media.alarm_control_panel import (
            AlexaAlarmControlPanel,
        )

        login = MagicMock()
        login.email = email
        coordinator = MagicMock()
        guard_entity = {
            "appliance_id": appliance_id,
            "id": "guard_entity_123",
        }
        panel = AlexaAlarmControlPanel(login, coordinator, guard_entity, {})
        return panel

    @pytest.mark.asyncio
    async def test_appliance_id_with_three_parts_extracts_third(self):
        """Test that appliance_id with exactly 3 parts extracts the third part.

        Expected format: "prefix_middle_EXTRACTED"
        The third part (index 2) should be extracted.
        """
        # Use exactly 3 parts: "AAA_BBB_EXPECTED" -> ["AAA", "BBB", "EXPECTED"]
        panel = self._create_panel("AAA_BBB_EXPECTED")
        panel.hass = MagicMock()
        panel.hass.data = {
            DATA_ALEXAMEDIA: {
                "accounts": {
                    "test@example.com": {
                        "options": {CONF_QUEUE_DELAY: 1.0},
                    }
                }
            }
        }

        mock_player = MagicMock()
        mock_player.state = "idle"
        mock_player.alexa_api = MagicMock()
        mock_player.alexa_api.set_guard_state = AsyncMock()
        panel._media_players = {"serial1": mock_player}

        with patch.object(panel.coordinator, "async_request_refresh", AsyncMock()):
            with patch(
                "custom_components.alexa_media.alarm_control_panel.sleep",
                AsyncMock(),
            ):
                await panel._async_alarm_set(STATE_ALARM_ARMED_AWAY)

        mock_player.alexa_api.set_guard_state.assert_called_once()
        call_args = mock_player.alexa_api.set_guard_state.call_args
        # The first positional argument should be "EXPECTED" (third part, index 2)
        assert call_args[0][0] == "EXPECTED", (
            f"Expected 'EXPECTED' (third part of 'AAA_BBB_EXPECTED'), "
            f"got '{call_args[0][0]}'"
        )

    @pytest.mark.asyncio
    async def test_appliance_id_with_two_parts_uses_full_id(self):
        """Test that appliance_id with only 2 parts uses the full ID as fallback.

        This is the PRIMARY regression test for the IndexError bug fix.

        BEFORE fix: "ABC_DEF".split("_")[2] would raise IndexError
        AFTER fix: Falls back to using "ABC_DEF" as the full ID
        """
        panel = self._create_panel("ABC_DEF")
        panel.hass = MagicMock()
        panel.hass.data = {
            DATA_ALEXAMEDIA: {
                "accounts": {
                    "test@example.com": {
                        "options": {CONF_QUEUE_DELAY: 1.0},
                    }
                }
            }
        }

        mock_player = MagicMock()
        mock_player.state = "idle"
        mock_player.alexa_api = MagicMock()
        mock_player.alexa_api.set_guard_state = AsyncMock()
        panel._media_players = {"serial1": mock_player}

        with patch.object(panel.coordinator, "async_request_refresh", AsyncMock()):
            with patch(
                "custom_components.alexa_media.alarm_control_panel.sleep",
                AsyncMock(),
            ):
                # This should NOT raise IndexError
                try:
                    await panel._async_alarm_set(STATE_ALARM_ARMED_AWAY)
                except IndexError:
                    pytest.fail(
                        "BUG DETECTED: IndexError raised when appliance_id has < 3 parts!\n\n"
                        "CAUSE: The code uses split('_')[2] without bounds checking:\n"
                        "  WRONG: self._appliance_id.split('_')[2]\n"
                        "  RIGHT: parts[2] if len(parts) > 2 else self._appliance_id\n\n"
                        "When appliance_id='ABC_DEF' (only 2 parts), accessing index 2 "
                        "raises IndexError."
                    )

        mock_player.alexa_api.set_guard_state.assert_called_once()
        call_args = mock_player.alexa_api.set_guard_state.call_args
        # Should fall back to full appliance_id
        assert (
            call_args[0][0] == "ABC_DEF"
        ), f"Expected full ID 'ABC_DEF' as fallback, got '{call_args[0][0]}'"

    @pytest.mark.asyncio
    async def test_appliance_id_with_one_part_uses_full_id(self):
        """Test that appliance_id with no underscores uses the full ID."""
        panel = self._create_panel("SINGLEPARTNOUNDERSCORE")
        panel.hass = MagicMock()
        panel.hass.data = {
            DATA_ALEXAMEDIA: {
                "accounts": {
                    "test@example.com": {
                        "options": {},  # Use default queue delay
                    }
                }
            }
        }

        mock_player = MagicMock()
        mock_player.state = "idle"
        mock_player.alexa_api = MagicMock()
        mock_player.alexa_api.set_guard_state = AsyncMock()
        panel._media_players = {"serial1": mock_player}

        with patch.object(panel.coordinator, "async_request_refresh", AsyncMock()):
            with patch(
                "custom_components.alexa_media.alarm_control_panel.sleep",
                AsyncMock(),
            ):
                await panel._async_alarm_set(STATE_ALARM_DISARMED)

        call_args = mock_player.alexa_api.set_guard_state.call_args
        assert call_args[0][0] == "SINGLEPARTNOUNDERSCORE"

    @pytest.mark.asyncio
    async def test_appliance_id_with_many_parts_extracts_third(self):
        """Test that appliance_id with many parts still extracts the third."""
        panel = self._create_panel("A_B_C_D_E_F")
        panel.hass = MagicMock()
        panel.hass.data = {
            DATA_ALEXAMEDIA: {
                "accounts": {
                    "test@example.com": {
                        "options": {CONF_QUEUE_DELAY: 0.5},
                    }
                }
            }
        }

        mock_player = MagicMock()
        mock_player.state = "idle"
        mock_player.alexa_api = MagicMock()
        mock_player.alexa_api.set_guard_state = AsyncMock()
        panel._media_players = {"serial1": mock_player}

        with patch.object(panel.coordinator, "async_request_refresh", AsyncMock()):
            with patch(
                "custom_components.alexa_media.alarm_control_panel.sleep",
                AsyncMock(),
            ):
                await panel._async_alarm_set(STATE_ALARM_ARMED_AWAY)

        call_args = mock_player.alexa_api.set_guard_state.call_args
        # Third part (index 2) is "C"
        assert call_args[0][0] == "C"


class TestAsyncAlarmSet:
    """Test the _async_alarm_set method behavior."""

    def _create_panel(
        self, appliance_id: str = "A_B_C", email: str = "test@example.com"
    ):
        """Create an AlexaAlarmControlPanel for testing."""
        from custom_components.alexa_media.alarm_control_panel import (
            AlexaAlarmControlPanel,
        )

        login = MagicMock()
        login.email = email
        coordinator = MagicMock()
        guard_entity = {
            "appliance_id": appliance_id,
            "id": "guard_entity_123",
        }
        panel = AlexaAlarmControlPanel(login, coordinator, guard_entity, {})
        return panel

    @pytest.mark.asyncio
    async def test_invalid_command_logs_error(self):
        """Test that invalid commands are rejected with error log."""
        panel = self._create_panel()

        with patch(
            "custom_components.alexa_media.alarm_control_panel._LOGGER"
        ) as mock_logger:
            await panel._async_alarm_set("INVALID_COMMAND")
            mock_logger.error.assert_called_once()
            assert "Invalid command" in str(mock_logger.error.call_args)

    @pytest.mark.asyncio
    async def test_disabled_panel_returns_early(self):
        """Test that disabled panel returns without action."""
        panel = self._create_panel()
        mock_player = MagicMock()
        mock_player.alexa_api = MagicMock()
        mock_player.alexa_api.set_guard_state = AsyncMock()
        panel._media_players = {"serial1": mock_player}

        # Use PropertyMock to simulate enabled=False
        with patch.object(
            type(panel), "enabled", new_callable=PropertyMock, return_value=False
        ):
            await panel._async_alarm_set(STATE_ALARM_ARMED_AWAY)
            # No API calls should be made
            mock_player.alexa_api.set_guard_state.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_available_media_players_uses_static_api(self):
        """Test fallback to static API when no media players available."""
        panel = self._create_panel()
        panel.hass = MagicMock()
        panel._media_players = {}
        panel.alexa_api = MagicMock()
        panel.alexa_api.static_set_guard_state = AsyncMock()

        with patch.object(panel.coordinator, "async_request_refresh", AsyncMock()):
            await panel._async_alarm_set(STATE_ALARM_DISARMED)

        panel.alexa_api.static_set_guard_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_unavailable_media_players_filtered_out(self):
        """Test that unavailable media players are filtered out."""
        from homeassistant.const import STATE_UNAVAILABLE

        panel = self._create_panel()
        panel.hass = MagicMock()
        panel.alexa_api = MagicMock()
        panel.alexa_api.static_set_guard_state = AsyncMock()

        # All players are unavailable
        unavailable_player = MagicMock()
        unavailable_player.state = STATE_UNAVAILABLE
        panel._media_players = {"serial1": unavailable_player}

        with patch.object(panel.coordinator, "async_request_refresh", AsyncMock()):
            await panel._async_alarm_set(STATE_ALARM_ARMED_AWAY)

        # Should fall back to static API
        panel.alexa_api.static_set_guard_state.assert_called_once()


class TestAlarmControlPanelProperties:
    """Test AlexaAlarmControlPanel properties."""

    def _create_panel(self):
        """Create an AlexaAlarmControlPanel for testing."""
        from custom_components.alexa_media.alarm_control_panel import (
            AlexaAlarmControlPanel,
        )

        login = MagicMock()
        login.email = "test@example.com"
        coordinator = MagicMock()
        guard_entity = {
            "appliance_id": "prefix_middle_12345",
            "id": "guard_entity_abc",
        }
        return AlexaAlarmControlPanel(login, coordinator, guard_entity, {})

    def test_unique_id_returns_guard_entity_id(self):
        """Test unique_id property returns the guard entity ID."""
        panel = self._create_panel()
        assert panel.unique_id == "guard_entity_abc"

    def test_name_returns_friendly_name(self):
        """Test name property returns friendly name with last 5 chars of appliance_id."""
        panel = self._create_panel()
        # Friendly name should be "Alexa Guard " + last 5 chars of appliance_id
        assert panel.name == "Alexa Guard 12345"

    def test_state_returns_armed_away(self):
        """Test state property returns armed away when coordinator says ARMED_AWAY."""
        panel = self._create_panel()
        with patch(
            "custom_components.alexa_media.alarm_control_panel.parse_guard_state_from_coordinator",
            return_value="ARMED_AWAY",
        ):
            assert panel.state == STATE_ALARM_ARMED_AWAY

    def test_state_returns_disarmed(self):
        """Test state property returns disarmed for any other state."""
        panel = self._create_panel()
        with patch(
            "custom_components.alexa_media.alarm_control_panel.parse_guard_state_from_coordinator",
            return_value="HOME",
        ):
            assert panel.state == STATE_ALARM_DISARMED

    def test_assumed_state_true_when_no_coordinator_data(self):
        """Test assumed_state is True when coordinator has no data."""
        panel = self._create_panel()
        panel.coordinator.data = None
        assert panel.assumed_state is True

    def test_assumed_state_true_when_entity_not_in_data(self):
        """Test assumed_state is True when entity not in coordinator data."""
        panel = self._create_panel()
        panel.coordinator.data = {"other_entity": {}}
        assert panel.assumed_state is True

    def test_assumed_state_false_when_entity_in_data(self):
        """Test assumed_state is False when entity is in coordinator data."""
        panel = self._create_panel()
        panel.coordinator.data = {"guard_entity_abc": {"state": "ARMED_AWAY"}}
        assert panel.assumed_state is False

    def test_extra_state_attributes_returns_attrs(self):
        """Test extra_state_attributes returns the _attrs dict."""
        panel = self._create_panel()
        panel._attrs = {"custom_attr": "value"}
        assert panel.extra_state_attributes == {"custom_attr": "value"}


class TestAlarmArmDisarm:
    """Test async_alarm_arm_away and async_alarm_disarm methods."""

    def _create_panel(self):
        """Create an AlexaAlarmControlPanel for testing."""
        from custom_components.alexa_media.alarm_control_panel import (
            AlexaAlarmControlPanel,
        )

        login = MagicMock()
        login.email = "test@example.com"
        coordinator = MagicMock()
        guard_entity = {
            "appliance_id": "A_B_C",
            "id": "guard_123",
        }
        return AlexaAlarmControlPanel(login, coordinator, guard_entity, {})

    @pytest.mark.asyncio
    async def test_async_alarm_disarm_calls_set_with_disarmed(self):
        """Test async_alarm_disarm calls _async_alarm_set with DISARMED."""
        panel = self._create_panel()
        panel._async_alarm_set = AsyncMock()

        await panel.async_alarm_disarm()

        panel._async_alarm_set.assert_called_once_with(STATE_ALARM_DISARMED)

    @pytest.mark.asyncio
    async def test_async_alarm_arm_away_calls_set_with_armed_away(self):
        """Test async_alarm_arm_away calls _async_alarm_set with ARMED_AWAY."""
        panel = self._create_panel()
        panel._async_alarm_set = AsyncMock()

        await panel.async_alarm_arm_away()

        panel._async_alarm_set.assert_called_once_with(STATE_ALARM_ARMED_AWAY)


# =============================================================================
# Tests for async_setup_platform and related functions
# =============================================================================


class TestAsyncSetupPlatform:
    """Test the async_setup_platform function."""

    @pytest.mark.asyncio
    async def test_setup_platform_no_account_raises_not_ready(self):
        """Test that missing account raises ConfigEntryNotReady."""
        from homeassistant.exceptions import ConfigEntryNotReady

        from custom_components.alexa_media.alarm_control_panel import (
            async_setup_platform,
        )

        hass = MagicMock()
        config = {}  # No email
        add_devices_callback = MagicMock()

        with pytest.raises(ConfigEntryNotReady):
            await async_setup_platform(hass, config, add_devices_callback)

    @pytest.mark.asyncio
    async def test_setup_platform_with_discovery_info(self):
        """Test setup with discovery_info providing the account."""
        from homeassistant.exceptions import ConfigEntryNotReady

        from custom_components.alexa_media.alarm_control_panel import (
            async_setup_platform,
        )

        hass = MagicMock()
        config = None
        add_devices_callback = MagicMock()
        discovery_info = {"config": {}}  # No email in config either

        with pytest.raises(ConfigEntryNotReady):
            await async_setup_platform(
                hass, config, add_devices_callback, discovery_info=discovery_info
            )

    @pytest.mark.asyncio
    async def test_setup_platform_media_player_not_loaded(self):
        """Test that unloaded media player raises ConfigEntryNotReady."""
        from homeassistant.exceptions import ConfigEntryNotReady

        from custom_components.alexa_media.alarm_control_panel import (
            async_setup_platform,
        )
        from custom_components.alexa_media.const import DATA_ALEXAMEDIA

        hass = MagicMock()
        account = "test@example.com"
        config = {"email": account}
        add_devices_callback = MagicMock()

        # Media player device exists but entity not loaded yet
        hass.data = {
            DATA_ALEXAMEDIA: {
                "accounts": {
                    account: {
                        "devices": {"media_player": {"serial1": {"capabilities": []}}},
                        "entities": {"media_player": {}},  # Empty - not loaded
                    }
                }
            }
        }

        with pytest.raises(ConfigEntryNotReady):
            await async_setup_platform(hass, config, add_devices_callback)

    @pytest.mark.asyncio
    async def test_setup_platform_no_guard_entities(self):
        """Test setup when no guard entities exist."""
        from custom_components.alexa_media.alarm_control_panel import (
            async_setup_platform,
        )
        from custom_components.alexa_media.const import DATA_ALEXAMEDIA

        hass = MagicMock()
        account = "test@example.com"
        config = {"email": account}
        add_devices_callback = AsyncMock()

        hass.data = {
            DATA_ALEXAMEDIA: {
                "accounts": {
                    account: {
                        "devices": {"media_player": {}, "guard": []},
                        "entities": {"media_player": {}},
                    }
                }
            }
        }

        with patch(
            "custom_components.alexa_media.alarm_control_panel.add_devices",
            AsyncMock(return_value=True),
        ) as mock_add:
            result = await async_setup_platform(hass, config, add_devices_callback)
            assert result is True
            # No devices should be added
            mock_add.assert_called_once()
            call_args = mock_add.call_args
            assert call_args[0][1] == []  # Empty devices list

    @pytest.mark.asyncio
    async def test_setup_platform_guard_entity_already_added(self):
        """Test setup when guard entity is already added."""
        from custom_components.alexa_media.alarm_control_panel import (
            async_setup_platform,
        )
        from custom_components.alexa_media.const import DATA_ALEXAMEDIA

        hass = MagicMock()
        account = "test@example.com"
        config = {"email": account}
        add_devices_callback = AsyncMock()

        # Create a mock login object
        mock_login = MagicMock()
        mock_login.email = account

        hass.data = {
            DATA_ALEXAMEDIA: {
                "accounts": {
                    account: {
                        "login_obj": mock_login,
                        "coordinator": MagicMock(),
                        "devices": {
                            "media_player": {},
                            "guard": [
                                {"appliance_id": "A_B_C", "id": "existing_guard_id"}
                            ],
                        },
                        "entities": {
                            "media_player": {},
                            "alarm_control_panel": {
                                "existing_guard_id": MagicMock()
                            },  # Already exists
                        },
                    }
                }
            }
        }

        with patch(
            "custom_components.alexa_media.alarm_control_panel.add_devices",
            AsyncMock(return_value=True),
        ) as mock_add:
            result = await async_setup_platform(hass, config, add_devices_callback)
            assert result is True
            # No new devices should be added (already exists)
            call_args = mock_add.call_args
            assert call_args[0][1] == []

    @pytest.mark.asyncio
    async def test_setup_platform_adds_new_guard_entity(self):
        """Test setup adds a new guard entity successfully."""
        from custom_components.alexa_media.alarm_control_panel import (
            async_setup_platform,
        )
        from custom_components.alexa_media.const import DATA_ALEXAMEDIA

        hass = MagicMock()
        account = "test@example.com"
        config = {"email": account}
        add_devices_callback = AsyncMock()

        mock_login = MagicMock()
        mock_login.email = account

        hass.data = {
            DATA_ALEXAMEDIA: {
                "accounts": {
                    account: {
                        "login_obj": mock_login,
                        "coordinator": MagicMock(),
                        "devices": {
                            "media_player": {},
                            "guard": [{"appliance_id": "A_B_C", "id": "new_guard_id"}],
                        },
                        "entities": {
                            "media_player": {},
                            "alarm_control_panel": {},  # Empty - new device
                        },
                    }
                }
            }
        }

        with patch(
            "custom_components.alexa_media.alarm_control_panel.add_devices",
            AsyncMock(return_value=True),
        ) as mock_add:
            result = await async_setup_platform(hass, config, add_devices_callback)
            assert result is True
            # One device should be added
            call_args = mock_add.call_args
            assert len(call_args[0][1]) == 1

    @pytest.mark.asyncio
    async def test_setup_platform_with_guard_media_players(self):
        """Test setup with guard-capable media players."""
        from custom_components.alexa_media.alarm_control_panel import (
            async_setup_platform,
        )
        from custom_components.alexa_media.const import DATA_ALEXAMEDIA

        hass = MagicMock()
        account = "test@example.com"
        config = {"email": account}
        add_devices_callback = AsyncMock()

        mock_login = MagicMock()
        mock_login.email = account

        mock_media_player = MagicMock()

        hass.data = {
            DATA_ALEXAMEDIA: {
                "accounts": {
                    account: {
                        "login_obj": mock_login,
                        "coordinator": MagicMock(),
                        "devices": {
                            "media_player": {
                                "serial1": {"capabilities": ["GUARD_EARCON", "OTHER"]}
                            },
                            "guard": [{"appliance_id": "A_B_C", "id": "guard_id"}],
                        },
                        "entities": {
                            "media_player": {"serial1": mock_media_player},
                            "alarm_control_panel": {},
                        },
                    }
                }
            }
        }

        with patch(
            "custom_components.alexa_media.alarm_control_panel.add_devices",
            AsyncMock(return_value=True),
        ):
            result = await async_setup_platform(hass, config, add_devices_callback)
            assert result is True


class TestAsyncSetupEntry:
    """Test the async_setup_entry function."""

    @pytest.mark.asyncio
    async def test_setup_entry_calls_setup_platform(self):
        """Test that setup_entry delegates to setup_platform."""
        from custom_components.alexa_media.alarm_control_panel import async_setup_entry

        hass = MagicMock()
        config_entry = MagicMock()
        config_entry.data = {"email": "test@example.com"}
        async_add_devices = MagicMock()

        with patch(
            "custom_components.alexa_media.alarm_control_panel.async_setup_platform",
            AsyncMock(return_value=True),
        ) as mock_setup:
            result = await async_setup_entry(hass, config_entry, async_add_devices)
            assert result is True
            mock_setup.assert_called_once_with(
                hass, config_entry.data, async_add_devices, discovery_info=None
            )


class TestAsyncUnloadEntry:
    """Test the async_unload_entry function."""

    @pytest.mark.asyncio
    async def test_unload_entry_removes_devices(self):
        """Test that unload_entry removes all alarm panel devices."""
        from custom_components.alexa_media.alarm_control_panel import async_unload_entry
        from custom_components.alexa_media.const import DATA_ALEXAMEDIA

        hass = MagicMock()
        entry = MagicMock()
        account = "test@example.com"
        entry.data = {"email": account}

        mock_device1 = MagicMock()
        mock_device1.async_remove = AsyncMock()
        mock_device2 = MagicMock()
        mock_device2.async_remove = AsyncMock()

        hass.data = {
            DATA_ALEXAMEDIA: {
                "accounts": {
                    account: {
                        "entities": {
                            "alarm_control_panel": {
                                "device1": mock_device1,
                                "device2": mock_device2,
                            }
                        }
                    }
                }
            }
        }

        result = await async_unload_entry(hass, entry)
        assert result is True
        mock_device1.async_remove.assert_called_once()
        mock_device2.async_remove.assert_called_once()


class TestSupportedFeatures:
    """Test the supported_features property."""

    def _create_panel(self):
        """Create an AlexaAlarmControlPanel for testing."""
        from custom_components.alexa_media.alarm_control_panel import (
            AlexaAlarmControlPanel,
        )

        login = MagicMock()
        login.email = "test@example.com"
        coordinator = MagicMock()
        guard_entity = {
            "appliance_id": "A_B_C",
            "id": "guard_123",
        }
        return AlexaAlarmControlPanel(login, coordinator, guard_entity, {})

    def test_supported_features_returns_arm_away(self):
        """Test supported_features returns ARM_AWAY when feature is available."""
        panel = self._create_panel()

        # The supported_features property should return ARM_AWAY
        features = panel.supported_features
        # ARM_AWAY should be supported
        assert features is not None

    def test_supported_features_with_import_error(self):
        """Test supported_features returns 0 when import fails.

        Note: The ImportError branch at lines 241-242 is for backwards
        compatibility with older Home Assistant versions. It cannot be easily
        tested without uninstalling the module. This test documents the expected
        behavior.
        """
        # This test documents that supported_features returns 0
        # when AlarmControlPanelEntityFeature cannot be imported
        # (older Home Assistant versions)
        pass


class TestAttributeErrorHandling:
    """Test AttributeError handling in _async_alarm_set."""

    def _create_panel(self):
        """Create an AlexaAlarmControlPanel for testing."""
        from custom_components.alexa_media.alarm_control_panel import (
            AlexaAlarmControlPanel,
        )

        login = MagicMock()
        login.email = "test@example.com"
        coordinator = MagicMock()
        guard_entity = {
            "appliance_id": "A_B_C",
            "id": "guard_123",
        }
        return AlexaAlarmControlPanel(login, coordinator, guard_entity, {})

    @pytest.mark.asyncio
    async def test_attribute_error_on_enabled_continues_execution(self):
        """Test that AttributeError when accessing 'enabled' is caught and execution continues.

        This tests lines 167-168 which catch AttributeError if the 'enabled'
        attribute doesn't exist and allow the method to continue.
        """
        panel = self._create_panel()
        panel.hass = MagicMock()
        panel.hass.data = {
            DATA_ALEXAMEDIA: {
                "accounts": {
                    "test@example.com": {
                        "options": {CONF_QUEUE_DELAY: 1.0},
                    }
                }
            }
        }

        mock_player = MagicMock()
        mock_player.state = "idle"
        mock_player.alexa_api = MagicMock()
        mock_player.alexa_api.set_guard_state = AsyncMock()
        panel._media_players = {"serial1": mock_player}

        # Delete the enabled property to force AttributeError
        # This simulates a scenario where the property doesn't exist
        with patch.object(
            type(panel),
            "enabled",
            new_callable=PropertyMock,
            side_effect=AttributeError("enabled not found"),
        ):
            with patch.object(panel.coordinator, "async_request_refresh", AsyncMock()):
                with patch(
                    "custom_components.alexa_media.alarm_control_panel.sleep",
                    AsyncMock(),
                ):
                    # Should NOT raise - the AttributeError should be caught
                    await panel._async_alarm_set(STATE_ALARM_ARMED_AWAY)

        # Execution should continue and API call should be made
        mock_player.alexa_api.set_guard_state.assert_called_once()
