from unittest.mock import MagicMock, patch

import pytest
from homeassistant.exceptions import ConditionErrorMessage

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
    """Test that simple path list is correctly joined with dots."""

    with patch("custom_components.alexa_media.helpers.dictor") as mock_dictor:
        mock_dictor.return_value = "test@example.com"

        result = safe_get({"config": {}}, ["config", "email"])

        mock_dictor.assert_called_once()
        args = mock_dictor.call_args[0]
        assert args[1] == "config.email"
        assert result == "test@example.com"


def test_safe_get_escapes_dots_in_keys():
    """Test that dots in key names are properly escaped."""

    with patch("custom_components.alexa_media.helpers.dictor") as mock_dictor:
        mock_dictor.return_value = "test@example.com"

        result = safe_get({}, ["config", "user.email"])

        args = mock_dictor.call_args[0]
        assert args[1] == "config.user\\.email"


def test_safe_get_multiple_dots_in_key():
    """Test that multiple dots in a single key are all escaped."""

    with patch("custom_components.alexa_media.helpers.dictor") as mock_dictor:
        safe_get({}, ["config", "user.email.primary"])

        args = mock_dictor.call_args[0]
        assert args[1] == "config.user\\.email\\.primary"


def test_safe_get_integer_path_segment():
    """Test that integer path segments are converted to strings."""

    with patch("custom_components.alexa_media.helpers.dictor") as mock_dictor:
        safe_get({}, ["items", 0, "name"])

        args = mock_dictor.call_args[0]
        assert args[1] == "items.0.name"


def test_safe_get_forwards_default_value():
    """Test that default value is forwarded as positional arg."""

    with patch("custom_components.alexa_media.helpers.dictor") as mock_dictor:
        mock_dictor.return_value = "default@example.com"

        safe_get({}, ["config", "email"], "default@example.com")

        args = mock_dictor.call_args[0]
        assert len(args) == 3
        assert args[2] == "default@example.com"


def test_safe_get_forwards_kwargs():
    """Test that kwargs are forwarded to dictor."""

    with patch("custom_components.alexa_media.helpers.dictor") as mock_dictor:
        safe_get({}, ["config", "email"], ignorecase=True, checknone=False)

        kwargs = mock_dictor.call_args[1]
        assert kwargs["ignorecase"] is True
        assert kwargs["checknone"] is False


def test_safe_get_type_match_returns_value():
    """Test that matching types pass through correctly."""

    with patch("custom_components.alexa_media.helpers.dictor") as mock_dictor:
        # String default, string result - should pass through
        mock_dictor.return_value = "actual_value"
        result = safe_get({}, ["key"], "default")
        assert result == "actual_value"

        # List default, list result - should pass through
        mock_dictor.return_value = [1, 2, 3]
        result = safe_get({}, ["key"], [])
        assert result == [1, 2, 3]

        # Dict default, dict result - should pass through
        mock_dictor.return_value = {"a": 1}
        result = safe_get({}, ["key"], {})
        assert result == {"a": 1}

        # Int default, int result - should pass through
        mock_dictor.return_value = 42
        result = safe_get({}, ["key"], 0)
        assert result == 42


def test_safe_get_type_mismatch_returns_none():
    """Test that type mismatches return None."""

    with patch("custom_components.alexa_media.helpers.dictor") as mock_dictor:
        # String default, int result - should return None
        mock_dictor.return_value = 123
        result = safe_get({}, ["key"], "default")
        assert result is None

        # List default, dict result - should return None
        mock_dictor.return_value = {"a": 1}
        result = safe_get({}, ["key"], [])
        assert result is None

        # Dict default, string result - should return None
        mock_dictor.return_value = "string"
        result = safe_get({}, ["key"], {})
        assert result is None

        # Int default, string result - should return None
        mock_dictor.return_value = "123"
        result = safe_get({}, ["key"], 0)
        assert result is None


def test_safe_get_none_result_with_default():
    """Test that None results are returned as-is (no type check)."""

    with patch("custom_components.alexa_media.helpers.dictor") as mock_dictor:
        # None result should pass through regardless of default type
        mock_dictor.return_value = None

        result = safe_get({}, ["key"], "default")
        assert result is None

        result = safe_get({}, ["key"], [])
        assert result is None

        result = safe_get({}, ["key"], {})
        assert result is None


def test_safe_get_no_default_no_type_check():
    """Test that without a default, no type checking occurs."""

    with patch("custom_components.alexa_media.helpers.dictor") as mock_dictor:
        # Any type should pass through when no default
        mock_dictor.return_value = "string"
        result = safe_get({}, ["key"])
        assert result == "string"

        mock_dictor.return_value = 123
        result = safe_get({}, ["key"])
        assert result == 123

        mock_dictor.return_value = [1, 2, 3]
        result = safe_get({}, ["key"])
        assert result == [1, 2, 3]


def test_safe_get_none_default_no_type_check():
    """Test that None as default doesn't trigger type checking."""

    with patch("custom_components.alexa_media.helpers.dictor") as mock_dictor:
        # Explicit None default should not trigger type check
        mock_dictor.return_value = "string"
        result = safe_get({}, ["key"], None)
        assert result == "string"

        mock_dictor.return_value = 123
        result = safe_get({}, ["key"], None)
        assert result == 123


def test_safe_get_empty_path_raises():
    """Test that empty path_list raises ValueError."""

    try:
        safe_get({}, [])
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "path_list cannot be empty" in str(e)


def test_safe_get_pathsep_kwarg_removed():
    """Test that pathsep kwarg is removed before calling dictor."""

    with patch("custom_components.alexa_media.helpers.dictor") as mock_dictor:
        safe_get({}, ["key"], pathsep="/")

        # pathsep should not be in kwargs
        kwargs = mock_dictor.call_args[1]
        assert "pathsep" not in kwargs


def test_safe_get_subclass_type_check():
    """Test type checking with subclasses."""

    with patch("custom_components.alexa_media.helpers.dictor") as mock_dictor:
        # bool is subclass of int in Python
        mock_dictor.return_value = True
        result = safe_get({}, ["key"], 0)
        assert result is True  # Should pass isinstance check

        # But int is not instance of bool
        mock_dictor.return_value = 1
        result = safe_get({}, ["key"], False)
        assert result is None  # Should fail isinstance check


def test_safe_get_complex_type_scenarios():
    """Test type checking with more complex scenarios."""

    with patch("custom_components.alexa_media.helpers.dictor") as mock_dictor:
        # Empty list default, non-empty list result
        mock_dictor.return_value = [1, 2, 3]
        result = safe_get({}, ["key"], [])
        assert result == [1, 2, 3]

        # Empty dict default, non-empty dict result
        mock_dictor.return_value = {"a": 1, "b": 2}
        result = safe_get({}, ["key"], {})
        assert result == {"a": 1, "b": 2}

        # String default, empty string result
        mock_dictor.return_value = ""
        result = safe_get({}, ["key"], "default")
        assert result == ""  # Empty string is still a string
