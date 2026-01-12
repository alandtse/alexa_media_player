from unittest.mock import MagicMock

from homeassistant.exceptions import ConditionErrorMessage
import pytest

from custom_components.alexa_media.const import DATA_ALEXAMEDIA
from custom_components.alexa_media.helpers import (
    _existing_serials,
    add_devices,
    is_http2_enabled,
    safe_get,
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

        # Import ConditionErrorMessage from the same module that helpers.py uses
        # to ensure we're using the same class for exception handling
        from custom_components.alexa_media import helpers

        add_devices_callback = MagicMock()
        # Create exception using the class from helpers module's imports
        exc = ConditionErrorMessage(
            "entity_exists", "Entity id already exists: device1"
        )
        add_devices_callback.side_effect = exc

        result = await helpers.add_devices(
            "test_account", devices, add_devices_callback
        )

        assert result is False
        add_devices_callback.assert_called_once_with([device1], False)

    @pytest.mark.asyncio
    async def test_add_devices_condition_error_other(self):
        """Test handling of other condition errors."""
        device1 = MagicMock()
        device1.name = "Device 1"
        devices = [device1]

        # Import from helpers module to ensure same class
        from custom_components.alexa_media import helpers

        add_devices_callback = MagicMock()
        exc = ConditionErrorMessage("other_error", "Some other error")
        add_devices_callback.side_effect = exc

        result = await helpers.add_devices(
            "test_account", devices, add_devices_callback
        )

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


def make_hass_data_http2(data: dict | None):
    """Return a hass-like mock object with a data attribute."""
    if data is None:
        return None
    hass = MagicMock()
    hass.data = data
    return hass


def test_is_http2_enabled_hass_none():
    """Test that is_http2_enabled returns False when hass is None."""
    assert is_http2_enabled(None, "test@example.com") is False


def test_is_http2_enabled_http2_none():
    """Test that http2 set to None results in a False return value."""
    hass = make_hass_data_http2(
        {DATA_ALEXAMEDIA: {"accounts": {"test@example.com": {"http2": None}}}}
    )

    assert is_http2_enabled(hass, "test@example.com") is False


def test_is_http2_enabled_http2_object():
    """Test that a non-None http2 object results in a True return value."""
    mock_http2_client = MagicMock()

    hass = make_hass_data_http2(
        {
            DATA_ALEXAMEDIA: {
                "accounts": {"test@example.com": {"http2": mock_http2_client}}
            }
        }
    )

    assert is_http2_enabled(hass, "test@example.com") is True


def test_safe_get_simple_path():
    """Test that simple path list correctly retrieves nested data."""
    data = {"config": {"email": "test@example.com"}}
    result = safe_get(data, ["config", "email"])
    assert result == "test@example.com"


def test_safe_get_escapes_dots_in_keys():
    """Test that dots in key names are properly escaped."""
    # dictor uses backslash to escape dots in paths
    data = {"config": {"user.email": "test@example.com"}}
    result = safe_get(data, ["config", "user.email"])
    assert result == "test@example.com"


def test_safe_get_multiple_dots_in_key():
    """Test that multiple dots in a single key are all escaped."""
    data = {"config": {"user.email.primary": "test@example.com"}}
    result = safe_get(data, ["config", "user.email.primary"])
    assert result == "test@example.com"


def test_safe_get_integer_path_segment():
    """Test that integer path segments work correctly."""
    data = {"items": [{"name": "first"}, {"name": "second"}]}
    result = safe_get(data, ["items", 0, "name"])
    assert result == "first"


def test_safe_get_forwards_default_value():
    """Test that default value is returned when path doesn't exist."""
    data = {"config": {}}
    result = safe_get(data, ["config", "email"], "default@example.com")
    # Path doesn't exist, so default should be returned
    assert result == "default@example.com"


def test_safe_get_forwards_kwargs():
    """Test that kwargs like ignorecase work correctly."""
    data = {"CONFIG": {"email": "test@example.com"}}
    # Without ignorecase, should return None/default
    result = safe_get(data, ["config", "email"], "default", ignorecase=True)
    assert result == "test@example.com"


def test_safe_get_type_match_returns_value():
    """Test that matching types pass through correctly."""
    # String default, string result - should pass through
    data = {"key": "actual_value"}
    result = safe_get(data, ["key"], "default")
    assert result == "actual_value"

    # List default, list result - should pass through
    data = {"key": [1, 2, 3]}
    result = safe_get(data, ["key"], [])
    assert result == [1, 2, 3]

    # Dict default, dict result - should pass through
    data = {"key": {"a": 1}}
    result = safe_get(data, ["key"], {})
    assert result == {"a": 1}

    # Int default, int result - should pass through
    data = {"key": 42}
    result = safe_get(data, ["key"], 0)
    assert result == 42


def test_safe_get_type_mismatch_returns_default():
    """Test that type mismatches return the default value."""
    # String default, int result - should return default
    data = {"key": 123}
    result = safe_get(data, ["key"], "default")
    assert result == "default"

    # List default, dict result - should return default
    data = {"key": {"a": 1}}
    result = safe_get(data, ["key"], [])
    assert result == []

    # Dict default, string result - should return default
    data = {"key": "string"}
    result = safe_get(data, ["key"], {})
    assert result == {}

    # Int default, string result - should return default
    data = {"key": "123"}
    result = safe_get(data, ["key"], 0)
    assert result == 0


def test_safe_get_none_result_with_default():
    """Test that None results are returned as-is (no type check)."""
    data = {"key": None}
    result = safe_get(data, ["key"], "default")
    assert result is None

    result = safe_get(data, ["key"], [])
    assert result is None

    result = safe_get(data, ["key"], {})
    assert result is None


def test_safe_get_no_default_no_type_check():
    """Test that without a default, no type checking occurs."""
    # Any type should pass through when no default
    data = {"key": "string"}
    result = safe_get(data, ["key"])
    assert result == "string"

    data = {"key": 123}
    result = safe_get(data, ["key"])
    assert result == 123

    data = {"key": [1, 2, 3]}
    result = safe_get(data, ["key"])
    assert result == [1, 2, 3]


def test_safe_get_none_default_no_type_check():
    """Test that None as default doesn't trigger type checking."""
    # Explicit None default should not trigger type check
    data = {"key": "string"}
    result = safe_get(data, ["key"], None)
    assert result == "string"

    data = {"key": 123}
    result = safe_get(data, ["key"], None)
    assert result == 123


def test_safe_get_empty_path_raises():
    """Test that empty path_list raises ValueError."""
    with pytest.raises(ValueError) as exc:
        safe_get({}, [])
    assert "path_list cannot be empty" in str(exc.value)


def test_safe_get_pathsep_kwarg_removed():
    """Test that pathsep kwarg doesn't break the function."""
    # pathsep should be ignored/removed internally
    data = {"key": "value"}
    result = safe_get(data, ["key"], pathsep="/")
    assert result == "value"


def test_safe_get_subclass_type_check():
    """Test type checking with subclasses."""
    # bool is subclass of int in Python
    data = {"key": True}
    result = safe_get(data, ["key"], 0)
    assert result is True  # Should pass isinstance check

    # But int is not instance of bool
    data = {"key": 1}
    result = safe_get(data, ["key"], False)
    assert result is False  # Should fail isinstance check -> return default


def test_safe_get_complex_type_scenarios():
    """Test type checking with more complex scenarios."""
    # Empty list default, non-empty list result
    data = {"key": [1, 2, 3]}
    result = safe_get(data, ["key"], [])
    assert result == [1, 2, 3]

    # Empty dict default, non-empty dict result
    data = {"key": {"a": 1, "b": 2}}
    result = safe_get(data, ["key"], {})
    assert result == {"a": 1, "b": 2}

    # String default, empty string result
    data = {"key": ""}
    result = safe_get(data, ["key"], "default")
    assert result == ""  # Empty string is still a string


class TestAddDevicesFilterDefaults:
    """Regression tests for add_devices filter default value handling.

    These tests verify the fix for the "[] or x" logic bug where the incorrect
    pattern "[] or include_filter" would return None when include_filter=None,
    instead of properly defaulting to an empty list.

    The correct pattern is "include_filter or []" which returns [] when
    include_filter is None/falsy.
    """

    @pytest.mark.asyncio
    async def test_add_devices_with_none_include_filter_adds_all_devices(self):
        """Test that None include_filter defaults to empty list and adds all devices.

        When include_filter is None (the default), it should be treated as an
        empty list, meaning no inclusion filtering is applied and all devices
        should be added.
        """
        device1 = MagicMock()
        device1.name = "Device 1"
        device2 = MagicMock()
        device2.name = "Device 2"
        devices = [device1, device2]

        add_devices_callback = MagicMock()

        # Explicitly pass None to test the default handling
        result = await add_devices(
            "test_account", devices, add_devices_callback, include_filter=None
        )

        assert result is True
        # All devices should be added when include_filter is None
        add_devices_callback.assert_called_once_with(devices, False)

    @pytest.mark.asyncio
    async def test_add_devices_with_none_exclude_filter_adds_all_devices(self):
        """Test that None exclude_filter defaults to empty list and adds all devices.

        When exclude_filter is None (the default), it should be treated as an
        empty list, meaning no exclusion filtering is applied and all devices
        should be added.
        """
        device1 = MagicMock()
        device1.name = "Device 1"
        device2 = MagicMock()
        device2.name = "Device 2"
        devices = [device1, device2]

        add_devices_callback = MagicMock()

        # Explicitly pass None to test the default handling
        result = await add_devices(
            "test_account", devices, add_devices_callback, exclude_filter=None
        )

        assert result is True
        # All devices should be added when exclude_filter is None
        add_devices_callback.assert_called_once_with(devices, False)

    @pytest.mark.asyncio
    async def test_add_devices_with_both_filters_none_adds_all_devices(self):
        """Test that both filters being None adds all devices without filtering.

        This is the default case when add_devices is called without filter
        arguments. Both filters should default to empty lists internally.
        """
        device1 = MagicMock()
        device1.name = "Device 1"
        device2 = MagicMock()
        device2.name = "Device 2"
        device3 = MagicMock()
        device3.name = "Device 3"
        devices = [device1, device2, device3]

        add_devices_callback = MagicMock()

        # Explicitly pass None for both to test the default handling
        result = await add_devices(
            "test_account",
            devices,
            add_devices_callback,
            include_filter=None,
            exclude_filter=None,
        )

        assert result is True
        # All devices should be added when both filters are None
        add_devices_callback.assert_called_once_with(devices, False)

    @pytest.mark.asyncio
    async def test_add_devices_with_empty_include_filter_adds_all_devices(self):
        """Test that empty list include_filter is equivalent to None.

        An empty include_filter should mean "include all" (no filtering),
        not "include nothing". This is consistent with the None behavior.
        """
        device1 = MagicMock()
        device1.name = "Device 1"
        device2 = MagicMock()
        device2.name = "Device 2"
        devices = [device1, device2]

        add_devices_callback = MagicMock()

        result = await add_devices(
            "test_account", devices, add_devices_callback, include_filter=[]
        )

        assert result is True
        # All devices should be added when include_filter is empty list
        add_devices_callback.assert_called_once_with(devices, False)

    @pytest.mark.asyncio
    async def test_add_devices_with_empty_exclude_filter_adds_all_devices(self):
        """Test that empty list exclude_filter is equivalent to None.

        An empty exclude_filter should mean "exclude nothing" (no filtering).
        """
        device1 = MagicMock()
        device1.name = "Device 1"
        device2 = MagicMock()
        device2.name = "Device 2"
        devices = [device1, device2]

        add_devices_callback = MagicMock()

        result = await add_devices(
            "test_account", devices, add_devices_callback, exclude_filter=[]
        )

        assert result is True
        # All devices should be added when exclude_filter is empty list
        add_devices_callback.assert_called_once_with(devices, False)

    @pytest.mark.asyncio
    async def test_add_devices_none_include_with_explicit_exclude_filters_correctly(
        self,
    ):
        """Test that None include_filter combined with explicit exclude_filter works.

        When include_filter is None (adds all) but exclude_filter has entries,
        only the exclude_filter should take effect.
        """
        device1 = MagicMock()
        device1.name = "Device 1"
        device2 = MagicMock()
        device2.name = "Device 2"
        device3 = MagicMock()
        device3.name = "Device 3"
        devices = [device1, device2, device3]

        add_devices_callback = MagicMock()

        result = await add_devices(
            "test_account",
            devices,
            add_devices_callback,
            include_filter=None,
            exclude_filter=["Device 2"],
        )

        assert result is True
        # Device 2 should be excluded, others added
        add_devices_callback.assert_called_once_with([device1, device3], False)

    @pytest.mark.asyncio
    async def test_add_devices_explicit_include_with_none_exclude_filters_correctly(
        self,
    ):
        """Test that explicit include_filter combined with None exclude_filter works.

        When include_filter has entries but exclude_filter is None,
        only devices in the include_filter should be added.
        """
        device1 = MagicMock()
        device1.name = "Device 1"
        device2 = MagicMock()
        device2.name = "Device 2"
        device3 = MagicMock()
        device3.name = "Device 3"
        devices = [device1, device2, device3]

        add_devices_callback = MagicMock()

        result = await add_devices(
            "test_account",
            devices,
            add_devices_callback,
            include_filter=["Device 1", "Device 3"],
            exclude_filter=None,
        )

        assert result is True
        # Only Device 1 and 3 should be added (Device 2 not in include list)
        add_devices_callback.assert_called_once_with([device1, device3], False)
