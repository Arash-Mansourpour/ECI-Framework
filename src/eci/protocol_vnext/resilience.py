"""ECI Resilience — Graceful Degradation + Substrate Independence + Experimental Lab.

- Graceful: crash of one submind/transport/model ≠ death; degraded mode
- Substrate: Node MUST satisfy interface, not MUST be LLM (supports SLM, transformer, neuromorphic, symbolic, future OI)
- Experimental Lab: parallel reasoning manifolds (tree, constraint, graph, stochastic, analogical)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = ["GracefulDegradation", "SubstrateAdapter", "ExperimentalReasoningLab"]


class GracefulDegradation:
    def __init__(self) -> None:
        self.failures: list[dict[str, Any]] = []
        self.degraded_components: set[str] = set()

    def report_failure(self, component: str, error: str) -> dict[str, Any]:
        self.failures.append({"component": component, "error": error})
        self.degraded_components.add(component)
        return {"status": "degraded", "failed": component, "degraded_set": sorted(self.degraded_components),
                "message": f"{component} failed, system degraded (not dead)"}

    def is_degraded(self, component: str) -> bool:
        return component in self.degraded_components

    def recover(self, component: str) -> None:
        self.degraded_components.discard(component)

    def to_dict(self) -> dict[str, Any]:
        return {"degraded": sorted(self.degraded_components), "failures": len(self.failures)}


@dataclass
class SubstrateAdapter:
    substrate: str = "transformer"  # transformer/slm/neuromorphic/symbolic/organoid
    supported: list[str] = field(default_factory=lambda: ["transformer", "slm", "llm", "neuromorphic", "symbolic", "organoid"])

    def check(self) -> bool:
        return self.substrate in self.supported or self.substrate == "future"

    def wrap(self, node: Any) -> dict[str, Any]:
        return {"substrate": self.substrate, "interface_ok": self.check(), "node": getattr(node, "node_id", str(node))}


class ExperimentalReasoningLab:
    """Tests multiple reasoning manifolds in parallel, records which wins per task."""

    def __init__(self) -> None:
        self.manifolds = ["tree", "constraint", "graph", "stochastic", "analogical"]
        self.results: list[dict[str, Any]] = []

    def experiment(self, task: str, manifold: str, score: float) -> None:
        self.results.append({"task": task, "manifold": manifold, "score": score})

    def best_for(self, task: str) -> str | None:
        cands = [r for r in self.results if r["task"] == task]
        if not cands:
            return None
        return max(cands, key=lambda x: x["score"])["manifold"]

    def to_dict(self) -> dict[str, Any]:
        return {"manifolds": self.manifolds, "experiments": len(self.results)}
