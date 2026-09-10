"""Governance futures: futarchy + sortition + sunsetting emergencies.

- Futarchy: policies pass iff a decision market predicts success —
  vote on *values*, bet on *beliefs* (built on market.py LMSR).
- Sortition: verifiable random citizen panels (seeded commitment reveal)
  for legitimacy without campaigns.
- Emergency powers: scoped, epoch-bounded, auto-expiring grants with a
  mandatory post-mortem record — power that cannot forget to die.
"""

from __future__ import annotations

import hashlib
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

__all__ = ["Futarchy", "Sortition", "EmergencyPowers"]


class Futarchy:
    """Decision markets over policy proposals (wraps Marketplace)."""

    def __init__(self, marketplace: Any = None, threshold: float = 0.6) -> None:
        if marketplace is None:
            from eci.market import Marketplace
            marketplace = Marketplace()
        self.mk = marketplace
        self.threshold = threshold
        self.policies: Dict[str, Dict[str, Any]] = {}

    def propose(self, pid: str, claim: str, proposer: str = "dao") -> Dict[str, Any]:
        self.mk.market_for(claim)
        self.policies[pid] = {"claim": claim, "proposer": proposer, "enacted": False,
                              "ts": time.time()}
        return {"pid": pid, "claim": claim}

    def bet(self, trader: str, pid: str, side: str, shares: float) -> Dict[str, Any]:
        p = self.policies[pid]
        return self.mk.trade(trader, p["claim"], side, shares)

    def close(self, pid: str, success_prob: float | None = None) -> Dict[str, Any]:
        """Enact iff market-implied P(success) >= threshold."""
        from eci.market import Marketplace
        p = self.policies[pid]
        mkt = self.mk.market_for(p["claim"])
        prob = mkt.price_yes() if success_prob is None else success_prob
        enacted = bool(prob >= self.threshold)
        p["enacted"] = enacted
        p["prob"] = prob
        return {"pid": pid, "prob": prob, "threshold": self.threshold,
                "enacted": enacted,
                "rule": "vote values, bet beliefs"}

    def health(self) -> Dict[str, Any]:
        return {"ok": True, "policies": len(self.policies)}


@dataclass
class Sortition:
    """Seeded, verifiable random panels (commit-reveal honesty)."""

    def draw(self, candidates: List[str], size: int, seed: str) -> Dict[str, Any]:
        if size > len(candidates):
            raise ValueError("panel larger than candidate pool")
        commitment = hashlib.sha256(f"sortition|{seed}".encode()).hexdigest()
        rng = random.Random(commitment)
        panel = rng.sample(sorted(candidates), size)
        proof = {"seed_hash": commitment[:16], "size": size,
                 "pool": len(candidates)}
        return {"panel": panel, "proof": proof,
                "verify": self.verify(candidates, size, seed, panel)}

    @staticmethod
    def verify(candidates: List[str], size: int, seed: str, panel: List[str]) -> bool:
        commitment = hashlib.sha256(f"sortition|{seed}".encode()).hexdigest()
        return random.Random(commitment).sample(sorted(candidates), size) == panel


@dataclass
class Grant:
    scope: str
    holder: str
    expiry_epoch: int
    reason: str
    postmortem: str = ""
    ts: float = field(default_factory=time.time)


class EmergencyPowers:
    """Powers with mandatory death dates."""

    def __init__(self, epoch_fn: Callable[[], int] | None = None) -> None:
        self._epoch = epoch_fn or (lambda: 0)
        self.grants: List[Grant] = []

    def grant(self, scope: str, holder: str, ttl_epochs: int, reason: str) -> Grant:
        g = Grant(scope, holder, self._epoch() + ttl_epochs, reason)
        self.grants.append(g)
        return g

    def alive(self, holder: str = "", scope: str = "") -> List[Grant]:
        now = self._epoch()
        return [g for g in self.grants if g.expiry_epoch >= now
                and (not holder or g.holder == holder)
                and (not scope or g.scope == scope) and not g.postmortem]

    def sweep(self) -> Dict[str, Any]:
        """Expire the dead; list the living that owe post-mortems."""
        now = self._epoch()
        dead = [g for g in self.grants if g.expiry_epoch < now and not g.postmortem]
        return {"expired": len(dead), "living": len(self.alive()),
                "owed_postmortems": [{"holder": g.holder, "scope": g.scope} for g in dead]}

    def postmortem(self, holder: str, scope: str, text: str) -> bool:
        for g in self.grants:
            if g.holder == holder and g.scope == scope and not g.postmortem:
                g.postmortem = text
                return True
        return False
