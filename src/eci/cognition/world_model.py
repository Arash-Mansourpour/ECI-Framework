"""Latent world model (RSSM-lite): the substrate of machine imagination.

A Recurrent State-Space Model with a deterministic GRU path + stochastic
Gaussian latent, plus a small dynamics *ensemble* whose disagreement is the
model's honest uncertainty signal. Supports one-step prediction, multi-step
``imagine()`` rollouts for planning, and surprise scoring for the dream
cycle. Toy-scale by design (obs_dim<=64, hidden<=128): the math is exact,
the capacity is deliberately small — scale the dims, not the equations.

Honest limits: Gaussian latents + MSE/Reconstruction losses assume roughly
unimodal smooth dynamics. Multimodal or symbolic dynamics need discrete
latents (listed in docs/COGNITION_AGI.md as the upgrade path).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import torch
import torch.nn as nn

__all__ = ["WorldModelConfig", "LatentWorldModel"]


@dataclass
class WorldModelConfig:
    obs_dim: int = 16
    act_dim: int = 4
    hidden: int = 64
    latent: int = 16
    ensemble: int = 3
    lr: float = 3e-3


class _DynamicsHead(nn.Module):
    def __init__(self, hidden: int, latent: int) -> None:
        super().__init__()
        self.mu = nn.Linear(hidden, latent)
        self.lv = nn.Linear(hidden, latent)

    def forward(self, h: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        return self.mu(h), self.lv(h).clamp(-6.0, 2.0)


class LatentWorldModel(nn.Module):
    """GRU + Gaussian latent + reward/discount heads + dynamics ensemble."""

    def __init__(self, cfg: WorldModelConfig | None = None) -> None:
        super().__init__()
        self.cfg = cfg or WorldModelConfig()
        c = self.cfg
        self.enc = nn.Linear(c.obs_dim, c.hidden)
        self.gru = nn.GRUCell(c.hidden + c.act_dim, c.hidden)
        self.post = _DynamicsHead(c.hidden, c.latent)
        self.prior = _DynamicsHead(c.hidden, c.latent)
        self.dec = nn.Linear(c.hidden + c.latent, c.obs_dim)
        self.rew = nn.Linear(c.hidden + c.latent, 1)
        self.disc = nn.Linear(c.hidden + c.latent, 1)
        self.ens = nn.ModuleList([nn.Linear(c.hidden + c.act_dim + c.latent, c.latent) for _ in range(c.ensemble)])
        self.opt = torch.optim.Adam(self.parameters(), lr=c.lr)
        self.train_steps = 0

    # -- core ----------------------------------------------------------
    def step(self, h: torch.Tensor, obs: torch.Tensor, act: torch.Tensor,
             sample: bool = True) -> dict[str, torch.Tensor]:
        e = torch.tanh(self.enc(obs))
        h2 = self.gru(torch.cat([e, act], -1), h)
        mu_q, lv_q = self.post(h2)
        mu_p, lv_p = self.prior(h2)
        std_q = (0.5 * lv_q).exp()
        z = mu_q + std_q * torch.randn_like(std_q) if sample else mu_q
        feat = torch.cat([h2, z], -1)
        out = {"h": h2, "z": z, "mu_q": mu_q, "lv_q": lv_q, "mu_p": mu_p, "lv_p": lv_p,
               "obs_hat": self.dec(feat), "rew_hat": self.rew(feat).squeeze(-1),
               "disc_hat": torch.sigmoid(self.disc(feat)).squeeze(-1)}
        # ensemble disagreement = epistemic uncertainty (exact variance)
        preds = torch.stack([m(torch.cat([h, act, z], -1)) for m in self.ens], 0)
        out["disagreement"] = preds.var(0).mean(-1).detach()
        out["ens_preds"] = preds
        return out

    def loss(self, obs: torch.Tensor, act: torch.Tensor, rew: torch.Tensor,
             next_obs: torch.Tensor) -> dict[str, torch.Tensor]:
        h = torch.zeros(obs.size(0), self.cfg.hidden)
        s = self.step(h, obs, act, sample=True)
        recon = ((s["obs_hat"] - next_obs) ** 2).mean()
        rloss = ((s["rew_hat"] - rew) ** 2).mean()
        kl = 0.5 * (s["lv_p"] - s["lv_q"] + (s["lv_q"].exp() + (s["mu_q"] - s["mu_p"]) ** 2) / (s["lv_p"].exp() + 1e-8) - 1).mean()
        ens = sum(((p - s["z"].detach()) ** 2).mean() for p in s["ens_preds"]) / len(self.ens)
        total = recon + rloss + 0.1 * kl + 0.5 * ens
        return {"total": total, "recon": recon.detach(), "reward": rloss.detach(),
                "kl": kl.detach(), "ensemble": ens.detach()}

    def train_step(self, obs: torch.Tensor, act: torch.Tensor,
                   rew: torch.Tensor, next_obs: torch.Tensor) -> dict[str, float]:
        self.opt.zero_grad()
        L = self.loss(obs, act, rew, next_obs)
        L["total"].backward()
        nn.utils.clip_grad_norm_(self.parameters(), 10.0)
        self.opt.step()
        self.train_steps += 1
        return {k: float(v.item()) for k, v in L.items()}

    @torch.no_grad()
    def imagine(self, h: torch.Tensor, z: torch.Tensor, policy: Any,
                horizon: int = 8) -> dict[str, torch.Tensor]:
        """Roll out latent trajectory with ``policy(h, z) -> act`` (prior path)."""
        B = h.size(0)
        zero_enc = torch.zeros(B, self.cfg.hidden)
        hs, zs, rews, discs, uncs = [], [], [], [], []
        for _ in range(horizon):
            a = policy(h, z)
            h = self.gru(torch.cat([zero_enc, a], -1), h)
            mu_p, _lv_p = self.prior(h)
            z = mu_p
            feat = torch.cat([h, z], -1)
            hs.append(h); zs.append(z)
            rews.append(self.rew(feat).squeeze(-1))
            discs.append(torch.sigmoid(self.disc(feat)).squeeze(-1))
            preds = torch.stack([m(torch.cat([h, a, z], -1)) for m in self.ens], 0)
            uncs.append(preds.var(0).mean(-1))
        return {"h": torch.stack(hs), "z": torch.stack(zs),
                "reward": torch.stack(rews), "discount": torch.stack(discs),
                "uncertainty": torch.stack(uncs)}

    def surprise(self, obs: torch.Tensor, act: torch.Tensor, next_obs: torch.Tensor) -> torch.Tensor:
        """Per-sample prediction surprise (detached MSE + KL)."""
        with torch.no_grad():
            h = torch.zeros(obs.size(0), self.cfg.hidden)
            s = self.step(h, obs, act, sample=False)
            return ((s["obs_hat"] - next_obs) ** 2).mean(-1) + 0.1 * s["disagreement"]
