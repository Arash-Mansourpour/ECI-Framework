"""ECI-CAP + Model Fabric + Contextual Trust.

- CapabilityVector: declared → observed → verified (EWMA + proof)
- Trust T(n,c,x) = contextual reputation per (node, capability, context)
- AdaptiveModelRouter: trivial→code, simple→SLM, private→local, domain→specialist, hard→frontier
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

__all__ = ["CapabilityVector", "CapabilityManifest", "ContextualTrust", "AdaptiveModelRouter", "ModelFabric"]


@dataclass
class CapabilityVector:
    python: float = 0.5
    security: float = 0.5
    research: float = 0.5
    coding: float = 0.5
    vision: float = 0.5

    def to_dict(self) -> dict[str, float]:
        return {"python": self.python, "security": self.security, "research": self.research,
                "coding": self.coding, "vision": self.vision}

    def score(self, task: str) -> float:
        return getattr(self, task, 0.5)


@dataclass
class CapabilityManifest:
    node_id: str
    models: list[str] = field(default_factory=lambda: ["local-model"])
    capabilities: CapabilityVector = field(default_factory=CapabilityVector)
    tools: list[str] = field(default_factory=list)
    privacy: str = "local_preferred"
    latency_ms: float = 730
    cost_class: str = "low"
    availability: float = 0.97
    declared_at: float = field(default_factory=time.time)
    # observed/verified are EWMA-updated by the network
    observed: CapabilityVector = field(default_factory=CapabilityVector)
    verified: CapabilityVector = field(default_factory=CapabilityVector)
    alpha: float = 0.2  # EWMA rate

    def observe(self, task: str, score: float) -> None:
        cur = getattr(self.observed, task, 0.5)
        setattr(self.observed, task, (1 - self.alpha) * cur + self.alpha * score)
        # verified is a slower EWMA over observed
        vcur = getattr(self.verified, task, 0.5)
        setattr(self.verified, task, 0.95 * vcur + 0.05 * getattr(self.observed, task))

    def to_dict(self) -> dict[str, Any]:
        return {"node": self.node_id, "models": self.models,
                "declared": self.capabilities.to_dict(),
                "observed": self.observed.to_dict(),
                "verified": self.verified.to_dict(),
                "privacy": self.privacy, "latency_ms": self.latency_ms,
                "cost_class": self.cost_class, "availability": self.availability}


class ContextualTrust:
    """T(n,c,x) — reputation per (node, capability, context)."""

    def __init__(self) -> None:
        self._scores: dict[tuple[str, str, str], float] = {}
        self._counts: dict[tuple[str, str, str], int] = {}

    def update(self, node: str, cap: str, ctx: str, outcome: float) -> float:
        k = (node, cap, ctx)
        prev = self._scores.get(k, 0.5)
        n = self._counts.get(k, 0)
        # incremental mean with decay for recency (EMA-like)
        new = 0.9 * prev + 0.1 * outcome if n > 5 else (prev * n + outcome) / (n + 1)
        self._scores[k] = max(0.0, min(1.0, new))
        self._counts[k] = n + 1
        return self._scores[k]

    def get(self, node: str, cap: str, ctx: str) -> float:
        return self._scores.get((node, cap, ctx), 0.5)

    def to_dict(self) -> dict[str, Any]:
        return {f"{n}/{c}/{x}": round(v, 3) for (n, c, x), v in self._scores.items()}


class AdaptiveModelRouter:
    """Routes Task → tier by Score = wc*C + wr*R + wp*P - wl*L - wk*K."""

    TIERS = ["deterministic", "slm", "local", "specialist", "frontier"]

    def __init__(self, wc=1.0, wr=0.8, wp=1.2, wl=0.001, wk=0.5) -> None:
        self.wc, self.wr, self.wp, self.wl, self.wk = wc, wr, wp, wl, wk

    def route(self, manifest: CapabilityManifest, trust: float, task: str, complexity: float, privacy_need: float) -> str:
        cap = manifest.verified.score(task) if manifest.verified.score(task) != 0.5 else manifest.capabilities.score(task)
        score = self.wc * cap + self.wr * trust + self.wp * (1 - privacy_need) - self.wl * manifest.latency_ms - self.wk * (0 if manifest.cost_class == "low" else 1)
        # complexity pushes upward
        score += complexity * 0.3
        if complexity < 0.2:
            return "deterministic"
        if complexity < 0.4 and manifest.cost_class == "low":
            return "slm"
        if privacy_need > 0.7:
            return "local"
        if cap > 0.85 and manifest.models and "specialist" in manifest.models[0]:
            return "specialist"
        return "frontier" if score < 0.6 else "specialist"

    def estimate(self, task: str, complexity: float) -> dict[str, Any]:
        return {"task": task, "complexity": complexity, "tiers": self.TIERS}


@dataclass
class ModelFabric:
    router: AdaptiveModelRouter = field(default_factory=AdaptiveModelRouter)
    trust: ContextualTrust = field(default_factory=ContextualTrust)
