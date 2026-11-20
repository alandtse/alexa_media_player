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


def cancel_account_reconnect(account: dict) -> None:
    """Stop any previously scheduled reconnect when an entry unloads."""
    import asyncio

    task = account.get("push_reconnect_task")
    if task is not None and task is not asyncio.current_task() and not task.done():
        task.cancel()


async def reconnect_account_push(
    hass,
    email: str,
    account: dict,
    login_obj,
    connect,
    *,
    sleep=None,
    clock=None,
) -> bool | None:
    """Reconnect only while this task owns an active account's transport."""
    import asyncio
    import time

    sleep = sleep or asyncio.sleep
    clock = clock or time.time
    task = asyncio.current_task()
    previous = account.get("push_reconnect_task")
    if previous is not None and previous is not task and not previous.done():
        return None

    def active() -> bool:
        return owns_push_account(hass, email, account) and not login_obj.close_requested

    if not active():
        return None
    account["push_reconnect_task"] = task
    try:
        close_account_push(account)
        if not login_obj.status.get("login_successful"):
            return False
        errors = account["http2error"]
        delay = 5 * 2**errors
        if clock() - account["http2_lastattempt"] < delay:
            return False
        while errors < 5:
            if not active():
                return None
            account["http2_lastattempt"] = clock()
            client = await connect()
            if not active() or (
                client is not None
                and getattr(client, "_amp_attempt", None)
                is not account.get("push_attempt")
            ):
                if client is not None:
                    client.on_close()
                return None
            account["http2"] = client
            if client is not None:
                return True
            errors = account["http2error"] = account["http2error"] + 1
            delay = 5 * 2**errors
            await sleep(delay)
            if not active():
                return None
        return False
    finally:
        if account.get("push_reconnect_task") is task:
            account["push_reconnect_task"] = None


async def open_owned_push(hass, email: str, account: dict, attempt: object, client):
    """Retire failed or displaced HTTP/2 open attempts before callbacks can act."""
    try:
        await client.async_run()
    except BaseException:
        abandon_push_attempt(account, attempt, client)
        raise
    if not owns_push_attempt(hass, email, account, attempt):
        abandon_push_attempt(account, attempt, client)
        return None
    client._amp_attempt = attempt
    return client
