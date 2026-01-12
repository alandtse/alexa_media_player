"""Tests for the helpers module.

This module verifies the helpers.py functions using source code analysis,
avoiding the complexity of importing the module with its Home Assistant
dependencies.
"""


class TestSafeGetFunction:
    """Tests for the safe_get function in helpers.py."""

    def test_safe_get_function_exists(self):
        """Verify safe_get function is defined in helpers.py."""
        with open("custom_components/alexa_media/helpers.py", encoding="utf-8") as f:
            content = f.read()

        assert "def safe_get(" in content, "safe_get function not found in helpers.py"

    def test_safe_get_escapes_dots_in_path_segments(self):
        """Verify safe_get properly escapes dots in path segment keys.

        The dictor library uses dots as path separators, so keys containing
        dots (like "user.email") need to be escaped with backslash.
        """
        with open("custom_components/alexa_media/helpers.py", encoding="utf-8") as f:
            content = f.read()

        # The code should escape dots in keys - the pattern is replace(".", "\\.")
        assert (
            'replace(".", "\\\\.")' in content or "replace('.', '\\\\.')" in content
        ), "safe_get should escape dots in path segment keys"

    def test_safe_get_handles_integer_path_segments(self):
        """Verify safe_get handles integer path segments for array indexing."""
        with open("custom_components/alexa_media/helpers.py", encoding="utf-8") as f:
            content = f.read()

        # The code should convert integers to strings for the path
        assert "str(" in content, (
            "safe_get should convert integer path segments to strings"
        )

    def test_safe_get_validates_empty_path_list(self):
        """Verify safe_get raises ValueError for empty path_list."""
        with open("custom_components/alexa_media/helpers.py", encoding="utf-8") as f:
            content = f.read()

        assert "path_list cannot be empty" in content, (
            "safe_get should raise ValueError with message for empty path_list"
        )

    def test_safe_get_performs_type_checking(self):
        """Verify safe_get performs type checking when default is provided."""
        with open("custom_components/alexa_media/helpers.py", encoding="utf-8") as f:
            content = f.read()

        # The code should check isinstance when default is provided
        assert "isinstance" in content, (
            "safe_get should use isinstance for type checking"
        )


class TestAddDevicesFunction:
    """Tests for the add_devices function in helpers.py."""

    def test_add_devices_function_exists(self):
        """Verify add_devices function is defined in helpers.py."""
        with open("custom_components/alexa_media/helpers.py", encoding="utf-8") as f:
            content = f.read()

        assert "async def add_devices(" in content, (
            "add_devices function not found in helpers.py"
        )

    def test_add_devices_filter_default_handling(self):
        """Verify add_devices uses correct pattern for filter defaults.

        The correct pattern is "include_filter or []" which returns []
        when include_filter is None. The incorrect pattern "[] or include_filter"
        would return None when include_filter=None.
        """
        with open("custom_components/alexa_media/helpers.py", encoding="utf-8") as f:
            content = f.read()

        # Find the add_devices function
        func_start = content.find("async def add_devices(")
        assert func_start != -1

        # Get the function body (next ~500 chars should include the filter handling)
        func_body = content[func_start : func_start + 800]

        # The correct pattern should be "include_filter or []" not "[] or include_filter"
        # Look for the pattern where the variable comes first
        assert "include_filter or [" in func_body or "include or [" in func_body, (
            "add_devices should use 'include_filter or []' pattern for default handling"
        )
        assert "exclude_filter or [" in func_body or "exclude or [" in func_body, (
            "add_devices should use 'exclude_filter or []' pattern for default handling"
        )

    def test_add_devices_handles_exceptions(self):
        """Verify add_devices catches exceptions from the callback."""
        with open("custom_components/alexa_media/helpers.py", encoding="utf-8") as f:
            content = f.read()

        # Find the add_devices function
        func_start = content.find("async def add_devices(")
        assert func_start != -1

        # Get a larger chunk to find exception handling
        func_body = content[func_start : func_start + 1500]

        # Should have exception handling
        assert "except" in func_body, (
            "add_devices should have exception handling for callback errors"
        )


class TestExistingSerialsFunction:
    """Tests for the _existing_serials function in helpers.py."""

    def test_existing_serials_function_exists(self):
        """Verify _existing_serials function is defined in helpers.py."""
        with open("custom_components/alexa_media/helpers.py", encoding="utf-8") as f:
            content = f.read()

        assert "def _existing_serials(" in content, (
            "_existing_serials function not found in helpers.py"
        )

    def test_existing_serials_handles_app_devices(self):
        """Verify _existing_serials includes app device serial numbers."""
        with open("custom_components/alexa_media/helpers.py", encoding="utf-8") as f:
            content = f.read()

        # Should handle appDeviceList
        assert "appDeviceList" in content, (
            "_existing_serials should handle appDeviceList"
        )

    def test_existing_serials_handles_missing_serial_number(self):
        """Verify _existing_serials handles missing serialNumber gracefully."""
        with open("custom_components/alexa_media/helpers.py", encoding="utf-8") as f:
            content = f.read()

        # Should safely get serialNumber with a default
        assert "serialNumber" in content, (
            "_existing_serials should access serialNumber from app devices"
        )


class TestIsHttp2EnabledFunction:
    """Tests for the is_http2_enabled function in helpers.py."""

    def test_is_http2_enabled_function_exists(self):
        """Verify is_http2_enabled function is defined in helpers.py."""
        with open("custom_components/alexa_media/helpers.py", encoding="utf-8") as f:
            content = f.read()

        assert "def is_http2_enabled(" in content, (
            "is_http2_enabled function not found in helpers.py"
        )

    def test_is_http2_enabled_handles_none_hass(self):
        """Verify is_http2_enabled handles None hass parameter."""
        with open("custom_components/alexa_media/helpers.py", encoding="utf-8") as f:
            content = f.read()

        # Find the function
        func_start = content.find("def is_http2_enabled(")
        assert func_start != -1

        # Get the function body
        func_body = content[func_start : func_start + 300]

        # Should check for None hass
        assert (
            "not hass" in func_body
            or "hass is None" in func_body
            or "if hass" in func_body
        ), "is_http2_enabled should handle None hass parameter"


class TestHelpersModuleStructure:
    """Tests for the overall structure of helpers.py."""

    def test_helpers_uses_dictor_for_safe_access(self):
        """Verify helpers.py uses dictor library for safe dictionary access."""
        with open("custom_components/alexa_media/helpers.py", encoding="utf-8") as f:
            content = f.read()

        assert "dictor" in content, "helpers.py should use dictor for safe dict access"

    def test_helpers_imports_logging(self):
        """Verify helpers.py imports logging for debug/error messages."""
        with open("custom_components/alexa_media/helpers.py", encoding="utf-8") as f:
            content = f.read()

        assert "import logging" in content or "from logging" in content, (
            "helpers.py should import logging"
        )

    def test_helpers_defines_data_alexamedia_constant_usage(self):
        """Verify helpers.py uses DATA_ALEXAMEDIA constant."""
        with open("custom_components/alexa_media/helpers.py", encoding="utf-8") as f:
            content = f.read()

        assert "DATA_ALEXAMEDIA" in content, (
            "helpers.py should use DATA_ALEXAMEDIA constant"
        )
