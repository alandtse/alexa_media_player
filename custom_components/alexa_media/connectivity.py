"""Account-owned Amazon connectivity observations; no network or scheduling."""

from collections.abc import Callable


class EchoConnectivityState:
    """Retain explicit observations, ignoring cache and in-flight stale inventory."""

    def __init__(self):
        """Initialize an empty observation store."""
        self.values: dict[str, bool | None] = {}
        self.account_available = True
        self.generation = 0
        self._invalidated_generation = -1
        self._push_generation: dict[str, int] = {}
        self._listeners: list[Callable] = []

    def add_listener(self, listener):
        """Subscribe until the returned removal callback is called."""
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    def notify(self):
        """Notify local observers without requesting coordinator updates."""
        for listener in tuple(self._listeners):
            listener()

    def invalidate(self):
        """Discard observations after account failure; cache cannot recover them."""
        self.account_available = False
        self.generation += 1
        self._invalidated_generation = self.generation
        self.values = dict.fromkeys(self.values)
        self.notify()

    def inventory(self, devices, generation, *, cached=False, previous_inventory=None):
        """Accept only real booleans from a fresh, existing inventory request."""
        cached = cached or devices is previous_inventory
        if generation < self._invalidated_generation:
            return
        for device in devices or []:
            serial = device.get("serialNumber")
            if not serial:
                continue
            self.values.setdefault(serial, None)
            if cached:
                continue
            # A push received while the request was in flight is newer.
            if self._push_generation.get(serial, -1) > generation:
                continue
            online = device.get("online")
            if type(online) is bool:
                self.values[serial] = online
        self.notify()

    def push(self, serial, payload):
        """Accept only explicit connection changes for known inventory serials."""
        if not isinstance(payload, dict):
            return
        status = payload.get("dopplerConnectionState")
        if serial not in self.values or status not in ("ONLINE", "OFFLINE"):
            return
        self.generation += 1
        self._push_generation[serial] = self.generation
        self.values[serial] = status == "ONLINE"
        self.notify()


def connectivity_state(account):
    """Return the store owned by this account, never by a media player."""
    if "echo_connectivity" not in account:
        account["echo_connectivity"] = EchoConnectivityState()
    return account["echo_connectivity"]
