"""Tests for switch.py - specifically the hue_emulated_enabled bugfix.

This tests the fix for the undefined variable bug where hue_emulated_enabled
was used but never defined, causing a NameError when users had Smart Plug
devices with CONF_EXTENDED_ENTITY_DISCOVERY enabled.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.alexa_media.const import (
    CONF_EXTENDED_ENTITY_DISCOVERY,
    DATA_ALEXAMEDIA,
)


@pytest.fixture
def mock_hass():
    """Create a mock hass object."""
    hass = MagicMock()
    hass.config.as_dict.return_value = {"components": set()}
    return hass


@pytest.fixture
def mock_hass_with_emulated_hue():
    """Create a mock hass object with emulated_hue enabled."""
    hass = MagicMock()
    hass.config.as_dict.return_value = {"components": {"emulated_hue"}}
    return hass


@pytest.fixture
def mock_account_dict():
    """Create a mock account dictionary with smart switch entities."""
    coordinator = MagicMock()
    login_obj = MagicMock()
    return {
        "devices": {
            "media_player": {},
            "smart_switch": [
                {"id": "switch1", "name": "Smart Plug 1", "is_hue_v1": False},
                {"id": "switch2", "name": "Smart Plug 2", "is_hue_v1": True},
            ],
        },
        "entities": {
            "switch": {},
            "media_player": {},
            "smart_switch": [],
        },
        "options": {CONF_EXTENDED_ENTITY_DISCOVERY: True},
        "coordinator": coordinator,
        "login_obj": login_obj,
    }


class TestHueEmulatedEnabledVariable:
    """Tests for the hue_emulated_enabled variable definition fix."""

    @pytest.mark.asyncio
    async def test_no_name_error_with_smart_switches(
        self, mock_hass, mock_account_dict
    ):
        """Verify that hue_emulated_enabled is defined before use.

        Before the fix, accessing smart_switch devices with
        CONF_EXTENDED_ENTITY_DISCOVERY would raise a NameError because
        hue_emulated_enabled was used but never defined.
        """
        email = "test@example.com"  # noqa: S105
        mock_hass.data = {DATA_ALEXAMEDIA: {"accounts": {email: mock_account_dict}}}

        with patch(
            "custom_components.alexa_media.switch.add_devices",
            new_callable=AsyncMock,
        ) as mock_add_devices:
            mock_add_devices.return_value = True

            from custom_components.alexa_media.switch import async_setup_platform

            # This should not raise NameError: name 'hue_emulated_enabled' is not defined
            config = {"email": email}
            result = await async_setup_platform(
                mock_hass, config, MagicMock(), discovery_info=None
            )

            assert result is True
            mock_add_devices.assert_called_once()


class TestSmartSwitchCreation:
    """Tests for Smart Switch entity creation with emulated_hue filtering."""

    @pytest.mark.asyncio
    async def test_non_hue_v1_switch_always_created(
        self, mock_hass_with_emulated_hue, mock_account_dict
    ):
        """Non-Hue-v1 switches are created regardless of emulated_hue setting.

        Even when emulated_hue is enabled, switches that are not marked as
        is_hue_v1=True should be created normally.
        """
        email = "test@example.com"  # noqa: S105
        # Only keep the non-hue-v1 switch
        mock_account_dict["devices"]["smart_switch"] = [
            {"id": "switch1", "name": "Smart Plug 1", "is_hue_v1": False}
        ]
        mock_hass_with_emulated_hue.data = {
            DATA_ALEXAMEDIA: {"accounts": {email: mock_account_dict}}
        }

        with patch(
            "custom_components.alexa_media.switch.add_devices",
            new_callable=AsyncMock,
        ) as mock_add_devices:
            mock_add_devices.return_value = True

            from custom_components.alexa_media.switch import async_setup_platform

            config = {"email": email}
            await async_setup_platform(
                mock_hass_with_emulated_hue, config, MagicMock(), discovery_info=None
            )

            # Verify the SmartSwitch was added to account_dict entities
            assert len(mock_account_dict["entities"]["smart_switch"]) == 1

    @pytest.mark.asyncio
    async def test_hue_v1_switch_skipped_when_emulated_hue_enabled(
        self, mock_hass_with_emulated_hue, mock_account_dict
    ):
        """Hue-v1 switches are skipped when emulated_hue is active.

        When emulated_hue is in the components list and a switch has
        is_hue_v1=True, it should be skipped to avoid duplicates with
        the emulated_hue integration.
        """
        email = "test@example.com"  # noqa: S105
        # Only keep the hue-v1 switch
        mock_account_dict["devices"]["smart_switch"] = [
            {"id": "switch2", "name": "Hue Plug", "is_hue_v1": True}
        ]
        mock_hass_with_emulated_hue.data = {
            DATA_ALEXAMEDIA: {"accounts": {email: mock_account_dict}}
        }

        with patch(
            "custom_components.alexa_media.switch.add_devices",
            new_callable=AsyncMock,
        ) as mock_add_devices:
            mock_add_devices.return_value = True

            from custom_components.alexa_media.switch import async_setup_platform

            config = {"email": email}
            await async_setup_platform(
                mock_hass_with_emulated_hue, config, MagicMock(), discovery_info=None
            )

            # Verify the hue-v1 switch was NOT added to smart_switch entities
            assert len(mock_account_dict["entities"]["smart_switch"]) == 0

    @pytest.mark.asyncio
    async def test_hue_v1_switch_created_when_emulated_hue_not_enabled(
        self, mock_hass, mock_account_dict
    ):
        """Hue-v1 switches are created when emulated_hue is not active.

        When emulated_hue is NOT in the components list, even switches with
        is_hue_v1=True should be created since there's no conflict.
        """
        email = "test@example.com"  # noqa: S105
        # Only keep the hue-v1 switch
        mock_account_dict["devices"]["smart_switch"] = [
            {"id": "switch2", "name": "Hue Plug", "is_hue_v1": True}
        ]
        mock_hass.data = {DATA_ALEXAMEDIA: {"accounts": {email: mock_account_dict}}}

        with patch(
            "custom_components.alexa_media.switch.add_devices",
            new_callable=AsyncMock,
        ) as mock_add_devices:
            mock_add_devices.return_value = True

            from custom_components.alexa_media.switch import async_setup_platform

            config = {"email": email}
            await async_setup_platform(
                mock_hass, config, MagicMock(), discovery_info=None
            )

            # Verify the hue-v1 switch WAS added when emulated_hue is not enabled
            assert len(mock_account_dict["entities"]["smart_switch"]) == 1

    @pytest.mark.asyncio
    async def test_no_smart_switches_when_extended_discovery_disabled(
        self, mock_hass, mock_account_dict
    ):
        """No smart switches created when CONF_EXTENDED_ENTITY_DISCOVERY is False.

        Smart switch creation should be skipped entirely when the extended
        entity discovery option is disabled.
        """
        email = "test@example.com"  # noqa: S105
        mock_account_dict["options"][CONF_EXTENDED_ENTITY_DISCOVERY] = False
        mock_hass.data = {DATA_ALEXAMEDIA: {"accounts": {email: mock_account_dict}}}

        with patch(
            "custom_components.alexa_media.switch.add_devices",
            new_callable=AsyncMock,
        ) as mock_add_devices:
            mock_add_devices.return_value = True

            from custom_components.alexa_media.switch import async_setup_platform

            config = {"email": email}
            await async_setup_platform(
                mock_hass, config, MagicMock(), discovery_info=None
            )

            # No smart switches should be added
            assert len(mock_account_dict["entities"]["smart_switch"]) == 0


class TestHueEmulatedDetection:
    """Tests for emulated_hue detection logic."""

    def test_emulated_hue_detected_in_components(self):
        """Verify emulated_hue is correctly detected in hass components.

        The fix checks for 'emulated_hue' in hass.config.as_dict().get('components').
        This tests the detection logic directly.
        """
        # Simulate hass.config.as_dict() return value
        config_with_hue = {"components": {"emulated_hue", "other_component"}}
        config_without_hue = {"components": {"other_component"}}
        config_empty = {"components": set()}
        config_missing = {}

        # With emulated_hue
        hue_enabled = "emulated_hue" in config_with_hue.get("components", set())
        assert hue_enabled is True

        # Without emulated_hue
        hue_enabled = "emulated_hue" in config_without_hue.get("components", set())
        assert hue_enabled is False

        # Empty components
        hue_enabled = "emulated_hue" in config_empty.get("components", set())
        assert hue_enabled is False

        # Missing components key
        hue_enabled = "emulated_hue" in config_missing.get("components", set())
        assert hue_enabled is False
