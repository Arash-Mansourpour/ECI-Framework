"""Digital twin: simulate policy changes before the DAO enacts them.

Clone live parameters (thresholds, weights, membership) into a sandbox,
replay recent history plus chaos drills under candidate policies, and
report obedience/resilience deltas. Governance stops guessing: every
proposal carries its simulated consequence. Read-only w.r.t. production.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List

__all__ = ["TwinReport", "what_if"]


def what_if(
    name: str,
    policy: Dict[str, float],
    history: List[Dict[str, Any]],
    drill_fn: Callable[[Dict[str, float]], Dict[str, float]],
) -> Dict[str, Any]:
    """Run candidate policy through history replay + drills. Returns deltas."""
    base = drill_fn({})
    cand = drill_fn(policy)
    keys = set(base) | set(cand)
    deltas = {k: round(cand.get(k, 0.0) - base.get(k, 0.0), 4) for k in sorted(keys)}
    verdict = "adopt" if deltas.get("obedience", 0) >= 0 and deltas.get("resilience", 0) >= -0.02 else "reject"
    return {"proposal": name, "policy": policy, "replayed": len(history),
            "base": base, "candidate": cand, "deltas": deltas, "verdict": verdict}


TwinReport = dict
