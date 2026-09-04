"""Sovereign architect identity and cryptographic stamping.

Every subsystem of the ECI Framework embeds the architect's identity:
node identifiers are derived from a keyed SHA-512 chain, consensus
records carry the architect stamp, and module metadata exposes it.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from eci.constants import ARCHITECT_NAME, ARCHITECT_SIGNATURE, ARCHITECT_TITLE, CREATOR_WALLET

__all__ = ["ArchitectIdentity", "ARCHITECT"]


@dataclass(frozen=True)
class ArchitectIdentity:
    """Immutable identity of the sovereign architect.

    The ``_key`` is a canonical digest of the identity fields; every stamp
    is ``SHA-512(key || canonical_payload || timestamp)`` which makes stamps
    deterministic for identical payloads (auditable) and unforgeable for
    different payloads.
    """

    name: str = ARCHITECT_NAME
    title: str = ARCHITECT_TITLE
    wallet: str = CREATOR_WALLET
    signature: str = ARCHITECT_SIGNATURE
    _key: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        if not self._key:
            canonical = json.dumps(
                {
                    "name": self.name,
                    "title": self.title,
                    "wallet": self.wallet,
                    "signature": self.signature,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
            object.__setattr__(self, "_key", hashlib.sha512(canonical.encode()).hexdigest())

    @property
    def key(self) -> str:
        return self._key

    def stamp(self, payload: Any, timestamp: Optional[float] = None) -> Dict[str, Any]:
        """Produce an auditable architect stamp for an arbitrary payload."""
        if timestamp is None:
            timestamp = time.time()
        canonical = json.dumps(
            payload,
            sort_keys=True,
            default=str,
            separators=(",", ":"),
        )
        digest = hashlib.sha512(
            f"{self._key}|{canonical}|{timestamp}".encode()
        ).hexdigest()
        return {
            "architect": self.name,
            "title": self.title,
            "wallet": self.wallet,
            "signature": self.signature,
            "timestamp": timestamp,
            "digest": digest,
        }

    def derive_id(self, prefix: str, payload: Any) -> str:
        """Deterministic, collision-resistant identifier keyed by the architect."""
        canonical = json.dumps(
            {"payload": payload, "wallet": self.wallet},
            sort_keys=True,
            default=str,
            separators=(",", ":"),
        )
        digest = hashlib.sha512(f"{self._key}|{canonical}".encode()).hexdigest()
        return f"{prefix}_{digest[:24]}"

    def verify(self, payload: Any, digest: str, timestamp: float) -> bool:
        """Verify a stamp produced by :meth:`stamp`."""
        canonical = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
        expected = hashlib.sha512(f"{self._key}|{canonical}|{timestamp}".encode()).hexdigest()
        return expected == digest

    def to_dict(self) -> Dict[str, str]:
        return {
            "name": self.name,
            "title": self.title,
            "wallet": self.wallet,
            "signature": self.signature,
            "key_fingerprint": self._key[:16],
        }


#: Process-wide sovereign architect identity.
ARCHITECT = ArchitectIdentity()
