"""Staged rollout: 10% canary -> divergence watch -> proceed / auto-rollback.

A version rolls out in batches; after each batch the collective gate is
checked (coherence/divergence from live awareness). Degraded/closed gate
halts the rollout and marks already-upgraded nodes for rollback. Every
step is a ledger record. Rollouts stop being scary and start being routine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List

__all__ = ["RolloutPlan", "staged_rollout"]


@dataclass
class RolloutPlan:
    version: str
    batches: List[List[str]] = field(default_factory=list)

    @classmethod
    def plan(cls, node_ids: List[str], first_batch: float = 0.1) -> "RolloutPlan":
        import math as _m

        n0 = max(1, _m.ceil(len(node_ids) * first_batch))
        batches = [node_ids[:n0]]
        rest = node_ids[n0:]
        step = max(1, _m.ceil(len(node_ids) / 4))
        batches += [rest[i:i + step] for i in range(0, len(rest), step)]
        return cls(version="", batches=batches)


def staged_rollout(
    plan: RolloutPlan,
    gate_fn: Callable[[List[str]], Dict[str, Any]],
    apply_fn: Callable[[str], bool],
    rollback_fn: Callable[[str], bool],
    ledger=None,
) -> Dict[str, Any]:
    """Execute batches; halt + rollback on degraded gate. Returns report."""
    upgraded: List[str] = []
    for i, batch in enumerate(plan.batches):
        for nid in batch:
            if apply_fn(nid):
                upgraded.append(nid)
        g = gate_fn(upgraded)
        if ledger:
            ledger.append("rollout_batch", {"batch": i, "nodes": batch, "gate": g.get("gate"), "version": plan.version})
        if g.get("gate") in ("degraded", "closed"):
            rolled = [nid for nid in upgraded if rollback_fn(nid)]
            if ledger:
                ledger.append("rollout_rollback", {"rolled_back": rolled, "gate": g.get("gate")})
            return {"done": False, "halted_at_batch": i, "upgraded": [], "rolled_back": rolled, "gate": g.get("gate")}
    if ledger:
        ledger.append("rollout_done", {"version": plan.version, "nodes": upgraded})
    return {"done": True, "upgraded": upgraded, "rolled_back": [], "gate": "open"}
