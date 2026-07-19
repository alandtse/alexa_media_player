"""Protected at-rest storage for minimized device credentials.

SPDX-License-Identifier: Apache-2.0

The auth redesign (RFC #3523) persists only the durable device credentials the
runtime derives everything else from: the device ``refresh_token``, ``mac_dms``,
the device ``serial``, and the bound Amazon account identifier. They live in a
dedicated ``Store(private=True, atomic_writes=True)`` file rather than the shared
config entry so they are excluded from casual config sharing and diagnostics.

This is file-permission hygiene, not host-compromise protection: ``.storage`` is
included in Home Assistant backups, and anyone who can read the filesystem can
read these credentials. See the design doc for the honest threat model:
https://github.com/superbeetle1973/alexa-auth-redesign
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
_STORAGE_KEY_TMPL = f"{DOMAIN}.secure_credentials.{{entry_id}}"

# Keys of the minimized credential set persisted to the protected store.
CREDENTIAL_KEYS = ("refresh_token", "mac_dms", "serial", "customer_id", "domain")


class SecureCredentialStore:
    """Per-config-entry wrapper around a private HA Store.

    Holds the minimized ``DeviceCredentials`` for one Amazon account. The
    ``pending_validation`` flag lets migration write credentials before they
    have been proven against Amazon and clear it on the first successful
    refresh, per the lazy validate-then-delete migration design.
    """

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store = Store(
            hass,
            STORAGE_VERSION,
            _STORAGE_KEY_TMPL.format(entry_id=entry_id),
            private=True,
            atomic_writes=True,
        )
        self._data: dict[str, Any] | None = None

    async def async_load(self) -> dict[str, Any] | None:
        """Load the stored credential payload, or None if nothing is stored."""
        if self._data is None:
            self._data = await self._store.async_load()
        return self._data

    async def async_save(
        self, credentials: dict[str, Any], *, pending_validation: bool = False
    ) -> None:
        """Persist the minimized credential set atomically.

        Only the recognized credential keys are written; anything else in the
        supplied mapping (a stray password, cookies) is dropped rather than
        persisted.
        """
        payload = {key: credentials.get(key) for key in CREDENTIAL_KEYS}
        payload["pending_validation"] = pending_validation
        await self._store.async_save(payload)
        self._data = payload

    async def async_mark_validated(self) -> None:
        """Clear the pending-validation flag after a successful Amazon round-trip."""
        data = await self.async_load()
        if not data or not data.get("pending_validation"):
            return
        data = dict(data, pending_validation=False)
        await self._store.async_save(data)
        self._data = data

    async def async_remove(self) -> None:
        """Delete the protected store file (best-effort on teardown)."""
        await self._store.async_remove()
        self._data = None

    @property
    def key(self) -> str:
        """Storage key, exposed for diagnostics/tests."""
        return self._store.key
