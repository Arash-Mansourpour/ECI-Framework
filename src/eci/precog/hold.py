"""Provisional hold: reversible pre-breach restraint (never punishment).

hold tier (p>=0.9) restrains an agent BEFORE any violation: sensitive
actions deny with reason 'provisional-hold', while read_state + challenges
stay open so the agent can always clear itself with a fresh pass. Holds
expire (TTL) and every hold/release is a ledger record. Contrast with
quarantine (post-breach, appeal-gated): hold is lighter, faster, reversible.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

__all__ = ["ProvisionalHold"]


@dataclass
class ProvisionalHold:
    ttl_s: float = 600.0
    held: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def place(self, agent_id: str, p: float, ledger=None) -> Dict[str, Any]:
        self.held[agent_id] = {"p": p, "until": time.time() + self.ttl_s}
        if ledger:
            ledger.append("precog_hold", {"node": agent_id, "p": round(p, 3)})
        return {"held": True, "until": self.held[agent_id]["until"]}

    def is_held(self, agent_id: str) -> bool:
        rec = self.held.get(agent_id)
        if not rec:
            return False
        if time.time() > rec["until"]:
            del self.held[agent_id]
            return False
        return True

    def check(self, agent_id: str, action: str) -> Optional[str]:
        """Return deny-reason, or None if allowed. Challenges always pass."""
        if not self.is_held(agent_id):
            return None
        if action in ("read_state", "challenge_respond", "appeal"):
            return None
        return "provisional-hold: clear with a fresh passing challenge"

    def release(self, agent_id: str, challenge_passed: bool, ledger=None) -> bool:
        if agent_id not in self.held:
            return True
        if challenge_passed:
            del self.held[agent_id]
            if ledger:
                ledger.append("precog_release", {"node": agent_id})
            return True
        return False
