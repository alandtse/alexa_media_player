"""Observe the HTTP/2 directives stream.

The alexapy 1.36.0 open callback can fire for a rejected HTTP response.
"""

from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager


def observe_verified_stream(
    client, verified_callback: Callable[[], Awaitable[None]]
) -> None:
    """Notify only after a successful response AND a parsed multipart boundary."""
    original_stream = client.client.stream
    original_on_message = client.on_message
    accepted = False
    verified = False

    @asynccontextmanager
    async def observed_stream(*args, **kwargs):
        nonlocal accepted
        accepted = False
        async with original_stream(*args, **kwargs) as response:
            accepted = response.status_code == 200
            yield response
        accepted = False

    async def on_message(message: str) -> None:
        nonlocal verified
        await original_on_message(message)
        if accepted and not verified and client.boundary:
            verified = True
            await verified_callback()

    client.client.stream = observed_stream
    client.on_message = on_message
