"""HTTP/2 stream client that confirms multipart traffic before reporting push active.

alexapy 1.36.0 invokes open_callback for some non-success responses such as
HTTP 503, without exposing the response status to AMP. Observing the first
multipart boundary provides evidence of a real directives stream and avoids
publishing a false connection transition for rejected plain-text responses.
"""

from collections.abc import Awaitable, Callable

from alexapy import HTTP2EchoClient


class VerifiedHTTP2EchoClient(HTTP2EchoClient):
    """Only publish a verified connection after multipart traffic starts."""

    def __init__(
        self,
        *args,
        verified_callback: Callable[[], Awaitable[None]],
        **kwargs,
    ) -> None:
        """Initialize the transport with an account-scoped verification callback."""
        super().__init__(*args, **kwargs)
        self._verified_callback = verified_callback
        self._verified_stream = False

    async def on_message(self, message: str) -> None:
        """Verify actual directives stream content, not merely HTTP open."""
        await super().on_message(message)
        if self.boundary and not self._verified_stream:
            self._verified_stream = True
            await self._verified_callback()
