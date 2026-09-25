"""BrainWorkspace: predictive Global Neuronal Workspace ignition.

Implements Dehaene GNW + Whyte predictive extension:
- competition p = softmax(beta * salience); ignition if max(s) > theta and H < H*
- broadcast g = ignition * (1 - H/logN) sent to ALL populations (global modulation)
- predictive coding: top-down prediction (EMA of salience) vs bottom-up input;
  precision-weighted prediction error drives free-energy contribution
  F_region = KL-ish surprise + MSE, summed by KernelLedger upstream
"""

from __future__ import annotations

import math
from typing import Any

import torch

__all__ = ["BrainWorkspace"]


class BrainWorkspace:
    def __init__(self, n_regions: int = 8, beta: float = 4.0, theta: float = 0.6,
                 entropy_max: float = 0.85, pred_lr: float = 0.1) -> None:
        self.n = n_regions
        self.beta = beta
        self.theta = theta
        self.entropy_max = entropy_max
        self.pred_lr = pred_lr
        self.prediction = torch.full((n_regions,), 0.5)
        self.history: list[dict[str, Any]] = []

    def cycle(self, salience: torch.Tensor) -> dict[str, Any]:
        s = salience.to(torch.float32).reshape(self.n).clamp(0.0, 1.0)
        logits = self.beta * s.double()
        p = torch.softmax(logits, dim=0)
        ent = float((-(p * torch.log(p.clamp_min(1e-12))).sum() / math.log(self.n)).item())
        winner = int(torch.argmax(s).item())
        ignited = bool(s[winner].item() > self.theta and ent < self.entropy_max)
        broadcast = float(float(ignited) * (1.0 - ent))
        # predictive coding error
        err = (s - self.prediction)
        precision = 1.0 - ent  # focused states trust error more
        f_region = float((err.pow(2).mean() * (0.5 + precision)).item())
        # update top-down prediction toward input (slow)
        self.prediction = self.prediction + self.pred_lr * err
        rec: dict[str, Any] = {"winner": winner, "ignited": ignited,
                                  "broadcast": broadcast, "entropy": ent,
                                  "pred_error": float(err.abs().mean().item()),
                                  "free_energy": f_region}
        self.history.append(rec)
        if len(self.history) > 1024:
            del self.history[:len(self.history) - 1024]
        return {"probabilities": p.float(), **rec}

    def reportability(self) -> float:
        if not self.history:
            return 0.0
        return sum(float(r["broadcast"]) for r in self.history) / len(self.history)

    def ignition_rate(self) -> float:
        if not self.history:
            return 0.0
        return sum(1 for r in self.history if r["ignited"]) / len(self.history)
