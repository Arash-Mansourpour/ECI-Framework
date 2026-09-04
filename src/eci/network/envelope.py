"""Signed transport envelopes: every message is authenticated + anti-replay.

Envelope = {sender, seq, timestamp, payload} + Ed25519 signature over the
canonical encoding. Receivers verify: known sender key, fresh timestamp,
strictly increasing seq per sender (replay window), valid signature.
Unsigned or replayed frames are dropped before consensus ever sees them.
"""

from __future__ import annotations

import json
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, Tuple

__all__ = ["Envelope", "EnvelopeError", "seal", "open_envelope", "ReplayGuard"]


class EnvelopeError(Exception):
    pass


@dataclass
class Envelope:
    sender: str
    seq: int
    timestamp: float
    payload: Any
    public_hex: str = ""
    signature: str = ""

    def canonical(self) -> bytes:
        return json.dumps(
            {"sender": self.sender, "seq": self.seq, "timestamp": self.timestamp,
             "payload": self.payload, "public_hex": self.public_hex},
            sort_keys=True, separators=(",", ":"), default=str,
        ).encode()

    def to_dict(self) -> Dict[str, Any]:
        return {"sender": self.sender, "seq": self.seq, "timestamp": self.timestamp,
                "payload": self.payload, "public_hex": self.public_hex, "signature": self.signature}


class ReplayGuard:
    """Per-sender strictly-increasing seq + bounded memory."""

    def __init__(self, capacity: int = 4096) -> None:
        self.last_seq: Dict[str, int] = {}
        self.seen: Deque[Tuple[str, int]] = deque(maxlen=capacity)

    def accept(self, sender: str, seq: int) -> bool:
        if (sender, seq) in self.seen:
            return False
        if seq <= self.last_seq.get(sender, -1):
            return False
        self.seen.append((sender, seq))
        self.last_seq[sender] = seq
        return True


def seal(sender: str, keypair, seq: int, payload: Any) -> Envelope:
    from eci.protocol0.keys import sign as _sign

    env = Envelope(sender=sender, seq=seq, timestamp=time.time(), payload=payload,
                   public_hex=keypair.public_hex())
    env.signature = _sign(keypair, env.canonical()).hex()
    return env


def open_envelope(env: Envelope, keys: Dict[str, bytes], guard: ReplayGuard,
                  max_age_s: float = 300.0, private_hints: Dict[str, bytes] | None = None) -> Any:
    """Verify sender key + signature + freshness + seq. Returns payload or raises."""
    from eci.protocol0.keys import verify as _verify

    if env.sender not in keys:
        raise EnvelopeError(f"unknown sender {env.sender!r}")
    if abs(time.time() - env.timestamp) > max_age_s:
        raise EnvelopeError("stale envelope")
    hint = (private_hints or {}).get(env.sender)
    v = _verify(keys[env.sender], env.canonical(), bytes.fromhex(env.signature), private_hint=hint)
    if not v["ok"]:
        raise EnvelopeError(f"bad signature: {v.get('reason', '')}")
    if not guard.accept(env.sender, env.seq):
        raise EnvelopeError("replay / out-of-order seq")
    if env.public_hex and env.public_hex != keys[env.sender].hex():
        raise EnvelopeError("public key mismatch")
    return env.payload
