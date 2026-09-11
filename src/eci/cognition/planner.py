"""Uncertainty-aware planner: CEM over imagined futures (System-1/2).

Objective per candidate action sequence (horizon H, batch B):
  J = E[sum_t gamma^t (r_t + beta_info * u_t)] - lambda_risk * max_t u_t
where u_t is ensemble disagreement. CEM refits a Gaussian over elite
sequences for a few iterations. *Adaptive thinking*: iterations scale with
current uncertainty (low -> 1 iteration = System-1 reflex; high -> up to
max_iters = System-2 deliberation), and the whole trace records its
uncertainty budget for the executive + provenance.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import torch

__all__ = ["PlannerConfig", "CEMPlanner"]


@dataclass
class PlannerConfig:
    horizon: int = 8
    candidates: int = 64
    elites: int = 8
    base_iters: int = 1
    max_iters: int = 4
    gamma: float = 0.99
    beta_info: float = 0.5
    lambda_risk: float = 1.0
    unc_system2: float = 0.05  # above this -> deliberate


class CEMPlanner:
    def __init__(self, world: Any, cfg: PlannerConfig | None = None,
                 risk_fn: Callable[[torch.Tensor, torch.Tensor], float] | None = None) -> None:
        self.world = world
        self.cfg = cfg or PlannerConfig()
        self.risk_fn = risk_fn  # optional precog hook (h, z) -> scalar
        self.last_trace: dict[str, Any] = {}

    @torch.no_grad()
    def plan(self, h: torch.Tensor, z: torch.Tensor,
             seed: int = 0) -> dict[str, Any]:
        c, B = self.cfg, h.size(0)
        A, H = self.world.cfg.act_dim, c.horizon
        g = torch.Generator().manual_seed(seed)
        # adaptive thinking budget from current uncertainty probe
        with torch.no_grad():
            probe = self.world.imagine(h, z, lambda hh, zz: torch.zeros(B, A), horizon=2)
            u0 = float(probe["uncertainty"].mean().item())
        iters = c.base_iters if u0 < c.unc_system2 else c.max_iters
        system = 1 if iters == c.base_iters else 2
        mu = torch.zeros(H, A)
        std = torch.ones(H, A)
        gamma = torch.tensor([c.gamma ** t for t in range(H)])
        best_J, best_seq = float("-inf"), mu.clone()
        for _ in range(iters):
            seqs = mu.unsqueeze(0) + std.unsqueeze(0) * torch.randn(c.candidates, H, A, generator=g)
            seqs = seqs.tanh()  # bounded actions in [-1, 1]
            J = torch.zeros(c.candidates)
            U = torch.zeros(c.candidates)
            for i in range(c.candidates):
                sq = seqs[i]
                rollout = self.world.imagine(h, z, _seq_policy(sq), horizon=H)
                r = rollout["reward"]          # (H, B)
                u = rollout["uncertainty"]     # (H, B)
                ret = ((r + c.beta_info * u) * gamma.unsqueeze(1)).sum(0).mean()
                J[i] = float(ret.item()) - c.lambda_risk * float(u.max().item())
                U[i] = float(u.mean().item())
            elite = J.topk(min(c.elites, c.candidates)).indices
            mu, std = seqs[elite].mean(0), seqs[elite].std(0).clamp_min(1e-3)
            if float(J.max().item()) > best_J:
                best_J, best_seq = float(J.max().item()), seqs[J.argmax()].clone()
        risk_extra = 0.0
        if self.risk_fn is not None:
            try:
                risk_extra = float(self.risk_fn(h, z))
            except Exception:  # noqa: BLE001
                risk_extra = 0.0
        self.last_trace = {"iters": iters, "system": system, "u0": u0,
                           "J": best_J, "risk_extra": risk_extra}
        return {"action": best_seq[0].mean(0) if best_seq.dim() == 3 else best_seq[0],
                "sequence": best_seq, "value": best_J - risk_extra,
                "system": system, "iters": iters, "u0": u0}


def _seq_policy(sq: torch.Tensor):
    t = [0]

    def _pol(h: torch.Tensor, z: torch.Tensor) -> torch.Tensor:
        i = min(t[0], sq.size(0) - 1)
        t[0] += 1
        a = sq[i]
        return a.expand(h.size(0), -1) if a.dim() == 1 else a

    return _pol
