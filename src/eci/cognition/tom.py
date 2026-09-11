"""Theory of mind: recursive peer models + deception tripwires.

Each peer gets a belief {capability, intent (coop/defect prior),
reliability} updated by Brier-scored observations. ``predict()`` answers
"what will they do?"; ``recursive_predict()`` answers "what do they think
*we* will do?" one level deep (level-k, k=1 — the documented bound).
Deception flags fire on challenge-response mismatch AND provenance
divergence (claimed inputs != traced inputs) — evidence, not paranoia.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

__all__ = ["PeerBelief", "TheoryOfMind"]


@dataclass
class PeerBelief:
    peer: str
    capability: float = 0.5   # P(successful cooperation)
    coop: float = 0.5         # P(cooperative intent)
    reliability: float = 0.5  # 1 - recent Brier score
    obs: int = 0
    brier_sum: float = 0.0
    flags: int = 0
    updated: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {"peer": self.peer, "capability": self.capability, "coop": self.coop,
                "reliability": self.reliability, "obs": self.obs, "flags": self.flags}


class TheoryOfMind:
    def __init__(self, lr: float = 0.2, flag_threshold: int = 3) -> None:
        self.peers: dict[str, PeerBelief] = {}
        self.lr = lr
        self.flag_threshold = flag_threshold

    def peer(self, peer_id: str) -> PeerBelief:
        return self.peers.setdefault(peer_id, PeerBelief(peer_id))

    def predict(self, peer_id: str) -> dict[str, Any]:
        b = self.peer(peer_id)
        p_coop_success = b.capability * b.coop
        return {"peer": peer_id, "p_coop_success": p_coop_success,
                "recommend": "cooperate" if p_coop_success > 0.5 else "verify-first",
                "confidence": b.reliability}

    def recursive_predict(self, peer_id: str, our_signal: float = 0.7) -> dict[str, Any]:
        """Level-1: they model us as cooperating with p=our_signal."""
        b = self.peer(peer_id)
        they_think_we_coop = our_signal * b.reliability + 0.5 * (1 - b.reliability)
        their_response = b.coop * they_think_we_coop + (1 - b.coop) * 0.2
        return {"peer": peer_id, "they_think_we_coop": they_think_we_coop,
                "their_p_coop": their_response, "depth": 1}

    def observe(self, peer_id: str, predicted_p: float, cooperated: bool,
                challenge_ok: bool = True, provenance_ok: bool = True) -> PeerBelief:
        b = self.peer(peer_id)
        y = 1.0 if cooperated else 0.0
        b.brier_sum += (predicted_p - y) ** 2
        b.obs += 1
        b.reliability = max(0.0, 1.0 - b.brier_sum / b.obs)
        b.capability += self.lr * ((1.0 if cooperated else 0.0) - b.capability)
        b.coop += self.lr * ((1.0 if cooperated else 0.0) - b.coop)
        if not challenge_ok or not provenance_ok:
            b.flags += 1
        b.updated = time.time()
        return b

    def quarantinable(self, peer_id: str) -> bool:
        return self.peer(peer_id).flags >= self.flag_threshold
