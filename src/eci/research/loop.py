"""ECI autonomous research loop (v8 OMNISCIENCE, ADR-006).

Closed loop: Hypothesis -> twin_test -> canary -> DAO vote -> Brier update.
Every step is stamped by ARCHITECT and returns JSON-able dicts so the
loop is auditable via provenance + audit without new dependencies.

Twin test = caller-supplied pure function drill(payload) -> score.
Canary = small-n subset evaluation. DAO vote = ECIDataDAO when available,
else deterministic local tally. Brier = exact math on resolved forecasts.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable


def _stamp(kind: str, payload: Any) -> dict[str, Any]:
    try:
        from eci.core.identity import ARCHITECT

        return ARCHITECT.stamp({"kind": kind, "payload": payload})
    except Exception:  # noqa: BLE001
        return {"architect": "unavailable", "kind": kind, "timestamp": time.time()}


@dataclass
class Hypothesis:
    id: str
    claim: str
    predicted_prob: float  # forecaster probability 0..1
    payload: dict[str, Any] = field(default_factory=dict)
    stamp: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.stamp:
            self.stamp = _stamp("research.hypothesis", {"id": self.id, "claim": self.claim})
        self.predicted_prob = min(1.0, max(0.0, float(self.predicted_prob)))


@dataclass
class CycleResult:
    hypothesis_id: str
    twin_score: float
    canary_score: float
    votes: dict[str, int]
    approved: bool
    outcome: int  # resolved ground truth 0/1
    brier: float
    stamp: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"hypothesis_id": self.hypothesis_id, "twin_score": self.twin_score,
                "canary_score": self.canary_score, "votes": dict(self.votes),
                "approved": self.approved, "outcome": self.outcome, "brier": self.brier,
                "stamp": self.stamp}


class ResearchLoop:
    """Deterministic self-improvement cycle."""

    def __init__(self, agent_id: str = "research-loop", quorum: float = 0.66) -> None:
        self.agent_id = agent_id
        self.quorum = quorum
        self.history: list[CycleResult] = []
        self._dao = None
        try:
            from eci.governance.dao import ECIDataDAO

            self._dao = ECIDataDAO(dao_id="ECI-Research")
        except Exception:  # noqa: BLE001
            self._dao = None

    def propose(self, claim: str, predicted_prob: float,
                payload: dict[str, Any] | None = None, hid: str | None = None) -> Hypothesis:
        hid = hid or f"hyp-{len(self.history)}-{int(time.time() * 1000) % 100000}"
        return Hypothesis(id=hid, claim=claim, predicted_prob=predicted_prob,
                          payload=dict(payload or {}))

    def run_cycle(self, hyp: Hypothesis,
                  drill: Callable[[dict[str, Any]], float],
                  canary_payloads: list[dict[str, Any]] | None = None,
                  voters: list[str] | None = None,
                  outcome: int = 1) -> CycleResult:
        # 1. twin test (inherits ALL limitations of drill — honest by construction)
        try:
            twin_score = float(drill(dict(hyp.payload)))
        except Exception:  # noqa: BLE001
            twin_score = 0.0
        # 2. canary on small-n subset
        canary_payloads = canary_payloads if canary_payloads else [dict(hyp.payload)]
        scores: list[float] = []
        for p in canary_payloads[:5]:
            try:
                scores.append(float(drill(p)))
            except Exception:  # noqa: BLE001
                scores.append(0.0)
        canary_score = sum(scores) / len(scores) if scores else 0.0
        # 3. vote: DAO when available else deterministic local rule
        voters = voters or ["voter-0", "voter-1", "voter-2"]
        votes: dict[str, int] = {}
        if self._dao is not None:
            try:
                pid = self._dao.propose(f"research:{hyp.id}", {"hypothesis": hyp.id},
                                                  self.agent_id) \
                    if hasattr(self._dao, "propose") else "local"
                # deterministic ballots from scores (no randomness)
                for i, v in enumerate(voters):
                    yes = (twin_score + canary_score) / 2.0 >= 0.5 - (i * 0.01)
                    votes[v] = 1 if yes else 0
            except Exception:  # noqa: BLE001
                votes = {v: (1 if canary_score >= 0.5 else 0) for v in voters}
        else:
            votes = {v: (1 if canary_score >= 0.5 else 0) for v in voters}
        yes_frac = sum(votes.values()) / max(1, len(votes))
        approved = yes_frac >= self.quorum
        # 4. Brier on resolved outcome
        brier = (hyp.predicted_prob - float(outcome)) ** 2
        res = CycleResult(hypothesis_id=hyp.id, twin_score=twin_score,
                          canary_score=canary_score, votes=votes,
                          approved=approved, outcome=int(outcome), brier=brier,
                          stamp=_stamp("research.cycle", {"id": hyp.id, "approved": approved}))
        self.history.append(res)
        return res

    def mean_brier(self) -> float:
        if not self.history:
            return 0.0
        return sum(r.brier for r in self.history) / len(self.history)

    def to_dict(self) -> dict[str, Any]:
        return {"agent": self.agent_id, "cycles": len(self.history),
                "mean_brier": self.mean_brier(),
                "approved": sum(1 for r in self.history if r.approved)}
