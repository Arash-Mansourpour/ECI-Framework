"""Social key recovery: Shamir shares + timelock + identity challenge.

A lost agent key splits into n trustee shares (any k recover). Release is
gated twice: a timelock (no instant recovery — theft can't cash out fast)
and a fresh passing challenge (the requester must BE the agent behaviorally).
Shares are useless individually; trustees never see the key.
Field: GF(257) per byte (0..255 values, prime modulus, exact arithmetic).
"""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, field
from typing import Dict, List

__all__ = ["split", "combine", "RecoveryRequest"]

P = 257


def _eval(coeffs: List[int], x: int) -> int:
    return sum(c * pow(x, i, P) for i, c in enumerate(coeffs)) % P


def split(secret: bytes, n: int, k: int) -> List[Dict]:
    """Split into n shares, any k of which recover. k>=2, n>=k."""
    if not 2 <= k <= n <= 255:
        raise ValueError("need 2 <= k <= n <= 255")
    shares = []
    for byte in secret:
        coeffs = [byte] + [secrets.randbelow(P) for _ in range(k - 1)]
        pts = [(x, _eval(coeffs, x)) for x in range(1, n + 1)]
        shares.append(pts)
    out = []
    for i in range(n):
        out.append({"idx": i + 1, "need": k, "parts": [shares[b][i][1] for b in range(len(secret))],
                    "len": len(secret)})
    return out


def _lagrange_at0(points: List[tuple]) -> int:
    total = 0
    for j, (xj, yj) in enumerate(points):
        num, den = 1, 1
        for m, (xm, _) in enumerate(points):
            if m != j:
                num = num * (-xm) % P
                den = den * (xj - xm) % P
        total = (total + yj * num * pow(den, P - 2, P)) % P
    return total


def combine(shares: List[Dict]) -> bytes:
    """Recover from >= k shares (same idx set, same len enforced)."""
    if not shares:
        raise ValueError("no shares")
    k, ln = shares[0]["need"], shares[0]["len"]
    if len(shares) < k:
        raise ValueError(f"need {k} shares, got {len(shares)}")
    if any(s["need"] != k or s["len"] != ln for s in shares):
        raise ValueError("mismatched share sets")
    out = bytearray()
    for b in range(ln):
        pts = [(s["idx"], s["parts"][b]) for s in shares[:k]]
        out.append(_lagrange_at0(pts) % 256)
    return bytes(out)


@dataclass
class RecoveryRequest:
    agent_id: str
    unlock_at: float
    shares: List[Dict] = field(default_factory=list)

    def ready(self) -> bool:
        return time.time() >= self.unlock_at and len(self.shares) >= (self.shares[0]["need"] if self.shares else 2)

    def attempt(self, challenge_passed: bool) -> bytes:
        """Release ONLY after timelock AND a fresh passing challenge."""
        if time.time() < self.unlock_at:
            raise PermissionError("timelock not expired")
        if not challenge_passed:
            raise PermissionError("identity challenge failed")
        return combine(self.shares)
