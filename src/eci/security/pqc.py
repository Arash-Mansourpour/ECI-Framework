"""Post-quantum cryptography suite (crypto-agile, research grade).

This module implements what can be implemented correctly in pure Python:

* **Hash-based signatures** - a WOTS+-inspired one-time signature over
  SHA-256 chains (the same family as NIST FIPS 205 / SLH-DSA, simplified
  for research use).
* **Key derivation** - HKDF-style extract-and-expand over HMAC-SHA-512.
* **Adapter interface** for standardized ML-KEM / ML-DSA via the
  ``liboqs-python`` package when it is installed.

The symmetric "secure channel" provided here is a *research simulation*
(HMAC-SHA256 keystream); it must not protect production traffic - use a
real TLS/ML-KEM stack for that.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from eci.core.identity import ARCHITECT
from eci.logging import get_logger

__all__ = ["HashBasedSigner", "derive_key", "SecureChannel", "PQCSuite"]

try:  # optional adapter for the NIST-standardized implementations
    import oqs  # type: ignore

    _OQS_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    oqs = None  # type: ignore
    _OQS_AVAILABLE = False


# ---------------------------------------------------------------------------
# Key derivation (HKDF-style)
# ---------------------------------------------------------------------------

def _hmac_sha512(key: bytes, data: bytes) -> bytes:
    return hmac.new(key, data, hashlib.sha512).digest()


def derive_key(
    ikm: bytes,
    salt: bytes = b"ECI-v4-key-derivation",
    info: bytes = b"eci-session",
    length: int = 32,
) -> bytes:
    """HKDF-style extract-then-expand over HMAC-SHA-512."""
    prk = _hmac_sha512(salt, ikm)
    okm = b""
    t = b""
    counter = 1
    while len(okm) < length:
        t = _hmac_sha512(prk, t + info + bytes([counter]))
        okm += t
        counter += 1
    return okm[:length]


# ---------------------------------------------------------------------------
# Hash-based one-time signatures (WOTS+-inspired)
# ---------------------------------------------------------------------------

_W = 16  # Winternitz parameter (4-bit chains)
_N = 32  # hash output bytes


def _chain(seed: bytes, steps: int) -> bytes:
    value = seed
    for _ in range(steps):
        value = hashlib.sha256(value).digest()
    return value


class HashBasedSigner:
    """WOTS+-style one-time hash-based signature (SLH-DSA family)."""

    def __init__(self, seed: Optional[bytes] = None) -> None:
        self.seed = seed if seed is not None else secrets.token_bytes(_N)
        self.logger = get_logger("security.pqc")

    # Key layout: len = ceil(256 / 4) + 2 checksum chains
    @staticmethod
    def _message_chunks(message: bytes) -> Tuple[list, int]:
        digest = hashlib.sha256(message).digest()
        chunks = [digest[i] // _W for i in range(_N)]
        checksum = sum((_W - 1 - c) for c in chunks)
        checksum_chunks = []
        while checksum > 0:
            checksum_chunks.append(checksum % _W)
            checksum //= _W
        return chunks + checksum_chunks, len(chunks)

    def _chain_len(self) -> int:
        # 32 message nibble-chains + up to 2 checksum chains
        return _N + 2

    def sign(self, message: bytes) -> Dict[str, bytes]:
        """One-time signature: publish the end-of-chain values for the message."""
        if self.seed is None:
            raise RuntimeError("signer already used (one-time key consumed)")
        chunks, n_msg = self._message_chunks(message)
        signature_chains = []
        for i, c in enumerate(chunks):
            chain_seed = _hmac_sha512(self.seed, f"chain-{i}".encode())[:_N]
            signature_chains.append(_chain(chain_seed, c))
        sig = b"".join(signature_chains)
        self.seed = None  # one-time use
        return {"signature": sig, "n_msg": n_msg.to_bytes(2, "big")}

    def public_key(self) -> Dict[str, bytes]:
        """Public verification key: end-of-max-chain values for each chain."""
        pks = []
        for i in range(self._chain_len()):
            chain_seed = _hmac_sha512(self.seed or b"", f"chain-{i}".encode())[:_N]
            pks.append(_chain(chain_seed, _W - 1))
        return {"public_chains": b"".join(pks)}

    def verify_with_pk(self, message: bytes, signature: Dict[str, bytes], public_key: Dict[str, bytes]) -> bool:
        """Verify the signature by completing each chain to the public end."""
        chunks, _ = self._message_chunks(message)
        sig = signature["signature"]
        pk = public_key["public_chains"]
        for i, c in enumerate(chunks):
            seg = sig[i * _N:(i + 1) * _N]
            expected = pk[i * _N:(i + 1) * _N]
            if _chain(seg, _W - 1 - c) != expected:
                return False
        return True


# ---------------------------------------------------------------------------
# Research-grade secure channel
# ---------------------------------------------------------------------------

class SecureChannel:
    """HMAC-SHA256-CTR style symmetric channel (research simulation only).

    Both sides derive the same key via :func:`derive_key` from a shared
    secret; messages are keystream-encrypted and HMAC-authenticated.
    """

    def __init__(self, shared_secret: bytes) -> None:
        self.enc_key = derive_key(shared_secret, info=b"eci-enc")
        self.mac_key = derive_key(shared_secret, info=b"eci-mac")

    def _keystream(self, nonce: bytes, length: int) -> bytes:
        stream = b""
        counter = 0
        while len(stream) < length:
            stream += hmac.new(self.enc_key, nonce + counter.to_bytes(8, "big"), hashlib.sha256).digest()
            counter += 1
        return stream[:length]

    def encrypt(self, plaintext: bytes) -> Tuple[bytes, bytes, bytes]:
        nonce = os.urandom(16)
        ks = self._keystream(nonce, len(plaintext))
        ciphertext = bytes(a ^ b for a, b in zip(plaintext, ks))
        tag = hmac.new(self.mac_key, nonce + ciphertext, hashlib.sha256).digest()
        return nonce, ciphertext, tag

    def decrypt(self, nonce: bytes, ciphertext: bytes, tag: bytes) -> Optional[bytes]:
        expected = hmac.new(self.mac_key, nonce + ciphertext, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, tag):
            return None
        ks = self._keystream(nonce, len(ciphertext))
        return bytes(a ^ b for a, b in zip(ciphertext, ks))


# ---------------------------------------------------------------------------
# Crypto-agile suite
# ---------------------------------------------------------------------------

@dataclass
class PQCSuite:
    """Facade over available post-quantum primitives."""

    signer: HashBasedSigner = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.signer is None:
            self.signer = HashBasedSigner()
        self.logger = get_logger("security.pqc")
        self.logger.info("PQC suite ready (oqs_available=%s)", _OQS_AVAILABLE)

    @property
    def capabilities(self) -> Dict[str, bool]:
        return {
            "hash_based_signatures": True,
            "ml_kem_adapter": _OQS_AVAILABLE,
            "ml_dsa_adapter": _OQS_AVAILABLE,
            "secure_channel": True,
            "architect_bound": True,
        }

    def architect_signed_token(self, payload: bytes) -> Dict[str, bytes]:
        """Sign a payload under the architect's one-time hash-based key."""
        pk = self.signer.public_key()
        sig = self.signer.sign(ARCHITECT.name.encode() + b":" + payload)
        return {"payload": payload, "signature": sig["signature"], "public_key": pk["public_chains"]}

    def verify_architect_token(self, token: Dict[str, bytes]) -> bool:
        verifier = HashBasedSigner(seed=b"\x00")
        payload = token["payload"]
        return verifier.verify_with_pk(
            ARCHITECT.name.encode() + b":" + payload,
            {"signature": token["signature"]},
            {"public_chains": token["public_key"]},
        )
