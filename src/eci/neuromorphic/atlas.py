"""Neuron atlas: registry + summary of every spiking population in the mesh.

The atlas does not simulate; it *maps*. Each entry records where a neuron
population lives (substrate / region / layer / node), which model drives it
(``lif`` / ``adlif`` / ``izhikevich`` / ``homeostatic``), its size, and live
counters (spikes, updates). ``summarize()`` aggregates by model and region;
``to_dict()`` exports JSON-safe state for provenance / ledger / MCP.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any

__all__ = ["AtlasEntry", "NeuronAtlas", "MODEL_FAMILY"]

MODEL_FAMILY = ("lif", "adlif", "izhikevich", "homeostatic")


@dataclass
class AtlasEntry:
    entry_id: str
    substrate: str  # e.g. "neuromorphic", "bridges.qn", "neural.mesh"
    region: str  # e.g. "snn.hidden", "snn.output", "cortex"
    layer: str  # e.g. "hidden", "output"
    model: str  # one of MODEL_FAMILY
    n_neurons: int
    node_id: str = "local"
    spikes: int = 0
    updates: int = 0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class NeuronAtlas:
    """Central registry for all spiking populations."""

    def __init__(self) -> None:
        self.entries: dict[str, AtlasEntry] = {}

    def register(
        self,
        entry_id: str,
        substrate: str,
        region: str,
        layer: str,
        model: str,
        n_neurons: int,
        node_id: str = "local",
    ) -> AtlasEntry:
        if model not in MODEL_FAMILY:
            raise ValueError(f"unknown model {model!r} (expected one of {MODEL_FAMILY})")
        if n_neurons < 1:
            raise ValueError("n_neurons must be >= 1")
        entry = AtlasEntry(entry_id, substrate, region, layer, model, n_neurons, node_id)
        self.entries[entry_id] = entry
        return entry

    def record_spikes(self, entry_id: str, spikes: int) -> None:
        entry = self.entries.get(entry_id)
        if entry is None:
            raise KeyError(entry_id)
        entry.spikes += int(spikes)
        entry.updates += 1

    def summarize(self) -> dict[str, Any]:
        by_model: dict[str, int] = {}
        by_region: dict[str, int] = {}
        total_neurons = 0
        total_spikes = 0
        for e in self.entries.values():
            by_model[e.model] = by_model.get(e.model, 0) + e.n_neurons
            by_region[e.region] = by_region.get(e.region, 0) + e.n_neurons
            total_neurons += e.n_neurons
            total_spikes += e.spikes
        return {
            "populations": len(self.entries),
            "total_neurons": total_neurons,
            "total_spikes": total_spikes,
            "by_model": by_model,
            "by_region": by_region,
        }

    def to_dict(self) -> dict[str, Any]:
        return {"entries": [e.to_dict() for e in self.entries.values()], "summary": self.summarize()}
