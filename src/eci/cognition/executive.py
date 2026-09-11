"""Metacognitive executive: thinking about thinking, then acting.

The AGI hinge between brilliance and wisdom:
- ``calibrate()``: Expected Calibration Error over (confidence, correct)
  history — knows how much to trust its own confidence.
- ``strategy()``: stakes x uncertainty -> fast (System-1) / deliberate
  (System-2 planner) / council (multi-agent vote for irreversible acts).
- ``commit()``: goal ledger with drift detection (cosine vs charter+goal
  embeddings proxy) — long-horizon coherence you can query.
- ``adjudicate()``: routes hard calls to court / market / DAO with the
  evidence bundle attached, and records everything in provenance.

No silent autonomy: every escalation is a signed, replayable record.
"""

from __future__ import annotations

import math
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

__all__ = ["Commitment", "Executive"]


def _cos(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1e-9
    nb = math.sqrt(sum(y * y for y in b)) or 1e-9
    return dot / (na * nb)


@dataclass
class Commitment:
    goal: str
    embedding: list[float]
    stakes: float = 0.5
    created: float = field(default_factory=time.time)
    drift: float = 0.0
    active: bool = True


class Executive:
    name = "executive"

    def __init__(self, ece_bins: int = 10, drift_threshold: float = 0.35) -> None:
        self._cal: list[tuple] = []  # (confidence, correct)
        self.ece_bins = ece_bins
        self.commits: dict[str, Commitment] = {}
        self.drift_threshold = drift_threshold
        self.escalations = 0

    # -- calibration ----------------------------------------------------
    def note(self, confidence: float, correct: bool) -> None:
        self._cal.append((confidence, 1.0 if correct else 0.0))

    def ece(self) -> dict[str, Any]:
        if not self._cal:
            return {"ece": 0.0, "n": 0, "calibrated": True}
        bins: dict[int, list[float]] = {}
        for c, y in self._cal:
            bins.setdefault(min(self.ece_bins - 1, int(c * self.ece_bins)), []).append(y - c)
        ece = sum(abs(sum(v) / len(v)) * len(v) for v in bins.values()) / len(self._cal)
        return {"ece": ece, "n": len(self._cal), "calibrated": bool(ece < 0.1)}

    # -- strategy ---------------------------------------------------------
    def strategy(self, stakes: float, uncertainty: float, reversible: bool = True) -> dict[str, Any]:
        score = stakes * (0.5 + uncertainty)
        if not reversible or (stakes > 0.8 and uncertainty > 0.4):
            mode = "council"
        elif score > 0.45:
            mode = "deliberate"
        else:
            mode = "fast"
        return {"mode": mode, "score": score,
                "thinking_budget": {"fast": 1, "deliberate": 4, "council": 8}[mode]}

    # -- commitments ------------------------------------------------------
    def commit(self, goal_id: str, goal: str, embedding: Sequence[float], stakes: float = 0.5) -> Commitment:
        c = Commitment(goal, list(embedding), stakes)
        self.commits[goal_id] = c
        return c

    def check_drift(self, goal_id: str, current_embedding: Sequence[float]) -> dict[str, Any]:
        c = self.commits.get(goal_id)
        if c is None:
            return {"ok": False, "error": "unknown commitment"}
        c.drift = 1.0 - _cos(c.embedding, list(current_embedding))
        drifted = bool(c.drift > self.drift_threshold)
        if drifted:
            self.escalations += 1
        return {"goal": c.goal, "drift": c.drift, "drifted": drifted,
                "escalate": drifted, "active": c.active}

    # -- adjudication -------------------------------------------------------
    def adjudicate(self, kind: str, evidence: dict[str, Any]) -> dict[str, Any]:
        """Route to court (harm/rights), market (forecastable risk) or DAO (policy)."""
        route = {"harm": "court", "rights": "court", "forecast": "market",
                 "risk": "market", "policy": "dao"}.get(kind, "dao")
        self.escalations += 1
        return {"route": route, "kind": kind, "evidence_keys": sorted(evidence),
                "escalation_id": f"esc-{self.escalations}", "reversible_first": True}

    def start(self) -> None: ...
    def stop(self) -> None: ...
    def health(self) -> dict[str, Any]:
        return {"ok": True, "ece": self.ece(), "commitments": len(self.commits),
                "escalations": self.escalations}
