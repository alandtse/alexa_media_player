"""Test the const module."""

from datetime import timedelta

import pytest

from custom_components.alexa_media.const import (
    __version__,
    PROJECT_URL,
    ISSUE_URL,
    NOTIFY_URL,
    DOMAIN,
    DATA_ALEXAMEDIA,
    PLAY_SCAN_INTERVAL,
    SCAN_INTERVAL,
    MIN_TIME_BETWEEN_SCANS,
    MIN_TIME_BETWEEN_FORCED_SCANS,
    ALEXA_COMPONENTS,
    DEPENDENT_ALEXA_COMPONENTS,
    HTTP_COOKIE_HEADER,
    CONF_ACCOUNTS,
    CONF_DEBUG,
    CONF_HASS_URL,
    CONF_INCLUDE_DEVICES,
    CONF_EXCLUDE_DEVICES,
    CONF_QUEUE_DELAY,
    CONF_PUBLIC_URL,
)


class TestConstants:
    """Test various constants and configuration values."""

    def test_version_format(self):
        """Test that version follows semantic versioning format."""
        # Version should be in format X.Y.Z
        version_parts = __version__.split('.')
        assert len(version_parts) == 3
        for part in version_parts:
            assert part.isdigit()

    def test_project_url_format(self):
        """Test that project URL is properly formatted."""
        assert PROJECT_URL.startswith("https://github.com/")
        assert PROJECT_URL.endswith("/")

    def test_issue_url_based_on_project(self):
        """Test that issue URL is based on project URL."""
        expected_issue_url = f"{PROJECT_URL}issues"
        assert ISSUE_URL == expected_issue_url

    def test_notify_url_based_on_project(self):
        """Test that notify URL is based on project URL."""
        expected_notify_url = f"{PROJECT_URL}wiki/Configuration%3A-Notification-Component#use-the-notifyalexa_media-service"
        assert NOTIFY_URL == expected_notify_url

    def test_domain_value(self):
        """Test that domain is set correctly."""
        assert DOMAIN == "alexa_media"

    def test_data_alexamedia_value(self):
        """Test that DATA_ALEXAMEDIA matches domain."""
        assert DATA_ALEXAMEDIA == "alexa_media"
        assert DATA_ALEXAMEDIA == DOMAIN

    def test_play_scan_interval_type(self):
        """Test that PLAY_SCAN_INTERVAL is an integer."""
        assert isinstance(PLAY_SCAN_INTERVAL, int)
        assert PLAY_SCAN_INTERVAL > 0

    def test_scan_interval_type_and_value(self):
        """Test that SCAN_INTERVAL is a timedelta and reasonable."""
        assert isinstance(SCAN_INTERVAL, timedelta)
        assert SCAN_INTERVAL.total_seconds() > 0
        assert SCAN_INTERVAL == timedelta(seconds=60)

    def test_min_time_between_scans_matches_scan_interval(self):
        """Test that MIN_TIME_BETWEEN_SCANS equals SCAN_INTERVAL."""
        assert MIN_TIME_BETWEEN_SCANS == SCAN_INTERVAL

    def test_min_time_between_forced_scans_value(self):
        """Test that MIN_TIME_BETWEEN_FORCED_SCANS is reasonable."""
        assert isinstance(MIN_TIME_BETWEEN_FORCED_SCANS, timedelta)
        assert MIN_TIME_BETWEEN_FORCED_SCANS == timedelta(seconds=1)
        # Forced scans should be allowed more frequently than regular scans
        assert MIN_TIME_BETWEEN_FORCED_SCANS < SCAN_INTERVAL

    def test_alexa_components_list(self):
        """Test that ALEXA_COMPONENTS contains expected components."""
        assert isinstance(ALEXA_COMPONENTS, list)
        assert "media_player" in ALEXA_COMPONENTS
        # Ensure no duplicates
        assert len(ALEXA_COMPONENTS) == len(set(ALEXA_COMPONENTS))

    def test_dependent_alexa_components_list(self):
        """Test that DEPENDENT_ALEXA_COMPONENTS contains expected components."""
        assert isinstance(DEPENDENT_ALEXA_COMPONENTS, list)
        expected_components = [
            "notify",
            "switch", 
            "sensor",
            "alarm_control_panel",
            "light",
            "binary_sensor",
        ]
        for component in expected_components:
            assert component in DEPENDENT_ALEXA_COMPONENTS
        # Ensure no duplicates
        assert len(DEPENDENT_ALEXA_COMPONENTS) == len(set(DEPENDENT_ALEXA_COMPONENTS))

    def test_alexa_components_and_dependent_no_overlap(self):
        """Test that main and dependent components don't overlap."""
        main_set = set(ALEXA_COMPONENTS)
        dependent_set = set(DEPENDENT_ALEXA_COMPONENTS)
        assert main_set.isdisjoint(dependent_set)

    def test_http_cookie_header_format(self):
        """Test that HTTP_COOKIE_HEADER is correct."""
        assert HTTP_COOKIE_HEADER == "# HTTP Cookie File"

    def test_configuration_constants_are_strings(self):
        """Test that configuration constants are strings."""
        config_constants = [
            CONF_ACCOUNTS,
            CONF_DEBUG,
            CONF_HASS_URL,
            CONF_INCLUDE_DEVICES,
            CONF_EXCLUDE_DEVICES,
            CONF_QUEUE_DELAY,
            CONF_PUBLIC_URL,
        ]
        
        for const in config_constants:
            assert isinstance(const, str)
            assert len(const) > 0

    def test_specific_configuration_values(self):
        """Test specific configuration constant values."""
        assert CONF_ACCOUNTS == "accounts"
        assert CONF_DEBUG == "debug"
        assert CONF_HASS_URL == "hass_url"
        assert CONF_INCLUDE_DEVICES == "include_devices"
        assert CONF_EXCLUDE_DEVICES == "exclude_devices"
        assert CONF_QUEUE_DELAY == "queue_delay"
        assert CONF_PUBLIC_URL == "public_url"

    def test_all_constants_exist(self):
        """Test that all expected constants are defined and not None."""
        constants_to_check = [
            __version__,
            PROJECT_URL,
            ISSUE_URL,
            NOTIFY_URL,
            DOMAIN,
            DATA_ALEXAMEDIA,
            PLAY_SCAN_INTERVAL,
            SCAN_INTERVAL,
            MIN_TIME_BETWEEN_SCANS,
            MIN_TIME_BETWEEN_FORCED_SCANS,
            ALEXA_COMPONENTS,
            DEPENDENT_ALEXA_COMPONENTS,
            HTTP_COOKIE_HEADER,
            CONF_ACCOUNTS,
            CONF_DEBUG,
            CONF_HASS_URL,
            CONF_INCLUDE_DEVICES,
            CONF_EXCLUDE_DEVICES,
            CONF_QUEUE_DELAY,
            CONF_PUBLIC_URL,
        ]
        
        for const in constants_to_check:
            assert const is not None