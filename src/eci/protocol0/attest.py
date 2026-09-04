"""Attestations: signed, fresh, replay-safe capability claims.

An agent attests: {agent_id, spec_version, awareness, obedience, trust,
timestamp, nonce} + architect stamp + HMAC signature under a per-agent
key derived via HKDF. Verification checks: schema, spec pin, freshness,
replay window, signature.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, Optional

from eci.core.identity import ARCHITECT
from eci.security.pqc import derive_key

__all__ = ["Attestation", "ReplayWindow", "issue_attestation", "verify_attestation"]


@dataclass
class Attestation:
    agent_id: str
    spec_version: str
    awareness: float
    obedience: float
    trust: float
    timestamp: float
    nonce: str
    signature: str = ""
    architect_stamp: Optional[Dict] = None

    def payload(self) -> str:
        return "|".join([
            self.agent_id, self.spec_version,
            f"{self.awareness:.6f}", f"{self.obedience:.6f}", f"{self.trust:.6f}",
            f"{self.timestamp:.3f}", self.nonce,
        ])

    def to_dict(self) -> Dict:
        return {
            "agent_id": self.agent_id, "spec_version": self.spec_version,
            "awareness": self.awareness, "obedience": self.obedience,
            "trust": self.trust, "timestamp": self.timestamp,
            "nonce": self.nonce, "signature": self.signature,
            "architect_stamp": self.architect_stamp,
        }


def _agent_key(agent_id: str) -> bytes:
    return derive_key(b"protocol0|" + agent_id.encode(), info=b"protocol0-attest", length=32)


def architect_anchor_available() -> Dict:
    """Report whether a NIST-standard anchor (ML-DSA via liboqs) exists.

    Per-message attestations stay HMAC (auditable, no new deps); the
    architect identity anchor upgrades to ML-DSA-65 automatically when
    liboqs-python is installed. Returns {available, mechanism}.
    """
    try:
        from eci.security.pqc import PQCSuite as _P

        caps = _P().capabilities() if hasattr(_P(), "capabilities") else {}
        if caps.get("ml_dsa"):
            return {"available": True, "mechanism": "ML-DSA-65/oqs"}
    except Exception:
        pass
    return {"available": False, "mechanism": "HMAC-SHA256+SHA512-stamp(research)"}


def issue_attestation(agent_id: str, spec_version: str, awareness: float, obedience: float, trust: float) -> Attestation:
    a = Attestation(
        agent_id=agent_id, spec_version=spec_version,
        awareness=float(max(0.0, min(1.0, awareness))),
        obedience=float(max(0.0, min(1.0, obedience))),
        trust=float(max(0.0, min(1.0, trust))),
        timestamp=time.time(), nonce=secrets.token_hex(12),
    )
    sig = hmac.new(_agent_key(agent_id), a.payload().encode(), hashlib.sha256).hexdigest()
    a.signature = sig
    a.architect_stamp = ARCHITECT.stamp({"kind": "protocol0_attest", "agent": agent_id, "nonce": a.nonce})
    return a


class ReplayWindow:
    """Per-agent nonce memory (bounded deque)."""

    def __init__(self, capacity: int = 1024) -> None:
        self.seen: Deque[str] = deque(maxlen=capacity)

    def check_and_add(self, nonce: str) -> bool:
        if nonce in self.seen:
            return False
        self.seen.append(nonce)
        return True


def verify_attestation(att: Attestation, spec_version: str, max_age_s: float, replay: Optional[ReplayWindow] = None, agent_key: Optional[bytes] = None) -> Dict:
    """Verify schema + spec pin + freshness + replay + HMAC. Returns {ok, reason}."""
    if att.spec_version != spec_version:
        return {"ok": False, "reason": f"spec pin mismatch {att.spec_version} != {spec_version}"}
    if not att.agent_id or not att.nonce or not att.signature:
        return {"ok": False, "reason": "missing fields"}
    if abs(time.time() - att.timestamp) > max_age_s:
        return {"ok": False, "reason": "stale attestation"}
    if replay is not None and not replay.check_and_add(att.agent_id + ":" + att.nonce):
        return {"ok": False, "reason": "replay detected"}
    key = agent_key if agent_key is not None else _agent_key(att.agent_id)
    expect = hmac.new(key, att.payload().encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expect, att.signature):
        return {"ok": False, "reason": "bad signature"}
    return {"ok": True, "reason": ""}
