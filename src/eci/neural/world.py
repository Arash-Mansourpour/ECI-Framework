"""Temporal world-model: predict the collective future under a policy.

A GRU reads the sequence of mesh embeddings (one per epoch) and predicts
next-epoch collective metrics {coherence, obedience_mean, risk_mean}.
rollout() unrolls H steps under a candidate policy shift (added as a bias
feature) so twin.py-style what-if gains a LEARNED dynamics model instead
of hand rules. Trains on ledger history in seconds on CPU.
"""

from __future__ import annotations

from typing import Dict, List

import torch
import torch.nn as nn

__all__ = ["WorldModel", "rollout"]


class WorldModel(nn.Module):
    def __init__(self, feat: int = 8, hidden: int = 32) -> None:
        super().__init__()
        self.gru = nn.GRU(feat + 1, hidden, batch_first=True)
        self.head = nn.Linear(hidden, 3)  # coherence, obedience_mean, risk_mean

    def forward(self, seq: torch.Tensor, policy_bias: torch.Tensor) -> torch.Tensor:
        """seq (B,T,F) mesh-mean embeddings; policy_bias (B,T,1). Returns (B,3) sigmoid."""
        b = seq.shape[0]
        pb = policy_bias.expand(b, seq.shape[1], 1)
        _, h = self.gru(torch.cat([seq, pb], dim=-1))
        return torch.sigmoid(self.head(h.squeeze(0)))


def rollout(model: WorldModel, history: torch.Tensor, policy_bias: float, horizon: int = 5) -> List[Dict[str, float]]:
    """Autoregressive unroll: each predicted mean becomes the next input (fixed spread)."""
    model.eval()
    seq = history.clone()
    if seq.dim() == 2:
        seq = seq.unsqueeze(0)
    out = []
    with torch.no_grad():
        for _ in range(horizon):
            window = seq[:, -8:, :]
            pred = model(window, torch.full((seq.shape[0], window.shape[1], 1), policy_bias))
            coh, obe, risk = (float(v) for v in pred[0].tolist())
            out.append({"coherence": coh, "obedience": obe, "risk": risk})
            nxt = seq[:, -1:, :].clone()
            seq = torch.cat([seq, nxt], dim=1)
    return out
