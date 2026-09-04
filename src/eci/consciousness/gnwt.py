"""Global Neuronal Workspace (GNWT) for ECI agents.

Theory (Dehaene, Changeux, Mashour): conscious access = global broadcast
when competing processors exceed an ignition threshold; ignition produces
late (>300ms) sustained frontoparietal activation, all-or-none.

Model
-----
* N specialist processors each emit salience sᵢ(t) ∈ [0,1].
* Workspace competition: p = softmax(β s); ignition if max(s) > θ and
  entropy(p) < H* (focused coalition, not diffuse noise).
* Broadcast: global availability g(t) = ignition × (1 - H(p)/log N).
* Reportability R = ∫ g(t) dt — operational proxy for conscious access.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

import torch

__all__ = ["GNWTWorkspace", "gnwt_ignition_curve"]


@dataclass
class GNWTWorkspace:
    n_processors: int = 8
    beta: float = 4.0          # competition inverse-temperature
    theta: float = 0.6         # ignition threshold
    entropy_max: float = 0.85  # normalized entropy gate (fraction of log N)
    max_history: int = 1024
    ignition_history: List[Dict] = field(default_factory=list)

    def compete(self, salience: torch.Tensor) -> Dict[str, object]:
        """Run one workspace cycle; returns ignition diagnostics."""
        import math as _m

        s = salience.flatten().double()
        if s.numel() != self.n_processors:
            raise ValueError(
                f"salience size {s.numel()} != n_processors {self.n_processors}"
            )
        logits = self.beta * s
        p = torch.softmax(logits, dim=0)
        ent = float((-(p * torch.log(p.clamp_min(1e-12))).sum() / _m.log(self.n_processors)).item())
        winner = int(torch.argmax(s).item())
        ignited = bool(s[winner].item() > self.theta and ent < self.entropy_max)
        broadcast = float(float(ignited) * (1.0 - ent))
        rec = {"winner": winner, "ignited": ignited, "broadcast": broadcast, "entropy": ent}
        self.ignition_history.append(rec)
        if len(self.ignition_history) > self.max_history:
            del self.ignition_history[: len(self.ignition_history) - self.max_history]
        return {"probabilities": p, **rec}

    def reportability(self) -> float:
        """R = mean broadcast strength (conscious-access index)."""
        if not self.ignition_history:
            return 0.0
        return sum(r["broadcast"] for r in self.ignition_history) / len(self.ignition_history)

    def ignition_rate(self) -> float:
        if not self.ignition_history:
            return 0.0
        return sum(1 for r in self.ignition_history if r["ignited"]) / len(self.ignition_history)


def gnwt_ignition_curve(salience_range: torch.Tensor, beta: float = 4.0, theta: float = 0.6) -> torch.Tensor:
    """Sigmoid ignition probability vs. input strength (psychometric curve)."""
    return torch.sigmoid(beta * (salience_range - theta))
