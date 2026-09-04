"""Privacy guardian: collective statistics without individual exposure.

Each agent owns a disclosure budget (epsilon). Aggregate queries (e.g.
mean awareness) are answered with Laplace noise scaled to sensitivity /
epsilon_share, and the spent budget is debited. Exhausted budget denies
further queries about that agent until epoch reset. Honest, textbook
differential privacy (Dwork 2006): noise = Lap(sensitivity / eps).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Callable, Dict, List

__all__ = ["Guardian"]


@dataclass
class Guardian:
    budget_per_epoch: float = 1.0
    spent: Dict[str, float] = field(default_factory=dict)

    def remaining(self, agent_id: str) -> float:
        return max(0.0, self.budget_per_epoch - self.spent.get(agent_id, 0.0))

    def ask(self, agent_id: str, value: float, sensitivity: float, eps: float, seed: int = 0) -> Dict:
        """Noisy release of one agent's value. Denies when budget is exhausted."""
        if eps <= 0 or eps > self.remaining(agent_id):
            return {"ok": False, "reason": "disclosure budget exhausted"}
        rng = random.Random(f"{agent_id}|{seed}")
        u = rng.random() - 0.5
        noise = -math.copysign(1.0, u) * (sensitivity / eps) * math.log(1 - 2 * abs(u))
        self.spent[agent_id] = self.spent.get(agent_id, 0.0) + eps
        return {"ok": True, "noisy": value + noise, "spent": eps, "remaining": self.remaining(agent_id)}

    def mean(self, values: Dict[str, float], eps_each: float = 0.1, seed: int = 0) -> Dict:
        """Private mean over agents (each charged independently; skips the broke)."""
        outs = {}
        for nid, v in values.items():
            r = self.ask(nid, v, sensitivity=1.0 / max(1, len(values)), eps=eps_each, seed=seed)
            if r["ok"]:
                outs[nid] = r["noisy"]
        if not outs:
            return {"ok": False, "reason": "no budget anywhere"}
        return {"ok": True, "mean": sum(outs.values()) / len(outs), "n": len(outs)}

    def reset_epoch(self) -> None:
        self.spent.clear()
