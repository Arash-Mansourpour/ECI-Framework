"""Sovereign architect identity and cryptographic stamping.

Two tiers, honestly labeled:

- **legacy-sha512** (default, no secret configured): the original
  ``SHA-512(key || canonical || timestamp)`` attribution label. Anyone with
  the source reproduces it — it proves *lineage*, not *authentication*.
  Every stamp carries ``"alg": "legacy-sha512"`` so verifiers never mistake
  it for a signature.
- **ed25519** (when ``ECI_ARCHITECT_SEED`` hex or ``ECI_ARCHITECT_KEYFILE``
  provides a 32-byte seed): real Ed25519 signatures via ``protocol0.keys``,
  with ``kid`` key-ids, domain-separated subkeys (HKDF), rotation history,
  and a ``did:eci:`` document. Third parties verify with the public key alone.

Every subsystem embeds this identity: node ids derive from it, consensus
records carry its stamps, module metadata exposes it.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any

from eci.constants import ARCHITECT_NAME, ARCHITECT_SIGNATURE, ARCHITECT_TITLE, CREATOR_WALLET

__all__ = ["ArchitectIdentity", "ARCHITECT", "LEGACY_ALG", "ED_ALG"]

LEGACY_ALG = "legacy-sha512"
ED_ALG = "ed25519"

_ENV_SEED = "ECI_ARCHITECT_SEED"
_ENV_KEYFILE = "ECI_ARCHITECT_KEYFILE"


def _read_seed() -> bytes | None:
    """Load a 32-byte architect seed from env/file. Never logged, never raised."""
    try:
        raw = os.environ.get(_ENV_SEED, "").strip()
        if not raw and os.environ.get(_ENV_KEYFILE, "").strip():
            with open(os.environ[_ENV_KEYFILE.strip()], "rb") as fh:
                raw = fh.read().decode("utf-8", errors="ignore").strip()
        if not raw:
            return None
        seed = bytes.fromhex(raw[:64] if len(raw) >= 64 else raw)
        return seed if len(seed) == 32 else None
    except Exception:  # noqa: BLE001
        return None


def _hkdf(seed: bytes, info: bytes, length: int = 32) -> bytes:
    """HKDF-SHA256 (RFC 5869). Uses cryptography when present, else pure-python."""
    try:
        from cryptography.hazmat.primitives import hashes as _h
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF as _HKDF

        return _HKDF(algorithm=_h.SHA256(), length=length, salt=b"eci-architect-v1", info=info).derive(seed)
    except Exception:  # noqa: BLE001
        prk = hmac.new(b"eci-architect-v1", seed, hashlib.sha256).digest()
        out, counter, prev = b"", 1, b""
        while len(out) < length:
            prev = hmac.new(prk, prev + info + bytes([counter]), hashlib.sha256).digest()
            out += prev
            counter += 1
        return out[:length]


@dataclass(frozen=True)
class ArchitectIdentity:
    """Immutable identity of the sovereign architect.

    The ``_key`` is a canonical digest of the identity fields; legacy stamps
    are ``SHA-512(key || canonical_payload || timestamp)`` — deterministic for
    identical payloads (auditable). v2 adds real signatures when a seed is
    configured (see module docstring).
    """

    name: str = ARCHITECT_NAME
    title: str = ARCHITECT_TITLE
    wallet: str = CREATOR_WALLET
    signature: str = ARCHITECT_SIGNATURE
    _key: str = field(default="", repr=False)
    _kid: str = field(default="genesis", repr=False)
    _keys: Any = field(default=None, repr=False, compare=False)

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
        if self._keys is None:
            object.__setattr__(self, "_keys", _KeyRing(self._key))

    @property
    def key(self) -> str:
        return self._key

    @property
    def kid(self) -> str:
        return self._keys.active_kid if self._keys else self._kid

    @property
    def alg(self) -> str:
        return ED_ALG if (self._keys and self._keys.ed_ready) else LEGACY_ALG

    # -- legacy attribution label (unchanged semantics, now labeled) --
    def stamp(self, payload: Any, timestamp: float | None = None) -> dict[str, Any]:
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
            "alg": LEGACY_ALG,
            "kid": self.kid,
        }

    def verify(self, payload: Any, digest: str, timestamp: float) -> bool:
        """Verify a legacy stamp produced by :meth:`stamp`."""
        canonical = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
        expected = hashlib.sha512(f"{self._key}|{canonical}|{timestamp}".encode()).hexdigest()
        return hmac.compare_digest(expected, digest)

    # -- v2 real signatures (ed25519 when a seed is configured) --
    def sign(self, payload: Any, domain: str = "default",
             timestamp: float | None = None) -> dict[str, Any]:
        """Sign a payload. Real signature in ed25519 mode, labeled legacy otherwise."""
        if timestamp is None:
            timestamp = time.time()
        canonical = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
        assert self._keys is not None
        return self._keys.sign(self, canonical, domain=domain, timestamp=timestamp)

    def verify_signature(self, payload: Any, envelope: dict[str, Any],
                         max_age_s: float | None = None) -> dict[str, Any]:
        """Verify a :meth:`sign` envelope. Returns ``{ok, alg, kid, reason}``."""
        canonical = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
        assert self._keys is not None
        return self._keys.verify(canonical, envelope, max_age_s=max_age_s)

    def subkey(self, domain: str) -> str:
        """Domain-separated 32-byte subkey (hex) — limits blast radius per use."""
        assert self._keys is not None
        return self._keys.subkey(domain)

    def rotate(self, new_seed_hex: str) -> "ArchitectIdentity":
        """Return a successor identity with a new active key (old keys stay verifiable)."""
        assert self._keys is not None
        seed = bytes.fromhex(new_seed_hex.strip())
        if len(seed) != 32:
            raise ValueError("rotation seed must be 32 bytes hex")
        new_ring = self._keys.rotated(seed)
        return ArchitectIdentity(name=self.name, title=self.title, wallet=self.wallet,
                                 signature=self.signature, _key=self._key,
                                 _kid=new_ring.active_kid, _keys=new_ring)

    def did(self) -> dict[str, Any]:
        """Decentralized identifier document for third-party verification."""
        assert self._keys is not None
        return self._keys.did_document(self)

    def key_status(self) -> dict[str, Any]:
        assert self._keys is not None
        return self._keys.status()

    # -- identifiers --
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

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "title": self.title,
            "wallet": self.wallet,
            "signature": self.signature,
            "key_fingerprint": self._key[:16],
            "alg": self.alg,
            "kid": self.kid,
            "did": str(self.did().get("id", "")),
        }


class _KeyRing:
    """Seed-backed Ed25519 keys with rotation. Reads env once; never logs seeds."""

    def __init__(self, legacy_key: str, seed: bytes | None = None, _history: Any = None,
                 _skip_env: bool = False) -> None:
        from eci.protocol0 import keys as _keys_mod

        self._mod = _keys_mod
        self.legacy_key = legacy_key
        self.active_kid = "genesis"
        self._pairs: dict[str, Any] = {}
        self._history: list[dict[str, str]] = list(_history or [])
        env_seed = seed if (seed is not None or _skip_env) else _read_seed()
        self.ed_ready = False
        if env_seed is not None:
            self._activate("genesis", env_seed, note="env/file seed")
        self.ed_ready = bool(self._pairs) and self._mod.mechanism().startswith("Ed25519")

    def _activate(self, kid: str, seed: bytes, note: str) -> None:
        try:
            from cryptography.hazmat.primitives import serialization as _ser
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey as _Priv

            priv = _Priv.from_private_bytes(seed)
            pub = priv.public_key().public_bytes(_ser.Encoding.Raw, _ser.PublicFormat.Raw)
        except Exception:  # noqa: BLE001
            pub = hashlib.sha256(b"eci-pub-fallback|" + bytes(seed)).digest()
        self._pairs[kid] = {"seed": bytes(seed), "public": bytes(pub)}
        self.active_kid = kid
        self._history.append({"kid": kid, "public_hex": bytes(pub).hex(),
                              "fingerprint": hashlib.sha256(b"eci-kid|" + bytes(pub)).hexdigest()[:16],
                              "note": note})

    def rotated(self, new_seed: bytes) -> "_KeyRing":
        ring = _KeyRing(self.legacy_key, seed=None, _history=self._history, _skip_env=True)
        ring._pairs = dict(self._pairs)
        ring.active_kid = self.active_kid
        ring._activate(f"gen-{len(self._history)}", new_seed, note="rotation")
        ring.ed_ready = self.ed_ready and self._mod.mechanism().startswith("Ed25519")
        return ring

    def _pair_for(self, domain: str) -> tuple[str, bytes, bytes]:
        """Active key, or domain subkey-derived keypair in ed mode."""
        active = self._pairs[self.active_kid]
        if domain in ("default", ""):
            return self.active_kid, active["seed"], active["public"]
        sub = _hkdf(active["seed"], b"eci-architect|" + domain.encode())
        # subkey acts as an Ed25519 seed; public derived deterministically
        if self.ed_ready:
            from cryptography.hazmat.primitives import serialization as _ser
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey as _Priv

            priv = _Priv.from_private_bytes(sub)
            pub = priv.public_key().public_bytes(_ser.Encoding.Raw, _ser.PublicFormat.Raw)
            return f"{self.active_kid}:{domain}", sub, bytes(pub)
        return f"{self.active_kid}:{domain}", sub, active["public"]

    def sign(self, ident: ArchitectIdentity, canonical: str, domain: str,
             timestamp: float) -> dict[str, Any]:
        base = {"architect": ident.name, "title": ident.title, "wallet": ident.wallet,
                "signature": ident.signature, "timestamp": timestamp, "domain": domain}
        if not self.ed_ready:
            digest = hashlib.sha512(f"{self.legacy_key}|{canonical}|{timestamp}".encode()).hexdigest()
            return {**base, "digest": digest, "alg": LEGACY_ALG, "kid": self.active_kid}
        from eci.protocol0.keys import KeyPair
        from eci.protocol0.keys import sign as _sign

        kid, seed, pub = self._pair_for(domain)
        msg = f"{kid}|{canonical}|{timestamp}".encode()
        sig = _sign(KeyPair(private_bytes=seed, public_bytes=pub), msg)
        return {**base, "signature": sig.hex(), "public_hex": pub.hex(),
                "alg": ED_ALG, "kid": kid}

    def verify(self, canonical: str, envelope: dict[str, Any],
               max_age_s: float | None) -> dict[str, Any]:
        try:
            ts = float(envelope.get("timestamp", 0))
        except Exception:  # noqa: BLE001
            return {"ok": False, "alg": str(envelope.get("alg", "?")),
                    "kid": str(envelope.get("kid", "?")), "reason": "bad timestamp"}
        if max_age_s is not None and abs(time.time() - ts) > max_age_s:
            return {"ok": False, "alg": str(envelope.get("alg", "?")),
                    "kid": str(envelope.get("kid", "?")), "reason": "expired"}
        alg = str(envelope.get("alg", LEGACY_ALG))
        if alg == LEGACY_ALG:
            ok = hmac.compare_digest(
                hashlib.sha512(f"{self.legacy_key}|{canonical}|{ts}".encode()).hexdigest(),
                str(envelope.get("digest", "")))
            return {"ok": ok, "alg": alg, "kid": str(envelope.get("kid", "?")),
                    "reason": "" if ok else "digest mismatch"}
        # ed25519: resolve public key by kid (active or retired, incl. subkeys)
        kid = str(envelope.get("kid", ""))
        base_kid = kid.split(":")[0]
        pub_hex = str(envelope.get("public_hex", ""))
        entry = self._pairs.get(base_kid)
        if entry is None:
            for h in self._history:
                if h["kid"] == base_kid:
                    entry = {"public": bytes.fromhex(h["public_hex"])}
                    break
        if ":" in kid and pub_hex:
            pub = bytes.fromhex(pub_hex)  # domain subkey: trust envelope's pub, verify sig
        elif entry is not None:
            pub = entry["public"] if isinstance(entry.get("public"), bytes) else bytes.fromhex(pub_hex or "")
        else:
            return {"ok": False, "alg": alg, "kid": kid, "reason": "unknown kid"}
        try:
            sig = bytes.fromhex(str(envelope.get("signature", "")))
        except Exception:  # noqa: BLE001
            return {"ok": False, "alg": alg, "kid": kid, "reason": "bad signature encoding"}
        res = self._mod.verify(pub, f"{kid}|{canonical}|{ts}".encode(), sig)
        return {"ok": bool(res.get("ok")), "alg": alg, "kid": kid,
                "reason": "" if res.get("ok") else str(res.get("reason", "invalid"))}

    def subkey(self, domain: str) -> str:
        if not self._pairs:
            # legacy mode: deterministic domain separation without secrets
            return hashlib.sha256(f"{self.legacy_key}|{domain}".encode()).hexdigest()
        seed = self._pairs[self.active_kid]["seed"]
        return _hkdf(seed, b"eci-architect|" + domain.encode()).hex()

    def did_document(self, ident: ArchitectIdentity) -> dict[str, Any]:
        if not self._pairs:
            fp = self.legacy_key[:16]
            return {"id": f"did:eci:legacy:{fp}", "alg": LEGACY_ALG,
                    "controller": ident.name, "warning": "attribution only — not a signature key"}
        pub = self._pairs[self.active_kid]["public"]
        fp = hashlib.sha256(b"eci-did|" + pub).hexdigest()[:16]
        return {"id": f"did:eci:{fp}", "alg": ED_ALG, "controller": ident.name,
                "active": {"kid": self.active_kid, "public_hex": pub.hex()},
                "retired": [{"kid": h["kid"], "public_hex": h["public_hex"],
                             "fingerprint": h["fingerprint"]}
                            for h in self._history if h["kid"] != self.active_kid]}

    def status(self) -> dict[str, Any]:
        return {"alg": ED_ALG if self.ed_ready else LEGACY_ALG,
                "kid": self.active_kid, "rotations": max(0, len(self._history) - 1),
                "mechanism": self._mod.mechanism(),
                "seed_configured": bool(self._pairs)}


#: Process-wide sovereign architect identity.
ARCHITECT = ArchitectIdentity()
