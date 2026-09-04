"""Federation bridge: mutual ledger anchoring + policy translation.

Anchor: mesh A appends mesh B's ledger head {height, hash} into its own
ledger (and vice versa) — a cross-signed checkpoint neither side can
rewrite. Translation: each direction carries a per-action weight factor
negotiated out-of-band; foreign votes count as weight*factor locally.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

__all__ = ["TranslationMap", "Bridge", "anchor", "translate_vote"]


@dataclass
class TranslationMap:
    """Per-action foreign-weight factors for one direction (A->B)."""

    factors: Dict[str, float] = field(default_factory=dict)
    default: float = 0.5

    def factor(self, action: str) -> float:
        return float(self.factors.get(action, self.default))


@dataclass
class Bridge:
    mesh_a: str
    mesh_b: str
    a_to_b: TranslationMap = field(default_factory=TranslationMap)
    b_to_a: TranslationMap = field(default_factory=TranslationMap)
    anchors: list = field(default_factory=list)

    def direction(self, source: str) -> TranslationMap:
        if source == self.mesh_a:
            return self.a_to_b
        if source == self.mesh_b:
            return self.b_to_a
        raise ValueError(f"unknown mesh {source!r} for this bridge")


def anchor(bridge: Bridge, ledger_a, ledger_b) -> Dict[str, Any]:
    """Cross-sign heads both ways; returns the anchor record pair."""
    ha, hb = ledger_a.snapshot(), ledger_b.snapshot()
    ra = ledger_a.append("federation_anchor", {"mesh": bridge.mesh_b, "head": hb})
    rb = ledger_b.append("federation_anchor", {"mesh": bridge.mesh_a, "head": ha})
    bridge.anchors.append({"a": ra["hash"], "b": rb["hash"]})
    return {"a": ra, "b": rb}


def translate_vote(bridge: Bridge, source_mesh: str, action: str, weight: float) -> float:
    """Foreign vote weight as counted locally (never amplifies: capped at 1x)."""
    return max(0.0, weight) * min(1.0, bridge.direction(source_mesh).factor(action))
