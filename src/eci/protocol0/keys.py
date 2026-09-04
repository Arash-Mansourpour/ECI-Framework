"""Asymmetric agent keys: Ed25519 when available, HMAC fallback otherwise.

Backend preference: ``cryptography`` (Ed25519, real signatures) — already a
transitive dependency of most stacks; ML-DSA-65 via liboqs upgrades the
*architect anchor* when installed (see attest.architect_anchor_available).
Every function reports ``mechanism`` so callers never mistake research-grade
HMAC for a signature. Keys are raw 32-byte seeds (never logged).
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from typing import Dict, Tuple

__all__ = ["KeyPair", "generate", "sign", "verify", "mechanism"]

try:  # real signatures
    from cryptography.exceptions import InvalidSignature as _InvalidSig
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey as _Priv,
    )

    _ED = True
except Exception:  # pragma: no cover
    _ED = False


def mechanism() -> str:
    return "Ed25519/cryptography" if _ED else "HMAC-SHA256(research-fallback)"


@dataclass
class KeyPair:
    private_bytes: bytes
    public_bytes: bytes

    def public_hex(self) -> str:
        return self.public_bytes.hex()


def generate() -> KeyPair:
    if _ED:
        priv = _Priv.generate()
        pub = priv.public_key()
        from cryptography.hazmat.primitives import serialization as _ser

        return KeyPair(
            private_bytes=priv.private_bytes(_ser.Encoding.Raw, _ser.PrivateFormat.Raw, _ser.NoEncryption()),
            public_bytes=pub.public_bytes(_ser.Encoding.Raw, _ser.PublicFormat.Raw),
        )
    seed = secrets.token_bytes(32)
    return KeyPair(private_bytes=seed, public_bytes=hashlib.sha256(b"p0-pub|" + seed).digest())


def sign(kp: KeyPair, message: bytes) -> bytes:
    if _ED:
        from cryptography.hazmat.primitives import serialization as _ser

        priv = _Priv.from_private_bytes(kp.private_bytes)
        return priv.sign(message)
    return hmac.new(kp.private_bytes, message, hashlib.sha256).digest()


def verify(public_bytes: bytes, message: bytes, signature: bytes, private_hint: bytes | None = None) -> Dict:
    """Verify. HMAC fallback needs the private seed as hint (documented)."""
    if _ED:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey as _Pub

        try:
            _Pub.from_public_bytes(public_bytes).verify(signature, message)
            return {"ok": True, "mechanism": mechanism()}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "reason": str(e), "mechanism": mechanism()}
    if private_hint is None:
        return {"ok": False, "reason": "HMAC fallback needs private_hint", "mechanism": mechanism()}
    expect = hmac.new(private_hint, message, hashlib.sha256).digest()
    return {"ok": hmac.compare_digest(expect, signature), "reason": "" if hmac.compare_digest(expect, signature) else "bad mac",
            "mechanism": mechanism()}


def fingerprint(public_bytes: bytes) -> str:
    return hashlib.sha256(b"p0-fp|" + public_bytes).hexdigest()[:16]
