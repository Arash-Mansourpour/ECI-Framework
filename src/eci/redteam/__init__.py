"""Adversarial epistemology: the loyal opposition every AGI needs.

- Challenger: falsification probes for hypotheses/facts — negations,
  boundary mutations, and cross-source contradictions (templates, seeded).
- Forecasters: Brier-scored prediction registry; scores flow back into
  ReputationBoard so truth-tracking *pays* and punditry costs.
- Contradiction scan: same subject+predicate with rival objects at high
  confidence -> auto-Dispute objects for the commons (never silent).
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

__all__ = ["Probe", "Challenger", "ForecasterRegistry", "contradiction_scan"]


@dataclass
class Probe:
    target: str
    kind: str            # negation | boundary | cross-source
    claim: str
    severity: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {"target": self.target, "kind": self.kind,
                "claim": self.claim, "severity": self.severity}


class Challenger:
    def __init__(self, seed: int = 0) -> None:
        self.rng = random.Random(seed)
        self.issued = 0

    def falsify(self, hypothesis: str, context: str = "") -> List[Probe]:
        negs = [f"NOT({hypothesis}) under {context}" if context else f"NOT({hypothesis})",
                f"{hypothesis} fails at boundary {self.rng.choice(['zero', 'saturation', 'empty-input'])}",
                f"rival source contradicts: {hypothesis}"]
        kinds = ["negation", "boundary", "cross-source"]
        out = [Probe(hypothesis, k, c, severity=round(self.rng.uniform(0.4, 0.9), 2))
               for k, c in zip(kinds, negs)]
        self.issued += len(out)
        return out


@dataclass
class _Forecast:
    fid: str
    forecaster: str
    claim: str
    prob: float
    outcome: Optional[bool] = None
    ts: float = field(default_factory=time.time)


class ForecasterRegistry:
    """Brier-scored predictions; reputation deltas computed, not vibes."""

    def __init__(self) -> None:
        self._fs: Dict[str, _Forecast] = {}
        self._seq = 0

    def predict(self, forecaster: str, claim: str, prob: float) -> str:
        self._seq += 1
        fid = f"fc-{self._seq}"
        self._fs[fid] = _Forecast(fid, forecaster, claim, max(0.0, min(1.0, prob)))
        return fid

    def resolve(self, fid: str, outcome: bool) -> Dict[str, Any]:
        f = self._fs[fid]
        f.outcome = outcome
        brier = (f.prob - (1.0 if outcome else 0.0)) ** 2
        return {"fid": fid, "brier": brier, "skill": 0.25 - brier,
                "forecaster": f.forecaster}

    def leaderboard(self) -> List[Dict[str, Any]]:
        agg: Dict[str, List[float]] = {}
        for f in self._fs.values():
            if f.outcome is None:
                continue
            agg.setdefault(f.forecaster, []).append((f.prob - (1.0 if f.outcome else 0.0)) ** 2)
        rows = [{"forecaster": k, "brier": sum(v) / len(v), "n": len(v)} for k, v in agg.items()]
        return sorted(rows, key=lambda r: r["brier"])


def contradiction_scan(facts: List[Dict[str, Any]],
                       confidence_floor: float = 0.7) -> List[Dict[str, Any]]:
    """Find (subject, predicate) with rival high-confidence objects."""
    groups: Dict[tuple, List[Dict[str, Any]]] = {}
    for f in facts:
        if float(f.get("confidence", 0)) >= confidence_floor:
            groups.setdefault((f.get("subject"), f.get("predicate")), []).append(f)
    disputes = []
    for (s, p), fs in groups.items():
        objs = {str(f.get("object")) for f in fs}
        if len(objs) > 1:
            disputes.append({"subject": s, "predicate": p, "rivals": sorted(objs),
                             "fids": [f.get("fid", f.get("id", "?")) for f in fs],
                             "action": "open Dispute in commons"})
    return disputes
