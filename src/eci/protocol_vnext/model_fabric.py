"""ECI Model Fabric — Hybrid routing (trivial→deterministic … hard→frontier)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from eci.protocol_vnext.capability import AdaptiveModelRouter, ContextualTrust

__all__ = ["ModelFabric"]


@dataclass
class ModelFabric:
    router: AdaptiveModelRouter = field(default_factory=AdaptiveModelRouter)
    trust: ContextualTrust = field(default_factory=ContextualTrust)

    def decide(self, manifest: Any, task: str, complexity: float, privacy: float, context: str = "default") -> dict[str, Any]:
        trust = self.trust.get(manifest.node_id, task, context)
        tier = self.router.route(manifest, trust, task, complexity, privacy)
        return {"tier": tier, "trust": round(trust, 3), "node": manifest.node_id}
