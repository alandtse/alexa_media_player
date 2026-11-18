"""Tests for confirming a live HTTP/2 multipart directives stream."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.alexa_media.verified_http2 import observe_verified_stream


@pytest.mark.asyncio
async def test_rejected_response_does_not_publish_push_connected() -> None:
    """Plain-text failures cannot be mistaken for an accepted directives stream."""
    original = AsyncMock()
    verified_callback = AsyncMock()
    client = SimpleNamespace(boundary="", on_message=original)
    observe_verified_stream(client, verified_callback)

    await client.on_message("HTTP 503 Service Unavailable")
    original.assert_awaited_once()
    verified_callback.assert_not_awaited()

    # The parser observes a real multipart boundary only on a live stream.
    client.boundary = "------boundary"
    await client.on_message("------boundary\n")
    verified_callback.assert_awaited_once()

    await client.on_message("------boundary\n")
    verified_callback.assert_awaited_once()
