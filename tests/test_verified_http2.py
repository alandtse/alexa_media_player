"""Tests for confirming a live HTTP/2 multipart directives stream."""

from unittest.mock import AsyncMock, patch

from alexapy import HTTP2EchoClient
import pytest

from custom_components.alexa_media.verified_http2 import VerifiedHTTP2EchoClient


@pytest.mark.asyncio
async def test_rejected_response_does_not_publish_push_connected() -> None:
    """Plain-text failure responses must not be mistaken for a push stream."""
    client = object.__new__(VerifiedHTTP2EchoClient)
    client.boundary = ""
    client._verified_stream = False
    client._verified_callback = AsyncMock()

    with patch.object(HTTP2EchoClient, "on_message", new_callable=AsyncMock):
        await client.on_message("HTTP 503 Service Unavailable")
        client._verified_callback.assert_not_awaited()

        # Real multipart traffic confirms the stream, exactly once.
        client.boundary = "------boundary"
        await client.on_message("------boundary\n")
        client._verified_callback.assert_awaited_once()

        await client.on_message("------boundary\n")
        client._verified_callback.assert_awaited_once()
