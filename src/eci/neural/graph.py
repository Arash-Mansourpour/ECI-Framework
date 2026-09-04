"""Mesh graph: agents as nodes, trust as edges, GNN as reader.

Node features (8-D): [awareness, obedience, trust, challenge_score,
vote_rate, anomaly_affinity, precog_p, freshness]. Edge weight =
pairwise trust x interaction recency. gnn_step() is one message-passing
round: h_i <- tanh(W_self h_i + W_msg sum_j w_ij h_j). Stacked rounds let
risk propagate: a rogue's neighbors' embeddings shift BEFORE it acts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

import torch
import torch.nn as nn

__all__ = ["MeshGraph", "build_graph", "gnn_step", "GNNLayer"]

FEATURES = ["awareness", "obedience", "trust", "challenge", "vote_rate", "anomaly", "precog_p", "freshness"]


@dataclass
class MeshGraph:
    node_ids: List[str]
    x: torch.Tensor  # (n, 8) node features
    edge_index: torch.Tensor  # (2, E) directed edges
    edge_weight: torch.Tensor  # (E,)

    @property
    def n(self) -> int:
        return len(self.node_ids)


def build_graph(states: Dict[str, Dict[str, float]], edges: List[tuple]) -> MeshGraph:
    """states: agent -> feature dict (missing keys default neutrally)."""
    ids = sorted(states)
    defaults = {"awareness": 0.5, "obedience": 0.5, "trust": 0.5, "challenge": 0.5,
                "vote_rate": 0.3, "anomaly": 0.0, "precog_p": 0.1, "freshness": 1.0}
    rows = [[float(states[i].get(k, defaults[k])) for k in FEATURES] for i in ids]
    idx = {nid: j for j, nid in enumerate(ids)}
    ei, ew = [], []
    for a, b, w in edges:
        if a in idx and b in idx:
            ei.append([idx[a], idx[b]])
            ew.append(float(w))
    if not ei:
        ei, ew = [[i, i] for i in range(len(ids))], [1.0] * len(ids)  # self-loops fallback
    return MeshGraph(ids, torch.tensor(rows, dtype=torch.float32),
                     torch.tensor(ei, dtype=torch.long).t().contiguous(),
                     torch.tensor(ew, dtype=torch.float32))


class GNNLayer(nn.Module):
    """Single message-passing round with residual + LayerNorm (stable deep stacks)."""

    def __init__(self, dim: int = 8, hidden: int = 16) -> None:
        super().__init__()
        self.w_self = nn.Linear(dim, hidden)
        self.w_msg = nn.Linear(dim, hidden)
        self.w_out = nn.Linear(hidden, dim)
        self.norm = nn.LayerNorm(dim)

    def forward(self, g: MeshGraph, h: torch.Tensor) -> torch.Tensor:
        src, dst = g.edge_index[0], g.edge_index[1]
        msg = torch.zeros_like(h)
        msg.index_add_(0, dst, g.edge_weight.unsqueeze(1) * h[src])
        deg = torch.zeros(h.shape[0], 1)
        deg.index_add_(0, dst, g.edge_weight.unsqueeze(1))
        msg = msg / deg.clamp_min(1e-6)
        out = torch.tanh(self.w_self(h) + self.w_msg(msg))
        return self.norm(h + self.w_out(out))


def gnn_step(g: MeshGraph, h: torch.Tensor | None = None, rounds: int = 2, seed: int = 0) -> torch.Tensor:
    """Untrained-but-deterministic readout (seeded init); train weights via Cortex.fit."""
    torch.manual_seed(seed)
    layer = GNNLayer(dim=g.x.shape[1])
    h = g.x if h is None else h
    for _ in range(rounds):
        h = layer(g, h)
    return h
