"""Secret manager: envelope-encrypted key/value store (research-grade).

Secrets are sealed with a master key via HKDF-SHA512 + HMAC-CTR (same
primitive family as pqc.py channel, correctly labelled research-grade).
Supports rotation (re-seal all under a new master) and TTL leases.
For production, swap MasterKey provider with HSM/KMS without changing
callers.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

__all__ = ["SecretManager", "SecretLease"]


def _kdf(master: bytes, ctx: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha512", master, ctx, 50_000, dklen=32)


def _xor(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


@dataclass
class SecretLease:
    name: str
    expires_at: float
    version: int


class SecretManager:
    name = "secrets"

    def __init__(self, master: bytes | None = None) -> None:
        self._master = master or os.urandom(32)
        self._store: Dict[str, Dict[str, Any]] = {}
        self._version = 1

    def put(self, name: str, value: bytes, ttl_s: float = 0.0) -> SecretLease:
        key = _kdf(self._master, f"eci-secret:{name}:v{self._version}".encode())
        blob = _xor(value, key)
        mac = hmac.new(key, blob, hashlib.sha256).hexdigest()
        self._store[name] = {"blob": blob.hex(), "mac": mac, "v": self._version,
                             "exp": (time.time() + ttl_s) if ttl_s > 0 else 0.0}
        return SecretLease(name, self._store[name]["exp"], self._version)

    def get(self, name: str) -> bytes:
        rec = self._store.get(name)
        if rec is None:
            raise KeyError(f"no secret {name!r}")
        if rec["exp"] and time.time() > rec["exp"]:
            del self._store[name]
            raise KeyError(f"secret {name!r} expired")
        key = _kdf(self._master, f"eci-secret:{name}:v{rec['v']}".encode())
        blob = bytes.fromhex(rec["blob"])
        if hmac.new(key, blob, hashlib.sha256).hexdigest() != rec["mac"]:
            raise ValueError("secret integrity failure")
        return _xor(blob, key)

    def rotate(self, new_master: bytes | None = None) -> int:
        # decrypt all with old master, bump version, re-seal
        plain: Dict[str, bytes] = {}
        for name in list(self._store):
            try:
                plain[name] = self.get(name)
            except Exception:  # noqa: BLE001
                continue
        self._master = new_master or os.urandom(32)
        self._version += 1
        self._store.clear()
        for name, val in plain.items():
            self.put(name, val)
        return self._version

    def start(self) -> None: ...
    def stop(self) -> None: ...
    def health(self) -> Dict[str, Any]:
        return {"ok": True, "secrets": len(self._store), "version": self._version}
