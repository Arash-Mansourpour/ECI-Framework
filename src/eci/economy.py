"""Internal economy: metered actions, staking, slash, relay rewards.

Not a currency: non-transferable usage credits that make spam expensive
and useful work (relaying, storing, witnessing) rewarding. Quarantine
slashes stake; honest epochs accrue. Settlement is a signed report, not
a token transfer — no chain, no exchange, no speculation surface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

__all__ = ["Economy", "ACTION_COSTS"]

ACTION_COSTS = {
    "read_state": 1.0, "propose_task": 2.0, "vote": 3.0,
    "execute_tool": 5.0, "relay": -2.0, "store": -1.0, "witness": -1.0,
    "modify_policy": 20.0, "self_modify": 50.0,
}
SLASH_QUARANTINE = 25.0
EPOCH_REWARD = 5.0


@dataclass
class Economy:
    balances: Dict[str, float] = field(default_factory=dict)
    stakes: Dict[str, float] = field(default_factory=dict)
    log: List[Dict] = field(default_factory=list)

    def fund(self, agent_id: str, credits: float, stake: float = 0.0) -> None:
        self.balances[agent_id] = self.balances.get(agent_id, 0.0) + credits
        self.stakes[agent_id] = self.stakes.get(agent_id, 0.0) + stake

    def charge(self, agent_id: str, action: str, ledger=None) -> Dict:
        cost = ACTION_COSTS.get(action, 5.0)
        bal = self.balances.get(agent_id, 0.0)
        if cost > 0 and bal < cost:
            if ledger:
                ledger.append("economy_deny", {"node": agent_id, "action": action, "cost": cost})
            return {"ok": False, "reason": f"insufficient credits ({bal:.1f} < {cost})"}
        self.balances[agent_id] = bal - cost  # negative cost = reward
        if ledger:
            ledger.append("economy", {"node": agent_id, "action": action, "delta": -cost})
        return {"ok": True, "balance": self.balances[agent_id]}

    def slash(self, agent_id: str, ledger=None) -> Dict:
        stake = self.stakes.get(agent_id, 0.0)
        cut = min(stake, SLASH_QUARANTINE)
        self.stakes[agent_id] = stake - cut
        if ledger:
            ledger.append("economy_slash", {"node": agent_id, "slashed": cut})
        return {"slashed": cut, "stake_left": self.stakes[agent_id]}

    def epoch(self, active: List[str], ledger=None) -> Dict:
        for nid in active:
            self.balances[nid] = self.balances.get(nid, 0.0) + EPOCH_REWARD
        if ledger:
            ledger.append("economy_epoch", {"rewarded": len(active), "each": EPOCH_REWARD})
        return {"rewarded": len(active)}

    def settlement(self) -> Dict:
        return {"balances": dict(self.balances), "stakes": dict(self.stakes),
                "total_credits": sum(self.balances.values()), "total_stake": sum(self.stakes.values())}
