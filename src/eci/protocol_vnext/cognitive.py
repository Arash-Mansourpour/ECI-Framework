"""ECI-COG — Neuro-Cognitive Runtime.

Perception loop around LLM (Smith's NCA): LLM is one component of cognition,
not cognition itself. Loop: PERCEIVE→ORIENT→RECALL→SUBMINDS→REASON→PLAN→ACT→OBSERVE→VERIFY→REFLECT→ENCODE
+ Faculties (parallel subminds) + Gating (basal-ganglia control)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

__all__ = ["CognitiveFaculty", "CognitiveGating", "CognitiveRuntime"]


@dataclass
class CognitiveFaculty:
    name: str
    active: bool = False
    last_output: Any = None
    calls: int = 0

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        self.active = True
        self.calls += 1
        # faculty-specific logic is pluggable; default is a scored stub
        self.last_output = {"faculty": self.name, "input_keys": sorted(context.keys()), "ts": time.time()}
        return self.last_output


FACULTIES = ["Reasoning", "Evidence", "Critic", "Planning", "Prediction", "Memory", "Risk", "Metacognition", "Novelty"]


class CognitiveGating:
    """Decides which faculties are actually needed (cost control)."""

    def select(self, task: str, complexity: float) -> list[str]:
        if complexity < 0.3:
            return ["Reasoning", "Memory"]
        if complexity < 0.7:
            return ["Reasoning", "Evidence", "Planning", "Memory"]
        return FACULTIES  # hard tasks use all


@dataclass
class CognitiveRuntime:
    faculties: dict[str, CognitiveFaculty] = field(default_factory=lambda: {n: CognitiveFaculty(n) for n in FACULTIES})
    gating: CognitiveGating = field(default_factory=CognitiveGating)
    history: list[dict[str, Any]] = field(default_factory=list)

    def cycle(self, perception: dict[str, Any], task: str = "general", complexity: float = 0.5) -> dict[str, Any]:
        active = self.gating.select(task, complexity)
        results: dict[str, Any] = {}
        for name in active:
            fac = self.faculties[name]
            try:
                results[name] = fac.run(perception)
            except Exception as e:  # graceful degradation: one faculty crash ≠ death
                results[name] = {"error": str(e), "degraded": True}
        # verify step
        verified = all("error" not in v or v.get("degraded") for v in results.values())
        # reflect + encode (stub: record)
        record = {"task": task, "active": active, "results": list(results.keys()), "verified": verified, "ts": time.time()}
        self.history.append(record)
        return {"perception": perception, "faculties": results, "verified": verified, "record": record}

    def health(self) -> dict[str, Any]:
        return {"faculties": {k: v.calls for k, v in self.faculties.items()}, "cycles": len(self.history)}
