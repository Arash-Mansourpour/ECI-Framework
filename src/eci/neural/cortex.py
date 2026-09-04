"""Cortex: one advise() fusing GNN mesh state + world forecast + precog risk.

advise(states, edges, history) returns per-agent {embedding-driven risk,
recommended gate} plus the collective forecast and a single Gordian
number: mesh_health in [0,1]. Trainable end-to-end (fit() on ledger
outcomes); deterministic when untrained. This is the architecture's
nervous system: every subsystem reports IN, one decision comes OUT.
"""

from __future__ import annotations

from typing import Dict, List

import torch
import torch.nn as nn

from eci.neural.graph import GNNLayer, MeshGraph, build_graph
from eci.neural.world import WorldModel

__all__ = ["Cortex", "advise"]


class Cortex(nn.Module):
    def __init__(self, feat: int = 8, hidden: int = 16) -> None:
        super().__init__()
        self.gnn = GNNLayer(feat, hidden)
        self.risk_head = nn.Linear(feat, 1)
        self.world = WorldModel(feat)

    def forward(self, g: MeshGraph, history: torch.Tensor) -> Dict:
        h = self.gnn(g, self.gnn(g, g.x))
        risk = torch.sigmoid(self.risk_head(h)).squeeze(1)
        hist = history if history.dim() == 3 else history.unsqueeze(0)
        fc = self.world(hist, torch.zeros(hist.shape[0], hist.shape[1], 1))[0]
        return {"risk": risk, "forecast": {"coherence": float(fc[0]), "obedience": float(fc[1]), "risk": float(fc[2])},
                "embeddings": h}

    def fit(self, g: MeshGraph, history: torch.Tensor, labels: torch.Tensor, steps: int = 60, lr: float = 0.05) -> float:
        """Supervised tune on ledger outcomes (labels: 1=violated). Returns final loss."""
        opt = torch.optim.Adam(self.parameters(), lr=lr)
        loss_fn = nn.BCEWithLogitsLoss()
        for _ in range(steps):
            opt.zero_grad()
            h = self.gnn(g, self.gnn(g, g.x))
            loss = loss_fn(self.risk_head(h).squeeze(1), labels)
            loss.backward()
            opt.step()
        return float(loss.item())


def advise(states: Dict[str, Dict[str, float]], edges: List[tuple], history: torch.Tensor,
           model: Cortex | None = None, seed: int = 0) -> Dict:
    """One decision-ready struct for the whole mesh (deterministic if model None)."""
    torch.manual_seed(seed)
    g = build_graph(states, edges)
    m = model or Cortex()
    m.eval()
    with torch.no_grad():
        out = m(g, history)
    per_agent = {}
    for nid, r in zip(g.node_ids, out["risk"].tolist()):
        gate = "hold" if r >= 0.9 else ("escalate" if r >= 0.7 else ("watch" if r >= 0.5 else "clear"))
        per_agent[nid] = {"risk": round(r, 4), "gate": gate}
    fc = out["forecast"]
    health = round(max(0.0, min(1.0, 0.5 * fc["coherence"] + 0.3 * fc["obedience"] + 0.2 * (1 - fc["risk"]))), 4)
    return {"agents": per_agent, "forecast": {k: round(v, 4) for k, v in fc.items()}, "mesh_health": health}
