"""Data-DAO + multi-level governance (Vana-inspired, consciousness-weighted).

Layers
------
* Local: agent self-governance, P2P negotiation.
* Regional: WBFT-elected coordinators, domain clusters.
* Global: federated DAO, quadratic + consciousness-weighted voting.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List

from eci.core.identity import ARCHITECT

__all__ = ["ECIDataDAO", "quadratic_vote_cost", "consciousness_weight"]


def quadratic_vote_cost(votes: int) -> int:
    """Quadratic voting cost: C = v² (Lalley & Weyl)."""
    return votes * votes


def consciousness_weight(phi: float) -> float:
    """Voting weight w(Φ) = log2(1+Φ) — expertise without plutocracy."""
    import math as _m

    return _m.log2(1.0 + max(0.0, phi))


@dataclass
class ECIDataDAO:
    dao_id: str
    members: Dict[str, Dict[str, float]] = field(default_factory=dict)
    proposals: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    treasury: float = 0.0

    def register(self, agent_id: str, data_contrib: float, phi: float, stake: float = 1.0) -> None:
        tokens = data_contrib * (1.0 + consciousness_weight(phi))
        self.members[agent_id] = {"tokens": tokens, "phi": phi, "stake": stake}

    def propose(self, title: str, payload: Any, proposer: str) -> str:
        pid = hashlib.sha256(f"{self.dao_id}|{title}|{time.time()}".encode()).hexdigest()[:16]
        self.proposals[pid] = {
            "title": title,
            "payload": payload,
            "proposer": proposer,
            "votes_for": 0.0,
            "votes_against": 0.0,
            "open": True,
            "stamp": ARCHITECT.stamp({"kind": "dao_proposal", "dao": self.dao_id, "title": title}),
        }
        return pid

    def vote(self, proposal_id: str, voter: str, votes: int, approve: bool) -> float:
        """Quadratic, consciousness-weighted vote; returns effective weight."""
        if proposal_id not in self.proposals or not self.proposals[proposal_id]["open"]:
            raise ValueError("proposal not open")
        m = self.members.get(voter)
        if m is None:
            raise ValueError("unknown voter")
        cost = quadratic_vote_cost(votes)
        if cost > m["tokens"]:
            raise ValueError("insufficient governance tokens")
        m["tokens"] -= cost
        w = votes * (1.0 + consciousness_weight(m["phi"]))
        key = "votes_for" if approve else "votes_against"
        self.proposals[proposal_id][key] += w
        return w

    def tally(self, proposal_id: str) -> Dict[str, Any]:
        p = self.proposals[proposal_id]
        p["open"] = False
        passed = p["votes_for"] > p["votes_against"]
        return {"passed": passed, "for": p["votes_for"], "against": p["votes_against"]}
