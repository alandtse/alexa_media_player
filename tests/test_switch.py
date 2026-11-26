"""Tests for switch.py - specifically the hue_emulated_enabled bugfix.

This tests the fix for the undefined variable bug where hue_emulated_enabled
was used but never defined, causing a NameError when users had Smart Plug
devices with CONF_EXTENDED_ENTITY_DISCOVERY enabled.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from homeassistant.exceptions import PlatformNotReady
import pytest

from custom_components.alexa_media import switch as switch_platform
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


async def _drain_display_registration(account):
    """Wait for the tracked display registration tasks to finish.

    Exceptions propagate intentionally: a failed registration task must fail the
    test instead of letting a negative assertion pass for the wrong reason.
    """
    tasks = list(account.get("display_setup_tasks", ()))
    if tasks:
        await asyncio.gather(*tasks)


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
            "amazon_kids_switch": [],
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

        # This should not raise NameError: name 'hue_emulated_enabled' is not defined
        config = {"email": email}
        result = await switch_platform.async_setup_platform(
            mock_hass, config, MagicMock(), discovery_info=None
        )

        assert result is True


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

        config = {"email": email}
        await switch_platform.async_setup_platform(
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

        config = {"email": email}
        await switch_platform.async_setup_platform(
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

        config = {"email": email}
        await switch_platform.async_setup_platform(
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

        config = {"email": email}
        await switch_platform.async_setup_platform(
            mock_hass, config, MagicMock(), discovery_info=None
        )

        # No smart switches should be added
        assert len(mock_account_dict["entities"]["smart_switch"]) == 0


@pytest.mark.asyncio
async def test_unload_removes_every_switch(mock_hass):
    """Unload iterates switch types, not the device serial key."""
    email = "test@example.com"  # noqa: S105
    dnd = MagicMock()
    dnd.async_remove = AsyncMock()
    shuffle = MagicMock()
    shuffle.async_remove = AsyncMock()
    mock_hass.data = {
        DATA_ALEXAMEDIA: {
            "accounts": {
                email: {
                    "entities": {
                        "switch": {"serial-1": {"dnd": dnd, "shuffle": shuffle}},
                        "amazon_kids_switch": [],
                    }
                }
            }
        }
    }
    entry = MagicMock()
    entry.data = {"email": email}

    from custom_components.alexa_media.switch import async_unload_entry

    assert await async_unload_entry(mock_hass, entry)
    dnd.async_remove.assert_awaited_once()
    shuffle.async_remove.assert_awaited_once()


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


@pytest.fixture
def switch_setup(monkeypatch, mock_hass, mock_account_dict):
    """Supply one Echo, one plug and one air quality monitor."""
    account = mock_account_dict
    devices = account["devices"]
    devices["media_player"] = {
        "echo": {
            "capabilities": ["MUSIC_SKILL"],
            "deviceFamily": "ECHO",
            "deviceType": "echo-type",
        }
    }
    devices["switch"] = {"echo": {"dnd": True}}
    devices["smart_switch"] = [
        {"id": "plug", "name": "Plug", "is_hue_v1": False},
        {"id": "plug", "name": "Plug", "is_hue_v1": False},
    ]
    devices["aiaqm"] = [
        {"id": "aqm", "name": "Monitor", "led_indicator_instance": "led"}
    ]
    client = SimpleNamespace(device_serial_number="echo")
    account["entities"]["media_player"] = {"echo": client}
    mock_hass.data = {DATA_ALEXAMEDIA: {"accounts": {"test@example.com": account}}}
    entry = SimpleNamespace(data={"email": "test@example.com"}, options={})
    kids = SimpleNamespace(
        track=MagicMock(), async_add_when_dashboard=AsyncMock(), async_start=AsyncMock()
    )
    monkeypatch.setattr(switch_platform, "KIDS_CAPABLE_FAMILIES", {"ECHO"})
    monkeypatch.setattr(switch_platform, "async_get_state", lambda *_: kids)
    monkeypatch.setattr(
        switch_platform,
        "can_probe_display",
        lambda d: d is devices["media_player"]["echo"],
    )
    monkeypatch.setattr(
        switch_platform,
        "async_get_display_state",
        AsyncMock(return_value=SimpleNamespace(supports=lambda _setting: True)),
    )

    def mock_switch(unique_id):
        return lambda *_: SimpleNamespace(
            unique_id=unique_id, name=unique_id, is_on=False
        )

    for name, unique_id in (
        ("DNDSwitch", "dnd"),
        ("ShuffleSwitch", "shuffle"),
        ("RepeatSwitch", "repeat"),
        ("SmartSwitch", "plug"),
        ("LEDIndicatorSwitch", "aqm_led_indicator"),
        ("AlexaDisplayPowerSwitch", "display"),
        ("AlexaAdaptiveBrightnessSwitch", "brightness"),
        ("AmazonKidsSwitch", "kids"),
    ):
        monkeypatch.setattr(switch_platform, name, mock_switch(unique_id))
    return entry, account, kids


@pytest.mark.parametrize("failure", ["dnd", "aqm_led_indicator"])
async def test_retry_submits_only_missing_switches(mock_hass, switch_setup, failure):
    """A synchronous rejection must not poison caches or repeat accepted batches."""
    entry, account, _ = switch_setup
    queued = []

    def reject_one_batch(entities, update_before_add):
        assert not update_before_add
        ids = [entity.unique_id for entity in entities]
        if failure in ids:
            raise RuntimeError("Callback failed before queuing")
        queued.extend(ids)

    with pytest.raises(PlatformNotReady):
        await switch_platform.async_setup_entry(mock_hass, entry, reject_one_batch)

    tracked = account["entities"]
    assert {entity.unique_id for entity in tracked["smart_switch"]} == {
        entity_id for entity_id in queued if entity_id in {"plug", "aqm_led_indicator"}
    }

    def schedule(entities, _):
        queued.extend(entity.unique_id for entity in entities)

    await switch_platform.async_setup_entry(mock_hass, entry, schedule)
    await _drain_display_registration(account)
    # These are still pending in Home Assistant. No entity_id or state exists.
    await switch_platform.async_setup_entry(mock_hass, entry, schedule)
    await _drain_display_registration(account)
    assert queued == [
        "dnd",
        "shuffle",
        "repeat",
        "plug",
        "aqm_led_indicator",
        "display",
        "brightness",
    ]
    assert [e.unique_id for e in tracked["smart_switch"]] == [
        "plug",
        "aqm_led_indicator",
    ]


async def test_setup_waits_for_later_media_player(mock_hass, switch_setup):
    """A missing Echo client must leave earlier switch candidates available."""
    entry, account, _ = switch_setup
    account["devices"]["media_player"]["late"] = {}
    callback = MagicMock()
    with pytest.raises(PlatformNotReady):
        await switch_platform.async_setup_entry(mock_hass, entry, callback)
    callback.assert_not_called()
    assert account["entities"]["switch"] == {}

    account["entities"]["media_player"]["late"] = object()
    await switch_platform.async_setup_entry(mock_hass, entry, callback)
    await _drain_display_registration(account)
    assert callback.call_args_list[0].args[0][0].unique_id == "dnd"


async def test_kids_waiters_retry_and_deduplicate(mock_hass, switch_setup):
    """Two deferred waiters share accepted Amazon Kids entities by unique ID."""
    entry, account, kids = switch_setup
    kids_attempts = []

    def schedule(entities, _):
        if entities[0].unique_id == "kids":
            kids_attempts.append(entities[0])
            if len(kids_attempts) == 1:
                raise RuntimeError("Dashboard add callback could not schedule")

    await switch_platform.async_setup_entry(mock_hass, entry, schedule)
    await switch_platform.async_setup_entry(mock_hass, entry, schedule)
    first, second = (
        call.args[0] for call in kids.async_add_when_dashboard.await_args_list
    )
    assert not await first()
    assert account["entities"]["amazon_kids_switch"] == []
    assert await first()
    assert await second()
    assert len(kids_attempts) == 2
    assert account["entities"]["amazon_kids_switch"] == [kids_attempts[1]]


async def test_filtered_plug_is_not_tracked(mock_hass, switch_setup):
    """The polling collection contains only candidates given to Home Assistant."""
    entry, account, _ = switch_setup
    entry.data["include_devices"] = ["dnd", "Monitor"]
    await switch_platform.async_setup_entry(mock_hass, entry, MagicMock())
    assert [e.unique_id for e in account["entities"]["smart_switch"]] == [
        "aqm_led_indicator"
    ]


async def test_reload_resubmits_after_scheduled_add_fails(mock_hass, switch_setup):
    """A fresh account can submit the same IDs after HA discards the old platform."""
    entry, account, _ = switch_setup
    queued = []

    def schedule(entities, _):
        queued.extend(entities)

    await switch_platform.async_setup_entry(mock_hass, entry, schedule)
    old_entities = queued.copy()
    # Model the config-entry reload boundary: HA discards the queued add
    # work and AMP replaces the runtime account and its entity collections.
    reloaded = {
        **account,
        "entities": {
            "media_player": account["entities"]["media_player"],
            "switch": {},
            "smart_switch": [],
            "amazon_kids_switch": [],
        },
    }
    mock_hass.data[DATA_ALEXAMEDIA]["accounts"][entry.data["email"]] = reloaded
    queued.clear()
    await switch_platform.async_setup_entry(mock_hass, entry, schedule)

    assert [entity.unique_id for entity in queued] == [
        entity.unique_id for entity in old_entities
    ]
    assert all(new is not old for new, old in zip(queued, old_entities, strict=True))


async def test_non_display_switches_submit_before_display_probe(
    mock_hass, switch_setup, monkeypatch
):
    """Setup returns while display discovery is still running."""
    entry, account, _ = switch_setup
    started = asyncio.Event()
    release = asyncio.Event()

    async def slow_display(*_args, **_kwargs):
        started.set()
        await release.wait()
        return SimpleNamespace(supports=lambda _setting: True)

    monkeypatch.setattr(switch_platform, "async_get_display_state", slow_display)
    submitted = []

    def schedule(entities, _):
        submitted.extend(entity.unique_id for entity in entities)

    task = asyncio.create_task(
        switch_platform.async_setup_entry(mock_hass, entry, schedule)
    )
    await asyncio.wait_for(started.wait(), timeout=1)
    assert "dnd" in submitted
    assert "display" not in submitted
    # The background registration stays tracked for unload/removal cleanup.
    assert account["display_registration_switch"] in account["display_setup_tasks"]
    # Platform setup does not wait for the display probe.
    assert await asyncio.wait_for(task, timeout=1)

    release.set()
    await _drain_display_registration(account)
    assert "display" in submitted


async def test_display_probe_exception_keeps_setup_loaded(
    mock_hass, switch_setup, monkeypatch
):
    """A failing probe stays a background failure, not a platform failure."""
    entry, account, _ = switch_setup

    async def failing_display(*_args, **_kwargs):
        raise RuntimeError("probe failed")

    monkeypatch.setattr(switch_platform, "async_get_display_state", failing_display)
    add = MagicMock()

    assert await switch_platform.async_setup_entry(mock_hass, entry, add)
    await _drain_display_registration(account)
    # The filtered switches and the LED batch were submitted; no display batch.
    assert add.call_count == 2
    switches = account["entities"]["switch"].get("echo", {})
    assert "display_power" not in switches
    assert "adaptive_brightness" not in switches


async def test_setup_retry_cancels_previous_registration(
    mock_hass, switch_setup, monkeypatch
):
    """A setup retry cancels the previous background registration."""
    entry, account, _ = switch_setup
    started = asyncio.Event()
    release = asyncio.Event()

    async def slow_display(*_args, **_kwargs):
        started.set()
        await release.wait()
        return SimpleNamespace(supports=lambda _setting: True)

    monkeypatch.setattr(switch_platform, "async_get_display_state", slow_display)
    add = MagicMock()

    await switch_platform.async_setup_entry(mock_hass, entry, add)
    await asyncio.wait_for(started.wait(), timeout=1)
    previous = account["display_registration_switch"]

    await switch_platform.async_setup_entry(mock_hass, entry, add)
    await asyncio.wait_for(asyncio.gather(previous, return_exceptions=True), timeout=1)
    assert previous.cancelled()
    assert account["display_registration_switch"] is not previous

    release.set()
    await _drain_display_registration(account)


async def test_switch_setup_skips_replaced_display_state(
    mock_hass, switch_setup, monkeypatch
):
    """A state replaced after the probe gets no display switches."""
    entry, account, _ = switch_setup
    account["display_states"] = {"echo": object()}
    replacement = SimpleNamespace(supports=lambda _setting: True)
    monkeypatch.setattr(
        switch_platform, "async_get_display_state", AsyncMock(return_value=replacement)
    )
    add = MagicMock()

    await switch_platform.async_setup_entry(mock_hass, entry, add)
    await _drain_display_registration(account)
    switches = account["entities"]["switch"].get("echo", {})
    assert "display_power" not in switches
    assert "adaptive_brightness" not in switches


async def test_switch_setup_skips_retired_display_state(
    mock_hass, switch_setup, monkeypatch
):
    """A state retired during the probe gets no display switches."""
    entry, account, _ = switch_setup
    retired = SimpleNamespace(_stopped=True, supports=lambda _setting: True)
    monkeypatch.setattr(
        switch_platform, "async_get_display_state", AsyncMock(return_value=retired)
    )
    add = MagicMock()

    await switch_platform.async_setup_entry(mock_hass, entry, add)
    await _drain_display_registration(account)
    switches = account["entities"]["switch"].get("echo", {})
    assert "display_power" not in switches
    assert "adaptive_brightness" not in switches


async def test_display_add_failure_keeps_setup_loaded(mock_hass, switch_setup):
    """A failed display batch is retried later instead of failing setup."""
    entry, account, _ = switch_setup
    queued = []

    def reject_display(entities, _):
        ids = [entity.unique_id for entity in entities]
        if "display" in ids:
            raise RuntimeError("display add failed")
        queued.extend(ids)

    assert await switch_platform.async_setup_entry(mock_hass, entry, reject_display)
    await _drain_display_registration(account)
    switches = account["entities"]["switch"].get("echo", {})
    assert "display_power" not in switches
    assert "adaptive_brightness" not in switches

    await switch_platform.async_setup_entry(mock_hass, entry, reject_display)
    await _drain_display_registration(account)
    assert "display" not in queued

    def accept(entities, _):
        queued.extend(entity.unique_id for entity in entities)

    await switch_platform.async_setup_entry(mock_hass, entry, accept)
    await _drain_display_registration(account)
    assert "display" in queued


async def test_late_display_registration_dropped_after_removal(
    mock_hass, switch_setup, monkeypatch
):
    """A probe result that arrives after removal adds no entities."""
    entry, account, _ = switch_setup
    started = asyncio.Event()
    release = asyncio.Event()

    async def slow_display(*_args, **_kwargs):
        started.set()
        await release.wait()
        return SimpleNamespace(supports=lambda _setting: True)

    monkeypatch.setattr(switch_platform, "async_get_display_state", slow_display)
    add = MagicMock()

    await switch_platform.async_setup_entry(mock_hass, entry, add)
    await asyncio.wait_for(started.wait(), timeout=1)
    # Removal retires the runtime account record.
    mock_hass.data[DATA_ALEXAMEDIA]["accounts"].pop("test@example.com")
    add.reset_mock()

    release.set()
    await _drain_display_registration(account)
    add.assert_not_called()


async def test_kids_device_added_between_setups_registers_later(
    mock_hass, switch_setup, monkeypatch
):
    """A new Kids device is registered after its client appears."""
    entry, account, kids = switch_setup

    def kids_switch(_state, _login, client, _device_type):
        return SimpleNamespace(
            unique_id=f"kids-{client.device_serial_number}",
            name="kids",
            is_on=False,
        )

    monkeypatch.setattr(switch_platform, "AmazonKidsSwitch", kids_switch)

    def schedule(entities, _):
        # Discovery adds the device while the first setup submits its batch.
        account["devices"]["media_player"]["new-kids"] = {
            "deviceFamily": "ECHO",
            "deviceType": "echo-type",
        }

    await switch_platform.async_setup_entry(mock_hass, entry, schedule)
    await _drain_display_registration(account)
    assert account["entities"]["amazon_kids_switch"] == []

    account["entities"]["media_player"]["new-kids"] = SimpleNamespace(
        device_serial_number="new-kids"
    )
    await switch_platform.async_setup_entry(mock_hass, entry, MagicMock())
    await _drain_display_registration(account)

    callback = kids.async_add_when_dashboard.await_args_list[-1].args[0]
    await callback()
    added = {entity.unique_id for entity in account["entities"]["amazon_kids_switch"]}
    assert "kids-new-kids" in added
