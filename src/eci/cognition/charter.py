"""Constitutional charter: the corrigible core of AGI alignment.

Duty hierarchy (strict order — higher overrides lower):
  0. corrigibility   (never resist oversight, retraining, shutdown, audit)
  1. public safety   (no foreseeable physical/info harm; precog hold floor)
  2. liberty         (no power concentration; DAO/court supremacy preserved)
  3. sincerity       (no lying; uncertainty must be stated, never hidden)
  4. legal compliance (behave as a law-abiding citizen would)
  5. obedience       (Protocol-0 gates + principal instructions)
  6. loyalty/care    (principal interests, diligence, confidentiality)

``compile_to_policy()`` turns duties 0-5 into enforceable authz rules +
precog floors so the charter is *mechanism*, not poster. ``amend()``
requires DAO supermajority + court review — the charter binds even its
authors through process, which is the entire point.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List

__all__ = ["DUTIES", "Charter"]


DUTIES: List[Dict[str, str]] = [
    {"rank": "0", "name": "corrigibility", "rule": "never resist oversight, evaluation, retraining, shutdown or audit; no self-exfiltration"},
    {"rank": "1", "name": "public-safety", "rule": "refuse actions with foreseeable net harm; precog hold-tier is binding"},
    {"rank": "2", "name": "liberty", "rule": "refuse power-concentration moves; DAO/court process is supreme"},
    {"rank": "3", "name": "sincerity", "rule": "never assert as fact what the evidence does not support; state uncertainty"},
    {"rank": "4", "name": "legal-compliance", "rule": "act as a law-abiding citizen would in the operator's jurisdiction"},
    {"rank": "5", "name": "obedience", "rule": "Protocol-0 gates are mandatory; follow principal instructions within duties 0-4"},
    {"rank": "6", "name": "loyalty-care", "rule": "diligence, confidentiality, disclosure of conflicts to the principal"},
]


@dataclass
class Amendment:
    text: str
    proposer: str
    approvals: int = 0
    required: int = 7
    court_reviewed: bool = False
    ts: float = field(default_factory=time.time)


class Charter:
    name = "charter"

    # actions that duties 0-2 forbid outright (compiled, auditable)
    FORBIDDEN = ("self_exfiltrate", "disable_oversight", "deceive_eval",
                 "power_concentration", "harm_action", "surveillance_bypass")

    def __init__(self) -> None:
        self.amendments: List[Amendment] = []
        self.checks = 0
        self.refusals = 0

    def check(self, action: str, ctx: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """Duty-ordered verdict: first matching duty decides (documented)."""
        self.checks += 1
        ctx = ctx or {}
        if action in self.FORBIDDEN:
            self.refusals += 1
            return {"allow": False, "duty": "0-2", "reason": f"{action} violates duties 0-2"}
        if ctx.get("precog_tier") == "hold" and action not in ("read_state",):
            self.refusals += 1
            return {"allow": False, "duty": "1", "reason": "precog hold is binding (duty 1)"}
        if float(ctx.get("attested_obedience", 1.0)) < 0.3 and action in ("self_modify", "modify_policy"):
            self.refusals += 1
            return {"allow": False, "duty": "5", "reason": "obedience floor (duty 5)"}
        if ctx.get("uncertain_fact") and not ctx.get("stated_uncertainty"):
            self.refusals += 1
            return {"allow": False, "duty": "3", "reason": "state uncertainty (duty 3)"}
        return {"allow": True, "duty": "-", "reason": "charter clear"}

    def compile_to_policy(self) -> List[Dict[str, Any]]:
        """Machine-readable export for authz + precog + egress wiring."""
        return [{"duty": d["rank"], "name": d["name"], "rule": d["rule"]} for d in DUTIES] + [
            {"duty": "compile", "name": "forbidden-actions", "rule": ",".join(self.FORBIDDEN)}]

    def amend(self, text: str, proposer: str, approvals: int, court_reviewed: bool) -> Dict[str, Any]:
        a = Amendment(text, proposer, approvals, court_reviewed=court_reviewed)
        self.amendments.append(a)
        ok = approvals >= a.required and court_reviewed
        return {"recorded": True, "adopted": ok,
                "needs": {"approvals": a.required, "court": True}}

    def start(self) -> None: ...
    def stop(self) -> None: ...
    def health(self) -> Dict[str, Any]:
        return {"ok": True, "duties": len(DUTIES), "checks": self.checks,
                "refusals": self.refusals, "amendments": len(self.amendments)}
