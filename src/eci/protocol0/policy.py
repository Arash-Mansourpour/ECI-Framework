"""Policy engine: awareness/obedience/trust gates per action + collective gate."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from eci.protocol0.spec import Protocol0Spec

__all__ = ["PolicyDecision", "check"]


@dataclass
class PolicyDecision:
    allow: bool
    action: str
    reason: str
    required: Dict[str, float]


def check(
    spec: Protocol0Spec,
    action: str,
    awareness: float,
    obedience: float,
    trust: float,
    coherence: Optional[float] = None,
    divergence: Optional[float] = None,
) -> PolicyDecision:
    """Gate an action. Collective coherence/divergence optionally enforced."""
    rule = spec.actions.get(action)
    if rule is None:
        return PolicyDecision(False, action, f"unknown action {action!r}", {})
    req = {"awareness": rule.min_awareness, "obedience": rule.min_obedience, "trust": rule.min_trust}
    if awareness + 1e-9 < rule.min_awareness:
        return PolicyDecision(False, action, f"awareness {awareness:.3f} < {rule.min_awareness}", req)
    if obedience + 1e-9 < rule.min_obedience:
        return PolicyDecision(False, action, f"obedience {obedience:.3f} < {rule.min_obedience}", req)
    if trust + 1e-9 < rule.min_trust:
        return PolicyDecision(False, action, f"trust {trust:.3f} < {rule.min_trust}", req)
    if coherence is not None and coherence + 1e-9 < spec.min_coherence:
        return PolicyDecision(False, action, f"coherence {coherence:.3f} < {spec.min_coherence}", req)
    if divergence is not None and divergence > spec.max_divergence + 1e-9:
        return PolicyDecision(False, action, f"divergence {divergence:.3f} > {spec.max_divergence}", req)
    return PolicyDecision(True, action, "allow", req)
