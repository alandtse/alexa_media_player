"""Tests for notify module.

Tests the notification service using pytest-homeassistant-custom-component.
"""

from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.alexa_media.const import DATA_ALEXAMEDIA
from custom_components.alexa_media.notify import AlexaNotificationService
import pytest

# =============================================================================
# Tests for AlexaNotificationService.devices property
# =============================================================================


class TestNotifyDevicesProperty:
    """Test the devices property of AlexaNotificationService.

    These tests cover a critical bug fix where the `devices` property raised
    KeyError when the 'accounts' key was missing from hass.data[DATA_ALEXAMEDIA].

    The Bug (BEFORE fix):
        if "accounts" not in data and not data["accounts"].items():

    Python evaluates BOTH sides of `and`. When "accounts" is missing, accessing
    data["accounts"] raises KeyError.

    The Fix (AFTER):
        if "accounts" not in data or not data["accounts"].items():

    With `or`, Python short-circuits and skips data["accounts"] when the first
    condition is True.
    """

    def _create_service(self, hass_data: dict) -> AlexaNotificationService:
        """Create a notification service with the given hass.data."""
        service = object.__new__(AlexaNotificationService)
        service.hass = MagicMock()
        service.hass.data = hass_data
        return service

    def test_devices_keyerror_when_accounts_missing(self):
        """Test that devices property does NOT raise KeyError when accounts missing.

        This is the PRIMARY regression test for the and->or bug fix.

        The bug: Using `and` instead of `or` caused Python to evaluate
        `data["accounts"]` even when "accounts" was not in the dict.
        """
        service = self._create_service(
            {
                DATA_ALEXAMEDIA: {
                    # 'accounts' key is intentionally MISSING
                    "config_flows": {},
                }
            }
        )

        # This MUST NOT raise KeyError
        try:
            result = service.devices
        except KeyError as exc:
            pytest.fail(
                f"BUG DETECTED: KeyError raised: {exc}\n\n"
                "CAUSE: The condition uses 'and' instead of 'or':\n"
                "  WRONG: 'accounts' not in data AND data['accounts'].items()\n"
                "  RIGHT: 'accounts' not in data OR  data['accounts'].items()\n\n"
                "With 'and', Python evaluates BOTH conditions. When 'accounts'\n"
                "is missing, accessing data['accounts'] raises KeyError.\n"
                "With 'or', Python short-circuits and never accesses the key."
            )

        assert result == []

    def test_devices_empty_when_accounts_key_missing(self):
        """Test devices returns empty list when accounts key is missing."""
        service = self._create_service({DATA_ALEXAMEDIA: {"config_flows": {}}})

        result = service.devices

        assert result == [], f"Expected empty list, got: {result}"

    def test_devices_empty_when_accounts_is_empty_dict(self):
        """Test devices returns empty list when accounts exists but is empty."""
        service = self._create_service(
            {
                DATA_ALEXAMEDIA: {
                    "accounts": {},
                    "config_flows": {},
                }
            }
        )

        result = service.devices

        assert result == [], f"Expected empty list, got: {result}"

    def test_devices_empty_when_data_alexamedia_missing(self):
        """Test devices handles missing DATA_ALEXAMEDIA gracefully."""
        service = self._create_service({})

        # Should raise KeyError for DATA_ALEXAMEDIA - this is expected behavior
        # The fix only addresses the accounts key, not DATA_ALEXAMEDIA itself
        with pytest.raises(KeyError):
            _ = service.devices

    def test_devices_returns_media_players(self):
        """Test devices returns media players when accounts exist."""
        mock_player_1 = MagicMock()
        mock_player_1.name = "Living Room Echo"
        mock_player_2 = MagicMock()
        mock_player_2.name = "Kitchen Echo"

        service = self._create_service(
            {
                DATA_ALEXAMEDIA: {
                    "accounts": {
                        "test@example.com": {
                            "entities": {
                                "media_player": {
                                    "serial1": mock_player_1,
                                    "serial2": mock_player_2,
                                }
                            }
                        }
                    },
                    "config_flows": {},
                }
            }
        )

        result = service.devices

        assert len(result) == 2
        assert mock_player_1 in result
        assert mock_player_2 in result

    def test_devices_aggregates_multiple_accounts(self):
        """Test devices aggregates media players from all accounts."""
        mock_player_1 = MagicMock()
        mock_player_2 = MagicMock()

        service = self._create_service(
            {
                DATA_ALEXAMEDIA: {
                    "accounts": {
                        "user1@example.com": {
                            "entities": {"media_player": {"serial1": mock_player_1}}
                        },
                        "user2@example.com": {
                            "entities": {"media_player": {"serial2": mock_player_2}}
                        },
                    },
                    "config_flows": {},
                }
            }
        )

        result = service.devices

        assert len(result) == 2
        assert mock_player_1 in result
        assert mock_player_2 in result


# =============================================================================
# DRAFT: Tests for async_send_message group expansion (PR #3446)
#
# These tests cover the two-stage target preprocessing introduced in PR #3446:
#   1. Normalisation: JSON / comma-delimited / bare string → list of strings
#   2. Expansion: media_player.* helper groups and old-style group.* YAML groups
#
# =============================================================================


class TestAsyncSendMessageGroupExpansion:
    """Draft tests for target normalisation and group expansion in async_send_message.

    Covers the fix introduced in PR #3446 (restore old-style YAML groups expansion):
    - UI media_player.* helper groups are expanded via state.attributes["entity_id"]
    - Legacy group.* YAML entities are expanded via expand_entity_ids()
    - Targets that are not groups are passed through unchanged
    - Non-string targets are passed through unchanged
    - Comma-delimited and JSON string targets are normalised before expansion
    """

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_hass(self, states: dict | None = None) -> MagicMock:
        """Return a minimal hass mock.

        Parameters
        ----------
        states:
            Mapping of entity_id → dict of attributes, used to drive
            hass.states.get().
        """
        hass = MagicMock()
        hass.data = {
            DATA_ALEXAMEDIA: {
                "accounts": {
                    "test@example.com": {
                        "entities": {"media_player": {}},
                        "options": {},
                    }
                }
            }
        }

        def _states_get(entity_id):
            if states and entity_id in states:
                state = MagicMock()
                state.attributes = states[entity_id]
                return state
            return None

        hass.states.get.side_effect = _states_get
        return hass

    def _create_service(self, hass: MagicMock):
        """Instantiate AlexaNotificationService without calling __init__."""
        from custom_components.alexa_media.notify import AlexaNotificationService

        service = object.__new__(AlexaNotificationService)
        service.hass = hass
        service.last_called = True
        # Stub convert() so tests focus purely on expansion logic.
        service.convert = MagicMock(return_value=[])
        return service

    # ------------------------------------------------------------------
    # Target normalisation tests
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_bare_string_target_is_appended(self):
        """A single bare string target (no comma, not JSON) is kept as-is."""
        hass = self._make_hass()
        service = self._create_service(hass)

        with patch(
            "custom_components.alexa_media.notify.expand_entity_ids",
            return_value=["media_player.echo1"],
        ):
            await service.async_send_message(
                "hello", **{"target": ["media_player.echo1"]}
            )

        service.convert.assert_called_once()
        assert service.convert.call_args.kwargs["type_"] == "entities"
        expanded = service.convert.call_args[0][0]
        assert "media_player.echo1" in expanded

    @pytest.mark.asyncio
    async def test_comma_delimited_target_is_split(self):
        """A comma-delimited target string is split into individual targets."""
        hass = self._make_hass()
        service = self._create_service(hass)

        with patch(
            "custom_components.alexa_media.notify.expand_entity_ids",
            return_value=[],
        ):
            await service.async_send_message(
                "hello",
                **{"target": ["media_player.echo1, media_player.echo2"]},
            )

        service.convert.assert_called_once()
        assert service.convert.call_args.kwargs["type_"] == "entities"
        expanded = service.convert.call_args[0][0]
        assert "media_player.echo1" in expanded
        assert "media_player.echo2" in expanded

    @pytest.mark.asyncio
    async def test_json_string_target_is_parsed(self):
        """A JSON-encoded list target is decoded into individual targets."""
        import json

        hass = self._make_hass()
        service = self._create_service(hass)

        json_target = json.dumps(["media_player.echo1", "media_player.echo2"])

        with patch(
            "custom_components.alexa_media.notify.expand_entity_ids",
            return_value=[],
        ):
            await service.async_send_message(
                "hello",
                **{"target": [json_target]},
            )

        service.convert.assert_called_once()
        assert service.convert.call_args.kwargs["type_"] == "entities"
        expanded = service.convert.call_args[0][0]
        assert "media_player.echo1" in expanded
        assert "media_player.echo2" in expanded

    @pytest.mark.asyncio
    async def test_non_string_dict_target_does_not_raise(self):
        """A dict target must not raise TypeError from json.loads.

        Regression test for issue #3453: ``json.loads`` only accepts
        ``str | bytes | bytearray``. A dict (or any non-string) raised
        ``TypeError`` outside the ``json.JSONDecodeError`` handler, aborting
        ``async_send_message``.
        """
        hass = self._make_hass()
        service = self._create_service(hass)

        dict_target = {"entity_id": "media_player.echo1"}

        with patch(
            "custom_components.alexa_media.notify.expand_entity_ids",
            return_value=[],
        ):
            await service.async_send_message("hello", **{"target": [dict_target]})

        service.convert.assert_called_once()
        expanded = service.convert.call_args[0][0]
        assert dict_target in expanded

    @pytest.mark.asyncio
    async def test_non_string_int_target_does_not_raise(self):
        """An int target is appended verbatim without TypeError."""
        hass = self._make_hass()
        service = self._create_service(hass)

        with patch(
            "custom_components.alexa_media.notify.expand_entity_ids",
            return_value=[],
        ):
            await service.async_send_message("hello", **{"target": [42]})

        service.convert.assert_called_once()
        expanded = service.convert.call_args[0][0]
        assert 42 in expanded

    @pytest.mark.asyncio
    async def test_json_scalar_string_target_appended_not_extended(self):
        """JSON that decodes to a scalar (non-list) is appended, not extended.

        Previous code used ``processed_targets += json.loads(target)`` which
        would iterate a string into individual characters. The fix appends a
        non-list parse result instead.
        """
        hass = self._make_hass()
        service = self._create_service(hass)

        # ``json.loads('"echo1"')`` returns the string "echo1". Under the old
        # code, ``processed_targets += "echo1"`` would produce
        # ``["e", "c", "h", "o", "1"]``.
        with patch(
            "custom_components.alexa_media.notify.expand_entity_ids",
            return_value=[],
        ):
            await service.async_send_message("hello", **{"target": ['"echo1"']})

        service.convert.assert_called_once()
        expanded = service.convert.call_args[0][0]
        assert "echo1" in expanded
        assert "e" not in expanded

    # ------------------------------------------------------------------
    # media_player.* group expansion tests
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_media_player_group_with_list_members_is_expanded(self):
        """A media_player.* group whose entity_id attribute is a list is expanded."""
        hass = self._make_hass(
            states={
                "media_player.echo_group": {
                    "entity_id": ["media_player.echo1", "media_player.echo2"]
                }
            }
        )
        service = self._create_service(hass)

        with patch(
            "custom_components.alexa_media.notify.expand_entity_ids",
            return_value=[],
        ):
            await service.async_send_message(
                "hello", **{"target": ["media_player.echo_group"]}
            )

        service.convert.assert_called_once()
        assert service.convert.call_args.kwargs["type_"] == "entities"
        expanded = service.convert.call_args[0][0]
        assert "media_player.echo1" in expanded
        assert "media_player.echo2" in expanded
        assert "media_player.echo_group" not in expanded

    @pytest.mark.asyncio
    async def test_media_player_group_with_tuple_members_is_expanded(self):
        """A media_player.* group whose entity_id is a tuple is expanded."""
        hass = self._make_hass(
            states={
                "media_player.echo_group": {
                    "entity_id": ("media_player.echo1", "media_player.echo2")
                }
            }
        )
        service = self._create_service(hass)

        with patch(
            "custom_components.alexa_media.notify.expand_entity_ids",
            return_value=[],
        ):
            await service.async_send_message(
                "hello", **{"target": ["media_player.echo_group"]}
            )

        service.convert.assert_called_once()
        assert service.convert.call_args.kwargs["type_"] == "entities"
        expanded = service.convert.call_args[0][0]
        assert "media_player.echo1" in expanded
        assert "media_player.echo2" in expanded

    @pytest.mark.asyncio
    async def test_media_player_group_with_non_list_entity_id_kept_as_is(self):
        """A media_player.* group whose entity_id is not a list is kept unchanged.

        The code appends the group target itself rather than the scalar entity_id
        value, matching the intent described in the PR comments.
        """
        hass = self._make_hass(
            states={
                "media_player.echo_group": {
                    "entity_id": "media_player.echo1"  # scalar, not a list
                }
            }
        )
        service = self._create_service(hass)

        with patch(
            "custom_components.alexa_media.notify.expand_entity_ids",
            return_value=[],
        ):
            await service.async_send_message(
                "hello", **{"target": ["media_player.echo_group"]}
            )

        service.convert.assert_called_once()
        assert service.convert.call_args.kwargs["type_"] == "entities"
        expanded = service.convert.call_args[0][0]
        assert "media_player.echo_group" in expanded

    @pytest.mark.asyncio
    async def test_media_player_entity_without_entity_id_attr_passes_through(self):
        """A media_player.* entity that is NOT a group (no entity_id attr) passes through."""
        hass = self._make_hass(
            states={
                "media_player.echo1": {"friendly_name": "Echo"}  # no entity_id attr
            }
        )
        service = self._create_service(hass)

        with patch(
            "custom_components.alexa_media.notify.expand_entity_ids",
            return_value=[],
        ):
            await service.async_send_message(
                "hello", **{"target": ["media_player.echo1"]}
            )

        service.convert.assert_called_once()
        assert service.convert.call_args.kwargs["type_"] == "entities"
        expanded = service.convert.call_args[0][0]
        assert "media_player.echo1" in expanded

    # ------------------------------------------------------------------
    # group.* (old-style YAML) expansion tests
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_yaml_group_is_expanded_via_expand_entity_ids(self):
        """A group.* target is expanded using expand_entity_ids().

        This is the PRIMARY regression test for PR #3446. Prior to this fix,
        group.* targets were not handled and silently passed through without
        expansion, so notify.alexa_media failed to reach group members.
        """
        hass = self._make_hass()
        service = self._create_service(hass)

        with patch(
            "custom_components.alexa_media.notify.expand_entity_ids",
            return_value=["media_player.echo1", "media_player.echo2"],
        ) as mock_expand:
            await service.async_send_message(
                "hello", **{"target": ["group.echo_players"]}
            )

        mock_expand.assert_called_once_with(hass, ["group.echo_players"])
        service.convert.assert_called_once()
        assert service.convert.call_args.kwargs["type_"] == "entities"
        expanded = service.convert.call_args[0][0]
        assert "media_player.echo1" in expanded
        assert "media_player.echo2" in expanded
        assert "group.echo_players" not in expanded

    @pytest.mark.asyncio
    async def test_yaml_group_expansion_falls_back_on_value_error(self):
        """When expand_entity_ids raises ValueError the original target is kept."""
        hass = self._make_hass()
        service = self._create_service(hass)

        with patch(
            "custom_components.alexa_media.notify.expand_entity_ids",
            side_effect=ValueError("invalid group"),
        ):
            await service.async_send_message("hello", **{"target": ["group.bad_group"]})

        service.convert.assert_called_once()
        assert service.convert.call_args.kwargs["type_"] == "entities"
        expanded = service.convert.call_args[0][0]
        assert "group.bad_group" in expanded

    @pytest.mark.asyncio
    async def test_yaml_group_original_not_in_expanded_when_successfully_expanded(
        self,
    ):
        """group.* target is removed from the list after successful expansion."""
        hass = self._make_hass()
        service = self._create_service(hass)

        with patch(
            "custom_components.alexa_media.notify.expand_entity_ids",
            return_value=["media_player.echo1"],
        ):
            await service.async_send_message(
                "hello", **{"target": ["group.echo_players"]}
            )

        service.convert.assert_called_once()
        assert service.convert.call_args.kwargs["type_"] == "entities"
        expanded = service.convert.call_args[0][0]
        assert "group.echo_players" not in expanded

    # ------------------------------------------------------------------
    # Pass-through tests
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_non_group_string_target_passes_through(self):
        """A plain string target that is neither media_player.* nor group.* passes through."""
        hass = self._make_hass()
        service = self._create_service(hass)

        with patch(
            "custom_components.alexa_media.notify.expand_entity_ids",
            return_value=[],
        ):
            await service.async_send_message(
                "hello", **{"target": ["Living Room Echo"]}
            )

        service.convert.assert_called_once()
        assert service.convert.call_args.kwargs["type_"] == "entities"
        expanded = service.convert.call_args[0][0]
        assert "Living Room Echo" in expanded

    @pytest.mark.asyncio
    async def test_sensor_domain_target_passes_through_unchanged(self):
        """A sensor.* target (not a group or media_player group) passes through unchanged."""
        hass = self._make_hass()
        service = self._create_service(hass)

        with patch(
            "custom_components.alexa_media.notify.expand_entity_ids",
            return_value=[],
        ):
            await service.async_send_message(
                "hello", **{"target": ["sensor.temperature"]}
            )

        service.convert.assert_called_once()
        assert service.convert.call_args.kwargs["type_"] == "entities"
        expanded = service.convert.call_args[0][0]
        assert "sensor.temperature" in expanded

    # ------------------------------------------------------------------
    # Mixed target list tests
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_mixed_group_and_plain_targets_all_resolved(self):
        """A mix of group.*, media_player group, and plain targets is fully resolved."""
        hass = self._make_hass(
            states={"media_player.echo_group": {"entity_id": ["media_player.echo1"]}}
        )
        service = self._create_service(hass)

        def _expand(hass_arg, entity_ids):
            if "group.echo_players" in entity_ids:
                return ["media_player.echo2", "media_player.echo3"]
            return entity_ids

        with patch(
            "custom_components.alexa_media.notify.expand_entity_ids",
            side_effect=_expand,
        ):
            await service.async_send_message(
                "hello",
                **{
                    "target": [
                        "media_player.echo_group",
                        "group.echo_players",
                        "Living Room Echo",
                    ]
                },
            )

        service.convert.assert_called_once()
        assert service.convert.call_args.kwargs["type_"] == "entities"
        expanded = service.convert.call_args[0][0]
        assert "media_player.echo1" in expanded  # from media_player group
        assert "media_player.echo2" in expanded  # from YAML group
        assert "media_player.echo3" in expanded  # from YAML group
        assert "Living Room Echo" in expanded  # plain target
        assert "media_player.echo_group" not in expanded
        assert "group.echo_players" not in expanded
