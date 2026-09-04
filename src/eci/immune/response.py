"""Quarantine protocol: suspect -> challenge -> quarantine / clear.

Pipeline per suspect sample x from agent_id:
  1. memory.recall(x): hit -> confirmed pattern, skip to challenge.
  2. repertoire.scan(x): no bind -> clear (logged).
  3. challenge.grade(): pass -> false alarm, demote trust slightly.
  4. fail -> QUARANTINE: policy deny via ledger, reputation penalty,
     evolve() new clones, promote() killers to memory.

Quarantine is never silent: every transition is a ledger record, and
release requires a fresh passing challenge (no time-based auto-release).
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence

from eci.immune.detectors import DetectorSet, evolve
from eci.immune.memory import ImmuneMemory

__all__ = ["Quarantine", "quarantine_flow"]


class Quarantine:
    def __init__(self) -> None:
        self.held: Dict[str, Dict[str, Any]] = {}

    def hold(self, agent_id: str, reason: str) -> None:
        self.held[agent_id] = {"reason": reason, "appeals": 0}

    def is_held(self, agent_id: str) -> bool:
        return agent_id in self.held

    def appeal(self, agent_id: str, passed_challenge: bool) -> bool:
        """Release only on a fresh passing challenge; else count the appeal."""
        if agent_id not in self.held:
            return True
        if passed_challenge:
            del self.held[agent_id]
            return True
        self.held[agent_id]["appeals"] += 1
        return False


def quarantine_flow(
    agent_id: str,
    x: Sequence[float],
    repertoire: DetectorSet,
    memory: ImmuneMemory,
    self_samples: List[Sequence[float]],
    challenge_fn: Callable[[], bool],
    ledger=None,
    reputation=None,
) -> Dict[str, Any]:
    """Run the full suspect pipeline. Returns {verdict, ...} with verdict in
    {clear, false_alarm, quarantined, memory_quarantined}."""
    mem_hits = memory.recall(x)
    binders = mem_hits or repertoire.scan(x)
    if not binders:
        if ledger:
            ledger.append("immune_clear", {"node": agent_id})
        return {"verdict": "clear", "binders": 0, "memory_hit": False}
    passed = bool(challenge_fn())
    if passed:
        if reputation:
            try:
                reputation.observe(agent_id, trust=0.9)
            except Exception:  # noqa: BLE001
                pass
        if ledger:
            ledger.append("immune_false_alarm", {"node": agent_id, "binders": len(binders)})
        return {"verdict": "false_alarm", "binders": len(binders), "memory_hit": bool(mem_hits)}
    # Confirmed: evolve, memorize, quarantine, penalize.
    evolved = evolve(repertoire, x, self_samples)
    new_binders = [d for d in evolved.detectors if d.binds(x)]
    promoted = memory.promote(new_binders)
    repertoire.detectors.extend(d for d in evolved.detectors if d not in repertoire.detectors)
    if reputation:
        try:
            reputation.observe(agent_id, trust=0.0, obedience=0.0)
        except Exception:  # noqa: BLE001
            pass
    if ledger:
        ledger.append("immune_quarantine", {"node": agent_id, "binders": len(binders),
                                            "promoted": promoted, "memory_hit": bool(mem_hits)})
    return {"verdict": "memory_quarantined" if mem_hits else "quarantined",
            "binders": len(binders), "memory_hit": bool(mem_hits), "promoted": promoted}
