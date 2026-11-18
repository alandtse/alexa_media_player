"""Account-scoped observations for AMP's HTTP/2 push transport.

These are observed open/close events, not the heuristic used to choose
last_called polling. No network requests are made by subscribers.
"""

from collections.abc import Callable


def set_push_connected(account: dict, connected: bool) -> None:
    """Publish a change in the account's observed HTTP/2 connection state."""
    connected = bool(connected)
    if account.get("push_connected", False) == connected:
        return
    account["push_connected"] = connected
    for listener in tuple(account.get("push_connection_listeners", ())):
        listener()


def subscribe_push_connected(account: dict, listener: Callable[[], None]):
    """Subscribe to account connection changes; return an unsubscribe callback."""
    listeners = account.setdefault("push_connection_listeners", set())
    listeners.add(listener)

    def unsubscribe() -> None:
        listeners.discard(listener)

    return unsubscribe


def owns_push_attempt(hass, email: str, account: dict, attempt: object) -> bool:
    """Reject callbacks for an old connection, load or removed account."""
    return (
        hass.data.get("alexa_media", {}).get("accounts", {}).get(email) is account
        and account.get("push_attempt") is attempt
    )


def begin_push_attempt(account: dict) -> object:
    """Replace the current attempt token and return ownership to the caller."""
    token = object()
    account["push_attempt"] = token
    return token


def abandon_push_attempt(account: dict, attempt: object, client=None) -> None:
    """Release only a failed attempt, never invalidating a newer connection."""
    if account.get("push_attempt") is attempt:
        account["push_attempt"] = None
        set_push_connected(account, False)
    if client is not None:
        client.on_close()


def close_account_push(account: dict) -> None:
    """Invalidate callbacks and close the active transport during teardown."""
    account["push_attempt"] = None
    set_push_connected(account, False)
    client = account.get("http2")
    account["http2"] = None
    if client is not None:
        client.on_close()


def owns_push_account(hass, email: str, account: dict) -> bool:
    """Check account identity independently of its changing attempt token."""
    return hass.data.get("alexa_media", {}).get("accounts", {}).get(email) is account
