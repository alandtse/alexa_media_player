from typing import Any
from unittest.mock import MagicMock, patch

from homeassistant.exceptions import ConditionErrorMessage
import pytest

from custom_components.alexa_media.const import DATA_ALEXAMEDIA
from custom_components.alexa_media.helpers import (
    _existing_serials,
    add_devices,
    get_nested_value,
)


def test_existing_serials_no_accounts():
    hass = MagicMock()
    login_obj = MagicMock()
    login_obj.email = "test@example.com"
    hass.data = {}

    result = _existing_serials(hass, login_obj)
    assert result == []


def test_existing_serials_no_email():
    hass = MagicMock()
    login_obj = MagicMock()
    login_obj.email = "test@example.com"
    hass.data = {DATA_ALEXAMEDIA: {"accounts": {}}}

    result = _existing_serials(hass, login_obj)
    assert result == []


def test_existing_serials_with_devices():
    hass = MagicMock()
    login_obj = MagicMock()
    email = "test@example.com"
    login_obj.email = email

    hass.data = {
        DATA_ALEXAMEDIA: {
            "accounts": {
                email: {
                    "entities": {"media_player": {"device1": {}, "device2": {}}},
                    "devices": {"media_player": {"device1": {}, "device2": {}}},
                }
            }
        }
    }

    result = _existing_serials(hass, login_obj)
    assert sorted(result) == ["device1", "device2"]


def test_existing_serials_with_app_devices():
    hass = MagicMock()
    login_obj = MagicMock()
    email = "test@example.com"
    login_obj.email = email

    hass.data = {
        DATA_ALEXAMEDIA: {
            "accounts": {
                email: {
                    "entities": {"media_player": {"device1": {}}},
                    "devices": {
                        "media_player": {
                            "device1": {
                                "appDeviceList": [
                                    {"serialNumber": "app1"},
                                    {"serialNumber": "app2"},
                                    {
                                        "serialNumber": "device1"
                                    },  # this reproduces the infinite loop bug
                                ]
                            }
                        }
                    },
                }
            }
        }
    }

    result = _existing_serials(hass, login_obj)
    assert sorted(result) == ["app1", "app2", "device1", "device1"]


def test_existing_serials_with_invalid_app_devices():
    hass = MagicMock()
    login_obj = MagicMock()
    email = "test@example.com"
    login_obj.email = email

    hass.data = {
        DATA_ALEXAMEDIA: {
            "accounts": {
                email: {
                    "entities": {"media_player": {"device1": {}}},
                    "devices": {
                        "media_player": {
                            "device1": {
                                "appDeviceList": [
                                    {"invalid": "data"},
                                    {"serialNumber": "app1"},
                                ]
                            }
                        }
                    },
                }
            }
        }
    }

    result = _existing_serials(hass, login_obj)
    assert sorted(result) == ["app1", "device1"]


@pytest.mark.parametrize(
    "data, path, default, expected",
    [
        # Basic dict access
        ({"a": {"b": 1}}, "a.b", None, 1),
        # Missing key
        ({"a": {}}, "a.c", "X", "X"),
        # None inside dict (special case)
        ({"a": None}, "a.b", "NOT_FOUND", "NOT_FOUND"),
        # List index access
        ({"a": [10, 20, 30]}, "a.1", None, 20),
        # Invalid list index
        ({"a": [10]}, "a.5", "OOB", "OOB"),
        # Non-int list index
        ({"a": [10]}, "a.foo", "ERR", "ERR"),
        # Nested combinations
        ({"a": [{"b": 99}]}, "a.0.b", None, 99),
        # Sequence but not traversable
        ("hello", "0", "D", "D"),
        # Empty path → return data itself
        ({"a": 1}, "", None, {"a": 1}),
    ],
)
def test_get_nested_value(data: Any, path: str, default: Any, expected: Any):
    assert get_nested_value(data, path, default) == expected


def test_get_nested_value_deep_none():
    data = {"a": {"b": None}}
    assert get_nested_value(data, "a.b.c", "DEF") == "DEF"


def test_get_nested_value_tuple_access():
    data = {"a": (10, 20, 30)}
    assert get_nested_value(data, "a.2", None) == 30


def test_get_nested_value_non_container_midway():
    data = {"a": 123}
    assert get_nested_value(data, "a.b", "FAIL") == "FAIL"


class TestAddDevices:
    """Test the add_devices function."""

    @pytest.mark.asyncio
    async def test_add_devices_success(self):
        """Test successful device addition."""
        device1 = MagicMock()
        device1.name = "Device 1"
        device2 = MagicMock()
        device2.name = "Device 2"
        devices = [device1, device2]

        add_devices_callback = MagicMock()

        result = await add_devices("test_account", devices, add_devices_callback)

        assert result is True
        add_devices_callback.assert_called_once_with(devices, False)

    @pytest.mark.asyncio
    async def test_add_devices_empty_list(self):
        """Test adding empty device list."""
        devices = []
        add_devices_callback = MagicMock()

        result = await add_devices("test_account", devices, add_devices_callback)

        assert result is True
        add_devices_callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_devices_with_include_filter(self):
        """Test device filtering with include filter."""
        device1 = MagicMock()
        device1.name = "Device 1"
        device2 = MagicMock()
        device2.name = "Device 2"
        devices = [device1, device2]

        add_devices_callback = MagicMock()
        include_filter = ["Device 1"]

        result = await add_devices(
            "test_account", devices, add_devices_callback, include_filter=include_filter
        )

        assert result is True
        # Only device1 should be added
        add_devices_callback.assert_called_once_with([device1], False)

    @pytest.mark.asyncio
    async def test_add_devices_with_exclude_filter(self):
        """Test device filtering with exclude filter."""
        device1 = MagicMock()
        device1.name = "Device 1"
        device2 = MagicMock()
        device2.name = "Device 2"
        devices = [device1, device2]

        add_devices_callback = MagicMock()
        exclude_filter = ["Device 2"]

        result = await add_devices(
            "test_account", devices, add_devices_callback, exclude_filter=exclude_filter
        )

        assert result is True
        # Only device1 should be added
        add_devices_callback.assert_called_once_with([device1], False)

    @pytest.mark.asyncio
    async def test_add_devices_filtered_to_empty(self):
        """Test when filtering results in no devices to add."""
        device1 = MagicMock()
        device1.name = "Device 1"
        devices = [device1]

        add_devices_callback = MagicMock()
        exclude_filter = ["Device 1"]

        result = await add_devices(
            "test_account", devices, add_devices_callback, exclude_filter=exclude_filter
        )

        assert result is True
        add_devices_callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_devices_condition_error_entity_exists(self):
        """Test handling of entity already exists error."""
        device1 = MagicMock()
        device1.name = "Device 1"
        devices = [device1]

        add_devices_callback = MagicMock()
        add_devices_callback.side_effect = ConditionErrorMessage(
            "entity_exists", "Entity id already exists: device1"
        )

        result = await add_devices("test_account", devices, add_devices_callback)

        assert result is False
        add_devices_callback.assert_called_once_with([device1], False)

    @pytest.mark.asyncio
    async def test_add_devices_condition_error_other(self):
        """Test handling of other condition errors."""
        device1 = MagicMock()
        device1.name = "Device 1"
        devices = [device1]

        add_devices_callback = MagicMock()
        add_devices_callback.side_effect = ConditionErrorMessage(
            "other_error", "Some other error"
        )

        result = await add_devices("test_account", devices, add_devices_callback)

        assert result is False
        add_devices_callback.assert_called_once_with([device1], False)

    @pytest.mark.asyncio
    async def test_add_devices_base_exception(self):
        """Test handling of base exceptions."""
        device1 = MagicMock()
        device1.name = "Device 1"
        devices = [device1]

        add_devices_callback = MagicMock()
        add_devices_callback.side_effect = ValueError("Some error")

        result = await add_devices("test_account", devices, add_devices_callback)

        assert result is False
        add_devices_callback.assert_called_once_with([device1], False)

    @pytest.mark.asyncio
    async def test_add_devices_include_and_exclude_filters(self):
        """Test device filtering with both include and exclude filters."""
        device1 = MagicMock()
        device1.name = "Device 1"
        device2 = MagicMock()
        device2.name = "Device 2"
        device3 = MagicMock()
        device3.name = "Device 3"
        devices = [device1, device2, device3]

        add_devices_callback = MagicMock()
        include_filter = ["Device 1", "Device 2"]
        exclude_filter = ["Device 2"]

        result = await add_devices(
            "test_account",
            devices,
            add_devices_callback,
            include_filter=include_filter,
            exclude_filter=exclude_filter,
        )

        assert result is True
        # Only device1 should be added (included but not excluded)
        add_devices_callback.assert_called_once_with([device1], False)
