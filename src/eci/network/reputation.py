"""Multi-signal reputation with designed forgetting.

weight = stake x trust x obedience x freshness, each in [0,1] except
stake. freshness = decay^epochs_since_active (default half-life 50
epochs). Old sins are forgiven exponentially; fresh betrayal dominates.
Aggregation weight for consensus/DAO = normalized reputation x stake.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

__all__ = ["Reputation", "ReputationBoard"]


@dataclass
class Reputation:
    stake: float = 1.0
    trust: float = 1.0
    obedience: float = 0.0
    epochs_since_active: int = 0
    half_life: int = 50

    def freshness(self) -> float:
        return 0.5 ** (max(0, self.epochs_since_active) / max(1, self.half_life))

    def weight(self) -> float:
        t = min(max(self.trust, 0.0), 1.0)
        o = min(max(self.obedience, 0.0), 1.0)
        return max(0.0, self.stake) * t * (0.3 + 0.7 * o) * self.freshness()


@dataclass
class ReputationBoard:
    members: Dict[str, Reputation] = field(default_factory=dict)

    def observe(self, agent_id: str, trust: float | None = None, obedience: float | None = None, active: bool = True) -> None:
        r = self.members.setdefault(agent_id, Reputation())
        if trust is not None:
            r.trust = min(max(trust, 0.0), 1.0)
        if obedience is not None:
            r.obedience = min(max(obedience, 0.0), 1.0)
        r.epochs_since_active = 0 if active else r.epochs_since_active + 1

    def tick(self) -> None:
        for r in self.members.values():
            r.epochs_since_active += 1

    def weights(self) -> Dict[str, float]:
        return {nid: r.weight() for nid, r in self.members.items()}
