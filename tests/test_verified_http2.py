"""Tests for confirming an accepted HTTP/2 multipart directives stream."""

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.alexa_media.verified_http2 import observe_verified_stream


@pytest.mark.asyncio
async def test_rejected_response_does_not_publish_push_connected() -> None:
    """Only a successfully accepted response with a parsed boundary can connect."""
    original = AsyncMock()
    callback = AsyncMock()
    client = SimpleNamespace(boundary="", on_message=original)

    @asynccontextmanager
    async def stream(*args, **kwargs):
        yield SimpleNamespace(status_code=args[0])

    client.client = SimpleNamespace(stream=stream)

    async def parsed_message(message):
        if message.startswith("------"):
            client.boundary = "------boundary"

    original.side_effect = parsed_message
    observe_verified_stream(client, callback)

    # Rejected HTTP response cannot become Connected even if it contains a
    # multipart-looking line.
    async with client.client.stream(503):
        await client.on_message("HTTP 503 Service Unavailable")
        callback.assert_not_awaited()

    async with client.client.stream(200):
        await client.on_message("------boundary\n")
        callback.assert_awaited_once()
        await client.on_message("------boundary\n")
        callback.assert_awaited_once()

    async with client.client.stream(503):
        await client.on_message("------boundary\n")
        callback.assert_awaited_once()


@pytest.mark.asyncio
async def test_boundary_on_rejected_response_is_not_sufficient() -> None:
    """A boundary parsed from a rejected HTTP response cannot signal Connected."""
    client = SimpleNamespace(boundary="", on_message=AsyncMock())
    callback = AsyncMock()

    @asynccontextmanager
    async def stream(*args, **kwargs):
        yield SimpleNamespace(status_code=503)

    client.client = SimpleNamespace(stream=stream)

    async def parse(_message):
        client.boundary = "------boundary"

    client.on_message.side_effect = parse
    observe_verified_stream(client, callback)
    async with client.client.stream():
        await client.on_message("------boundary\n")
    callback.assert_not_awaited()
