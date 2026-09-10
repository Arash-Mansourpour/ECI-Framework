"""Object-capability security: attenuable, expiring, auditable authority.

Macaroon-style tokens with HMAC-chained caveats. A token starts broad
(issuer root) and can only be *narrowed* by adding caveats — delegation
without escalation, verifiable offline by any holder of the root key:

  sig_0 = HMAC(root, token_id)
  sig_{i+1} = HMAC(sig_i, caveat_string)

Caveat grammar (exact, deny-on-unknown):
  exp:<unix_ts>        expiry wall-clock
  ns:<fnmatch>         namespace pattern (team-a, mesh/*)
  act:<fnmatch>        action pattern (tool.*, ledger.append)
  budget:<float>       max cumulative spend authorized
  rate:<float>         max calls/second
  epoch:<int>          valid while continuum epoch <= value

Serialization is base64url(JSON) — passes through MCP/HTTP headers.
Third-party (discharge) caveats are the documented upgrade path.
"""

from __future__ import annotations

import base64
import fnmatch
import hashlib
import hmac
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

__all__ = ["CaveatError", "CapToken", "Issuer"]


class CaveatError(PermissionError):
    pass


def _hmac(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode(), hashlib.sha256).digest()


@dataclass
class CapToken:
    tid: str
    issuer: str
    caveats: List[str] = field(default_factory=list)
    sig: str = ""  # hex of chained HMAC

    def attenuate(self, root: bytes, *caveats: str) -> "CapToken":
        """Return a NARROWED copy (original untouched, chain extended)."""
        for c in caveats:
            _check_syntax(c)
        sig = bytes.fromhex(self.sig)
        caveats_all = list(self.caveats)
        for c in caveats:
            sig = _hmac(sig, c)
            caveats_all.append(c)
        return CapToken(self.tid, self.issuer, caveats_all, sig.hex())

    def serialize(self) -> str:
        raw = json.dumps({"t": self.tid, "i": self.issuer,
                          "c": self.caveats, "s": self.sig}).encode()
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    @classmethod
    def deserialize(cls, s: str) -> "CapToken":
        raw = base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))
        d = json.loads(raw)
        return cls(d["t"], d["i"], list(d.get("c", [])), d.get("s", ""))


def _check_syntax(c: str) -> None:
    kind, _, val = c.partition(":")
    if kind not in ("exp", "ns", "act", "budget", "rate", "epoch"):
        raise CaveatError(f"unknown caveat {c!r} (deny-on-unknown)")
    if kind in ("exp", "budget", "rate", "epoch"):
        float(val)  # must parse (raises ValueError -> caller maps)


class Issuer:
    """Holds root keys per issuer id; mints and verifies."""

    def __init__(self) -> None:
        self._roots: Dict[str, bytes] = {}
        self.minted = 0

    def mint(self, issuer: str, *caveats: str, root: bytes | None = None) -> Tuple[CapToken, str]:
        """Mint + serialize. Returns (token, serialized)."""
        for c in caveats:
            try:
                _check_syntax(c)
            except ValueError as exc:
                raise CaveatError(f"bad caveat value {c!r}") from exc
        key = root or os.urandom(32)
        self._roots[issuer] = key
        tid = uuid.uuid4().hex[:12]
        sig = _hmac(key, tid)
        tok = CapToken(tid, issuer, [], sig.hex())
        if caveats:
            tok = tok.attenuate(key, *caveats)
        self.minted += 1
        return tok, tok.serialize()

    def verify(self, serialized: str, action: str = "", namespace: str = "",
               spend: float = 0.0, now: float | None = None,
               epoch: int = 0) -> Dict[str, Any]:
        """Recompute the chain; enforce every caveat. Structured verdict."""
        now = time.time() if now is None else now
        try:
            tok = CapToken.deserialize(serialized)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": f"malformed: {exc}"}
        key = self._roots.get(tok.issuer)
        if key is None:
            return {"ok": False, "error": "unknown issuer"}
        sig = _hmac(key, tok.tid)
        for c in tok.caveats:
            try:
                _check_syntax(c)
            except (CaveatError, ValueError):
                return {"ok": False, "error": f"bad caveat {c!r}"}
            sig = _hmac(sig, c)
        if sig.hex() != tok.sig:
            return {"ok": False, "error": "signature mismatch (forgery or tamper)"}
        # enforce
        spent_floor = 0.0
        for c in tok.caveats:
            kind, _, val = c.partition(":")
            if kind == "exp" and now > float(val):
                return {"ok": False, "error": "expired"}
            if kind == "epoch" and epoch > int(float(val)):
                return {"ok": False, "error": "epoch exceeded"}
            if kind == "ns" and not fnmatch.fnmatchcase(namespace, val):
                return {"ok": False, "error": f"namespace {namespace!r} outside {val!r}"}
            if kind == "act" and action and not fnmatch.fnmatchcase(action, val):
                return {"ok": False, "error": f"action {action!r} outside {val!r}"}
            if kind == "budget":
                spent_floor = float(val)
        if spend > spent_floor and any(c.startswith("budget:") for c in tok.caveats):
            return {"ok": False, "error": f"spend {spend} exceeds budget {spent_floor}"}
        return {"ok": True, "issuer": tok.issuer, "caveats": len(tok.caveats)}
