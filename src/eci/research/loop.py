"""Evidence-aware research cycles with explicit labels and reviewers.

Scores inherit the limitations of the supplied drill. Resolved outcomes must
carry a source, and synthetic votes are opt-in and marked as such. This keeps
demo mechanics distinguishable from externally reviewed research results.
"""

from __future__ import annotations

import json
import math
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


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
        probability = float(self.predicted_prob)
        if not math.isfinite(probability) or not 0.0 <= probability <= 1.0:
            raise ValueError("predicted_prob must be finite and in [0, 1]")
        self.predicted_prob = probability
        if not self.stamp:
            self.stamp = _stamp("research.hypothesis", {"id": self.id, "claim": self.claim})


@dataclass
class CycleResult:
    hypothesis_id: str
    twin_score: float
    canary_score: float
    votes: dict[str, int]
    approved: bool
    outcome: int  # resolved ground truth 0/1
    brier: float
    outcome_source: str
    vote_source: str
    canary_count: int
    policy_loss: float
    drill_failures: list[str] = field(default_factory=list)
    stamp: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"hypothesis_id": self.hypothesis_id, "twin_score": self.twin_score,
                "canary_score": self.canary_score, "votes": dict(self.votes),
                "approved": self.approved, "outcome": self.outcome, "brier": self.brier,
                "outcome_source": self.outcome_source, "vote_source": self.vote_source,
                "canary_count": self.canary_count,
                "policy_loss": self.policy_loss,
                "drill_failures": list(self.drill_failures),
                "stamp": self.stamp}


class ResearchLoop:
    """Deterministic self-improvement cycle."""

    def __init__(self, agent_id: str = "research-loop", quorum: float = 0.66,
                 vote_fn: Callable[[Hypothesis, dict[str, float]], Mapping[str, int]] | None = None,
                 bus: Any = None) -> None:
        if not math.isfinite(quorum) or not 0.0 <= quorum <= 1.0:
            raise ValueError("quorum must be finite and in [0, 1]")
        self.agent_id = agent_id
        self.quorum = quorum
        self.history: list[CycleResult] = []
        self.vote_fn = vote_fn
        self.bus = bus

    def propose(self, claim: str, predicted_prob: float,
                payload: dict[str, Any] | None = None, hid: str | None = None) -> Hypothesis:
        hid = hid or f"hyp-{len(self.history)}-{int(time.time() * 1000) % 100000}"
        hypothesis = Hypothesis(id=hid, claim=claim, predicted_prob=predicted_prob,
                                payload=dict(payload or {}))
        self._publish("research.hypothesis.proposed", {
            "hypothesis_id": hypothesis.id,
            "predicted_prob": hypothesis.predicted_prob,
        })
        return hypothesis

    def run_cycle(self, hyp: Hypothesis,
                  drill: Callable[[dict[str, Any]], float],
                  canary_payloads: list[dict[str, Any]] | None = None,
                  voters: list[str] | None = None,
                  outcome: int | None = None,
                  outcome_source: str | None = None,
                  simulate_votes: bool = False) -> CycleResult:
        """Evaluate one hypothesis against an explicitly resolved outcome.

        Scores use the caller's drill and therefore inherit its limitations.
        A ground-truth outcome and its source are mandatory; synthetic voting
        is available only when explicitly requested for demos/tests.
        """
        if isinstance(outcome, bool) or not isinstance(outcome, int) or outcome not in (0, 1):
            raise ValueError("outcome must be a resolved binary label (0 or 1)")
        if not outcome_source or not outcome_source.strip():
            raise ValueError("outcome_source is required for a resolved label")

        failures: list[str] = []

        def evaluate(payload: dict[str, Any], label: str) -> float:
            try:
                score = float(drill(dict(payload)))
                if not math.isfinite(score) or not 0.0 <= score <= 1.0:
                    raise ValueError("drill score must be finite and in [0, 1]")
                return score
            except Exception as exc:  # noqa: BLE001
                failures.append(f"{label}: {type(exc).__name__}: {str(exc)[:160]}")
                return 0.0

        # 1. held-out/twin score. Its validity depends on the supplied drill.
        twin_score = evaluate(hyp.payload, "twin")
        # 2. evaluate every supplied canary case; do not silently truncate data.
        canary_payloads = canary_payloads if canary_payloads is not None else [dict(hyp.payload)]
        if not canary_payloads:
            raise ValueError("canary_payloads must contain at least one case")
        scores: list[float] = []
        for i, payload in enumerate(canary_payloads):
            scores.append(evaluate(payload, f"canary[{i}]"))
        canary_score = sum(scores) / len(scores) if scores else 0.0
        # 3. Real votes come from an injected reviewer/DAO adapter. Synthetic
        # ballots are opt-in and are clearly identified in the result.
        if self.vote_fn is not None:
            raw_votes = self.vote_fn(hyp, {
                "twin_score": twin_score,
                "canary_score": canary_score,
                "canary_count": float(len(scores)),
                "drill_failure_rate": len(failures) / (1 + len(scores)),
            })
            if not isinstance(raw_votes, Mapping) or any(
                isinstance(v, bool) or not isinstance(v, int) or v not in (0, 1)
                for v in raw_votes.values()
            ):
                raise ValueError("vote_fn must return voter IDs mapped to binary votes")
            votes = {str(k): int(v) for k, v in raw_votes.items()}
            vote_source = "configured-reviewer"
        elif simulate_votes:
            voters = voters or ["demo-voter-0", "demo-voter-1", "demo-voter-2"]
            votes = {v: int((twin_score + canary_score) / 2.0 >= 0.5 - i * 0.01)
                     for i, v in enumerate(voters)}
            vote_source = "synthetic-demo"
        else:
            votes = {}
            vote_source = "no-reviewer"
        yes_frac = sum(votes.values()) / len(votes) if votes else 0.0
        approved = bool(votes) and yes_frac >= self.quorum and not failures
        # 4. Brier on caller-supplied resolved ground truth.
        brier = (hyp.predicted_prob - float(outcome)) ** 2
        policy_loss = (int(approved) - int(outcome)) ** 2
        res = CycleResult(hypothesis_id=hyp.id, twin_score=twin_score,
                          canary_score=canary_score, votes=votes,
                          approved=approved, outcome=int(outcome), brier=brier,
                          outcome_source=outcome_source, vote_source=vote_source,
                          canary_count=len(scores),
                          policy_loss=float(policy_loss),
                          drill_failures=failures,
                          stamp=_stamp("research.cycle", {"id": hyp.id, "approved": approved}))
        self.history.append(res)
        self._publish("research.cycle.completed", {
            "hypothesis_id": res.hypothesis_id,
            "approved": res.approved,
            "outcome": res.outcome,
            "brier": res.brier,
            "policy_loss": res.policy_loss,
            "canary_count": res.canary_count,
            "drill_failures": len(res.drill_failures),
            "outcome_source": res.outcome_source,
            "vote_source": res.vote_source,
        })
        return res

    def _publish(self, event_type: str, payload: dict[str, Any]) -> None:
        if self.bus is None:
            return
        try:
            from eci.kernel.bus import Event

            self.bus.publish(Event(type=event_type, source=self.agent_id, payload=payload))
        except Exception:  # noqa: BLE001
            # Telemetry must not change an already resolved research result.
            return

    def mean_brier(self) -> float | None:
        if not self.history:
            return None
        return sum(r.brier for r in self.history) / len(self.history)

    def mean_policy_loss(self) -> float | None:
        if not self.history:
            return None
        return sum(r.policy_loss for r in self.history) / len(self.history)

    def mean_objective(self) -> float | None:
        """Calibration loss plus decision loss, both on resolved outcomes."""
        if not self.history:
            return None
        return sum(r.brier + r.policy_loss for r in self.history) / len(self.history)

    def to_dict(self) -> dict[str, Any]:
        return {"agent": self.agent_id, "cycles": len(self.history),
                "mean_brier": self.mean_brier(),
                "mean_policy_loss": self.mean_policy_loss(),
                "mean_objective": self.mean_objective(),
                "approved": sum(1 for r in self.history if r.approved),
                "results": [result.to_dict() for result in self.history]}

    def export_json(self, path: str | Path) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n",
                               encoding="utf-8")
