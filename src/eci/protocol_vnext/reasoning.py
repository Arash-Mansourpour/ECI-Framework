"""ECI Reasoning: Multi-Dimensional Reasoning + Reasoning Landscape + World Model.

For multi-constraint problems, flattening to sequential steps loses trade-offs.
We map to constraint-space, compute Pareto frontier (Smith's hypothesis).
Also predictive world-model: current state → prediction → action → error → learning.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Any

__all__ = ["ReasoningLandscape", "ParetoFrontier", "PredictiveWorldModel"]


@dataclass
class ReasoningLandscape:
    problem: str
    dimensions: list[str]  # e.g. ["cost", "safety", "quality", "latency"]
    solutions: list[dict[str, float]] = field(default_factory=list)

    def propose(self, solution: dict[str, float]) -> None:
        self.solutions.append(solution)

    def pareto(self) -> list[dict[str, float]]:
        """Naive Pareto: solution is non-dominated if no other is >= in all dims and > in one."""
        frontier = []
        for s in self.solutions:
            dominated = False
            for o in self.solutions:
                if o is s:
                    continue
                if all(o.get(d, 0) >= s.get(d, 0) for d in self.dimensions) and any(o.get(d, 0) > s.get(d, 0) for d in self.dimensions):
                    dominated = True
                    break
            if not dominated:
                frontier.append(s)
        return frontier

    def to_dict(self) -> dict[str, Any]:
        return {"problem": self.problem, "dimensions": self.dimensions,
                "solutions": len(self.solutions), "pareto": self.pareto()}


class ParetoFrontier:
    @staticmethod
    def frontier(solutions: list[dict[str, float]], dims: list[str]) -> list[dict[str, float]]:
        land = ReasoningLandscape(problem="generic", dimensions=dims, solutions=solutions)
        return land.pareto()


@dataclass
class PredictiveWorldModel:
    """Internal model: predict next state, measure error, learn."""

    history: list[dict[str, Any]] = field(default_factory=list)
    predictions: list[dict[str, Any]] = field(default_factory=list)

    def predict(self, state: dict[str, Any]) -> dict[str, Any]:
        # simple stub: predict next coherence = current * 0.95 + noise
        pred = {"coherence": state.get("coherence", 0.5) * 0.95 + random.uniform(-0.05, 0.05),
                "predicted_from": state, "ts": time.time()}
        self.predictions.append(pred)
        return pred

    def observe(self, actual: dict[str, Any]) -> float:
        if not self.predictions:
            return 0.0
        pred = self.predictions[-1]
        err = abs(pred.get("coherence", 0.5) - actual.get("coherence", 0.5))
        self.history.append({"predicted": pred, "actual": actual, "error": err})
        return err

    def calibration(self) -> float:
        if not self.history:
            return 0.0
        return 1 - sum(h["error"] for h in self.history) / len(self.history)
