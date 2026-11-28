"""Account authentication state change notifications."""

from collections.abc import Callable


def publish_authentication(account: dict) -> None:
    """Notify listeners only when authentication changes."""
    login = account.get("login_obj")
    authenticated = bool(login and login.status.get("login_successful"))
    if account.get("_last_authentication_state") is authenticated:
        return
    account["_last_authentication_state"] = authenticated
    for listener in tuple(account.get("authentication_listeners", ())):
        listener()


def subscribe_authentication(account: dict, listener: Callable[[], None]):
    """Subscribe to changes, returning a cleanup callback."""
    listeners = account.setdefault("authentication_listeners", set())
    listeners.add(listener)

    def unsubscribe() -> None:
        listeners.discard(listener)

    return unsubscribe
