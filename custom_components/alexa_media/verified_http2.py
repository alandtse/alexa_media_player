"""Observe the HTTP/2 directives stream.

The alexapy 1.36.0 open callback can fire for a rejected HTTP response.
"""

from collections.abc import Awaitable, Callable


def observe_verified_stream(
    client, verified_callback: Callable[[], Awaitable[None]]
) -> None:
    """Notify once after the original client parses a multipart boundary."""
    original_on_message = client.on_message
    verified = False

    async def on_message(message: str) -> None:
        nonlocal verified
        await original_on_message(message)
        if not verified and client.boundary:
            verified = True
            await verified_callback()

    client.on_message = on_message
