"""Tests for the Echo reboot request helper."""

from unittest.mock import AsyncMock, MagicMock, patch

from alexapy import AlexapyLoginError
import pytest

from custom_components.alexa_media.helpers import async_restart_device

EMAIL = "test@example.com"  # noqa: S105
SERIAL = "G090XXXXXXXXXXXX"
DEVICE_TYPE = "A3S5BH2HU6VAYF"


class FakeResponse:
    """Minimal async context manager for aiohttp responses."""

    def __init__(self, status=200):
        self.status = status
        self.text = AsyncMock(return_value="failure")

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return False


@pytest.mark.asyncio
async def test_restart_refreshes_token_then_sends_bearer_request():
    """The helper refreshes auth first and sends the expected reboot payload."""
    calls = []
    login = MagicMock()
    login.url = "amazon.com"
    login.access_token = "old-token"  # nosec B105
    login._ssl = False
    login.session = MagicMock()
    login.session.post.return_value = FakeResponse(200)

    async def _auth(_login):
        calls.append("auth")
        login.access_token = "new-token"  # nosec B105

    login.session.post.side_effect = lambda *args, **kwargs: (
        calls.append("post") or FakeResponse(200)
    )

    with patch(
        "custom_components.alexa_media.helpers.AlexaAPI.get_authentication",
        side_effect=_auth,
    ):
        assert await async_restart_device(login, DEVICE_TYPE, SERIAL)

    assert calls == ["auth", "post"]
    args, kwargs = login.session.post.call_args
    assert args[0] == (
        "https://alexa.amazon.com/v1/alexa/device/reboot/" f"{DEVICE_TYPE}/{SERIAL}"
    )
    assert kwargs["headers"]["authorization"] == "Bearer new-token"
    assert kwargs["json"] == {
        "deviceSerialNumber": SERIAL,
        "deviceType": DEVICE_TYPE,
    }
    assert kwargs["ssl"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [400, 404, 429, 500])
async def test_restart_returns_false_for_non_2xx(status):
    """A rejected reboot returns False instead of claiming success."""
    login = MagicMock()
    login.email = EMAIL
    login.url = "amazon.com"
    login.access_token = "token"  # nosec B105
    login._ssl = False
    login.session = MagicMock()
    login.session.post.return_value = FakeResponse(status)

    with patch(
        "custom_components.alexa_media.helpers.AlexaAPI.get_authentication",
        new_callable=AsyncMock,
    ):
        assert not await async_restart_device(login, DEVICE_TYPE, SERIAL)


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [401, 403])
async def test_restart_raises_for_authentication_failure(status):
    """Rejected credentials propagate to the button's relogin handling."""
    login = MagicMock()
    login.url = "amazon.com"
    login.access_token = "token"  # nosec B105
    login.session.post.return_value = FakeResponse(status)

    with patch(
        "custom_components.alexa_media.helpers.AlexaAPI.get_authentication",
        new_callable=AsyncMock,
    ):
        with pytest.raises(AlexapyLoginError, match=f"HTTP {status}"):
            await async_restart_device(login, DEVICE_TYPE, SERIAL)
