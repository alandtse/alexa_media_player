"""Virtual Alexa Account device and Authentication diagnostic regression tests."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.alexa_media import (
    _register_account_device,
    account_device_identifier,
)
from custom_components.alexa_media.account_auth import (
    publish_authentication,
    subscribe_authentication,
)
from custom_components.alexa_media.const import DOMAIN
from custom_components.alexa_media.sensor import (
    AlexaAccountAuthenticationSensor,
    async_setup_entry,
)


def entry(identifier: str = "entry-one"):
    return SimpleNamespace(
        entry_id=identifier,
        data={"email": "example@example.com"},
        options={},
    )


def account(authenticated: bool = True):
    return {"login_obj": SimpleNamespace(status={"login_successful": authenticated})}


def test_account_identity_is_stable_and_private():
    first, second = entry("entry-one"), entry("entry-two")
    assert account_device_identifier(first) == (DOMAIN, "account_entry-one")
    assert account_device_identifier(first) != account_device_identifier(second)
    registry = MagicMock()
    hass = MagicMock()
    with patch("custom_components.alexa_media.dr.async_get", return_value=registry):
        _register_account_device(hass, first)
        _register_account_device(hass, first)
    assert registry.async_get_or_create.call_count == 2
    kwargs = registry.async_get_or_create.call_args.kwargs
    assert kwargs["identifiers"] == {(DOMAIN, "account_entry-one")}
    assert "example@example.com" not in kwargs["name"]
    assert kwargs["manufacturer"] == "Amazon"


def test_authentication_sensor_state_and_account_device():
    a = account()
    sensor = AlexaAccountAuthenticationSensor(a, entry())
    assert sensor.native_value == "authenticated"
    assert sensor.device_info["identifiers"] == {(DOMAIN, "account_entry-one")}
    assert sensor.unique_id == "entry-one_account_authentication"
    assert sensor.should_poll is False
    a["login_obj"].status["login_successful"] = False
    assert sensor.native_value == "not authenticated"
    a["login_obj"] = None
    assert sensor.native_value == "not authenticated"


def test_authentication_notifies_once_and_unsubscribes():
    a = account()
    listener = MagicMock()
    unsubscribe = subscribe_authentication(a, listener)
    publish_authentication(a)
    listener.assert_called_once()
    publish_authentication(a)
    listener.assert_called_once()
    a["login_obj"].status["login_successful"] = False
    publish_authentication(a)
    assert listener.call_count == 2
    unsubscribe()
    a["login_obj"].status["login_successful"] = True
    publish_authentication(a)
    assert listener.call_count == 2


@pytest.mark.asyncio
async def test_sensor_platform_adds_account_without_echoes():
    e = entry()
    a = account()
    a["entities"] = {"media_player": {}, "sensor": {}}
    a["devices"] = {"media_player": {}}
    hass = SimpleNamespace(data={DOMAIN: {"accounts": {e.data["email"]: a}}})
    add = MagicMock()
    with patch(
        "custom_components.alexa_media.sensor.async_setup_platform",
        new_callable=AsyncMock,
        return_value=True,
    ):
        assert await async_setup_entry(hass, e, add)
        assert await async_setup_entry(hass, e, add)
    add.assert_called_once()
    assert isinstance(add.call_args.args[0][0], AlexaAccountAuthenticationSensor)
    assert a["sensor_add_devices"] is add
    assert a["account_sensor_forwarded"] is True


@pytest.mark.asyncio
async def test_failed_sensor_platform_does_not_mark_account_loaded():
    e = entry()
    a = account()
    hass = SimpleNamespace(data={DOMAIN: {"accounts": {e.data["email"]: a}}})
    add = MagicMock()
    with patch(
        "custom_components.alexa_media.sensor.async_setup_platform",
        new_callable=AsyncMock,
        return_value=False,
    ):
        assert not await async_setup_entry(hass, e, add)
    add.assert_not_called()
    assert not a.get("account_sensor_forwarded")
