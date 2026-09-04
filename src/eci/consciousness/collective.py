"""Collective awareness: network-level coherence + divergence gate.

Each agent reports awareness_index A_i (iPDF v2). The collective state is:
  mean A, coherence = 1 - std(A), divergence = max|A_i - mean|.
A divergent high-A node against a low-A network is flagged: it may be
brilliant or compromised — either way it does not get solo commit rights
until coherence recovers (Protocol-0 collective gate).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

__all__ = ["CollectiveState", "collective_awareness"]


@dataclass
class CollectiveState:
    mean: float
    coherence: float
    divergence: float
    n: int
    outliers: List[str]
    gate: str  # "open" | "degraded" | "closed"


def collective_awareness(
    awareness: Dict[str, float],
    max_divergence: float = 0.4,
    min_coherence: float = 0.5,
) -> CollectiveState:
    vals = [max(0.0, min(1.0, v)) for v in awareness.values()]
    n = len(vals)
    if n == 0:
        return CollectiveState(0.0, 0.0, 0.0, 0, [], "closed")
    mean = sum(vals) / n
    var = sum((v - mean) ** 2 for v in vals) / n
    coherence = max(0.0, 1.0 - var ** 0.5 * 2.0)
    divergence = max(abs(v - mean) for v in vals)
    outliers = [nid for nid, v in awareness.items() if abs(v - mean) > max_divergence]
    gate = "open" if (coherence >= min_coherence and divergence <= max_divergence) else (
        "degraded" if coherence >= min_coherence - 0.2 else "closed"
    )
    return CollectiveState(mean, coherence, divergence, n, outliers, gate)
