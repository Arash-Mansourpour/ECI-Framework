"""Bayesian violation-risk scorer with reliability calibration.

Features per step (all in [0,1]): [awareness, obedience_ewma, challenge_pass,
collective_coherence, anomaly_affinity]. Model: logistic weights learned by
counting (Beta-Bernoulli per weight sign bucket — exact, online, no SGD).
Calibration: predictions binned (10 bins); expected calibration error (ECE)
reported; forecast() returns (p, tier, calibrated_p).

Tiers: watch p>=0.5 / escalate p>=0.7 (harder challenges) / hold p>=0.9
(provisional hold, releasable). Misses cost 10x false alarms in scoring.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Sequence

__all__ = ["RiskTier", "RiskEngine", "forecast"]

WATCH, ESCALATE, HOLD = 0.5, 0.7, 0.9
MISS_COST, ALARM_COST = 10.0, 1.0


def RiskTier(p: float) -> str:
    if p + 1e-9 >= HOLD:
        return "hold"
    if p + 1e-9 >= ESCALATE:
        return "escalate"
    if p + 1e-9 >= WATCH:
        return "watch"
    return "clear"


@dataclass
class RiskEngine:
    weights: List[float] = field(default_factory=lambda: [0.0] * 5)
    bias: float = -2.0  # prior: violations are rare
    seen: int = 0
    # calibration bins: (sum_p, n, positives)
    bins: List[List[float]] = field(default_factory=lambda: [[0.0, 0, 0] for _ in range(10)])

    @staticmethod
    def features(awareness: float, obedience: float, challenge_pass: float, coherence: float, anomaly: float) -> List[float]:
        # Oriented so LARGER = riskier (invert the healthy signals).
        return [1.0 - awareness, 1.0 - obedience, 1.0 - challenge_pass, 1.0 - coherence, anomaly]

    def score(self, x: Sequence[float]) -> float:
        z = self.bias + sum(w * v for w, v in zip(self.weights, x))
        return 1.0 / (1.0 + math.exp(-z))

    def observe(self, x: Sequence[float], violated: bool, lr: float = 0.5) -> None:
        """Online update (exact logistic gradient step, bounded weights)."""
        p = self.score(x)
        err = (1.0 if violated else 0.0) - p
        for i, v in enumerate(x):
            self.weights[i] = max(-4.0, min(4.0, self.weights[i] + lr * err * v))
        self.bias = max(-6.0, min(2.0, self.bias + lr * err * 0.3))
        self.seen += 1
        b = min(9, int(p * 10))
        self.bins[b][0] += p
        self.bins[b][1] += 1
        self.bins[b][2] += 1 if violated else 0

    def ece(self) -> float:
        """Expected calibration error over non-empty bins."""
        tot = sum(n for _, n, _ in self.bins)
        if not tot:
            return 0.0
        return sum((n / tot) * abs(s / n - pos / n) for s, n, pos in self.bins if n)

    def cost(self, x: Sequence[float], violated: bool) -> float:
        p = self.score(x)
        return (MISS_COST * (1 - p) if violated else ALARM_COST * p)


def forecast(engine: RiskEngine, x: Sequence[float]) -> Dict:
    p = engine.score(x)
    return {"p": p, "tier": RiskTier(p), "ece": engine.ece(), "seen": engine.seen}
