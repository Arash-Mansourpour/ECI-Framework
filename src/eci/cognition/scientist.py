"""Scientist loop: abduction -> BIC scoring -> designed experiment -> belief.

The autonomous-science slice AGI needs: anomalies become hypotheses with
*equations*, hypotheses compete on BIC (fit minus complexity), the winner
earns its next datapoint by maximum-variance design, and beliefs update by
conjugate Gaussian rules. Promotion to the semantic commons requires
crossing evidence + replication thresholds — no hype-driven facts.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

__all__ = ["Hypothesis", "Scientist"]


@dataclass
class Hypothesis:
    name: str
    equation: str            # e.g. "y = a*x + b"
    k: int                   # free parameters (complexity penalty)
    rss: float = 0.0         # residual sum of squares
    n: int = 0               # supporting samples
    mean: float = 0.0        # posterior mean of headline effect
    prec: float = 1.0        # posterior precision
    replications: int = 0

    def bic(self) -> float:
        if self.n < 2 or self.rss <= 0:
            return float("inf")
        return self.n * math.log(self.rss / self.n) + self.k * math.log(self.n)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "equation": self.equation, "k": self.k,
                "n": self.n, "bic": self.bic(), "mean": self.mean,
                "prec": self.prec, "replications": self.replications}


class Scientist:
    """Competing-hypothesis engine with conjugate updates."""

    def __init__(self, promote_bic_gap: float = 6.0, promote_reps: int = 2) -> None:
        self.hypos: dict[str, Hypothesis] = {}
        self.promote_bic_gap = promote_bic_gap
        self.promote_reps = promote_reps

    def propose(self, name: str, equation: str, k: int) -> Hypothesis:
        h = Hypothesis(name, equation, k)
        self.hypos[name] = h
        return h

    def observe(self, name: str, xs: Sequence[float], ys: Sequence[float],
                pred: Sequence[float]) -> Hypothesis:
        """Score fit (RSS) + conjugate belief update on the residual mean."""
        h = self.hypos[name]
        rss = sum((y - p) ** 2 for y, p in zip(ys, pred))
        h.rss += rss
        h.n += len(ys)
        # conjugate Gaussian update on mean residual
        if ys:
            m = sum(y - p for y, p in zip(ys, pred)) / len(ys)
            lik_prec = len(ys) / (rss / len(ys) + 1e-9)
            h.mean = (h.prec * h.mean + lik_prec * m) / (h.prec + lik_prec)
            h.prec += lik_prec
        h.replications += 1
        return h

    def compete(self) -> dict[str, Any]:
        ranked = sorted(self.hypos.values(), key=lambda h: h.bic())
        table = [h.to_dict() for h in ranked]
        gap = (ranked[1].bic() - ranked[0].bic()) if len(ranked) > 1 else float("inf")
        winner = ranked[0] if ranked else None
        promotable = bool(winner and winner.replications >= self.promote_reps
                          and (gap >= self.promote_bic_gap or len(ranked) == 1)
                          and math.isfinite(winner.bic()))
        return {"ranking": table, "winner": winner.name if winner else None,
                "bic_gap": gap, "promotable": promotable,
                "promote_to_commons": promotable}

    def design_next(self, candidates: Sequence[float],
                    unc: Sequence[float]) -> dict[str, Any]:
        """Maximum-uncertainty design: sample where we know least."""
        i = max(range(len(candidates)), key=lambda j: unc[j])
        return {"x": candidates[i], "expected_info_gain": float(unc[i]), "rule": "max-variance"}
