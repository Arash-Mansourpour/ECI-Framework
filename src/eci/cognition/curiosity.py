"""Intrinsic motivation: curiosity as principled information appetite.

Three exact signals, one running-normalized combination:
- ``novelty`` (RND-lite): error of a distilled predictor against a frozen
  random target net — high on unseen states, decays with visits.
- ``disagreement``: world-model ensemble variance (epistemic uncertainty).
- ``surprise``: one-step prediction error (aleatoric + epistemic mix).

``bonus = w_nov*novelty + w_dis*disagreement + w_sur*surprise`` with
Welford running stats so the scale is self-calibrating across tasks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence

import torch
import torch.nn as nn

__all__ = ["CuriosityConfig", "IntrinsicMotivation"]


@dataclass
class CuriosityConfig:
    obs_dim: int = 16
    hidden: int = 64
    w_novelty: float = 1.0
    w_disagreement: float = 1.0
    w_surprise: float = 0.5
    lr: float = 3e-3


class _Net(nn.Module):
    def __init__(self, d: int, h: int) -> None:
        super().__init__()
        self.net = nn.Sequential(nn.Linear(d, h), nn.Tanh(), nn.Linear(h, h))
        for p in self.parameters():
            p.requires_grad = False

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class IntrinsicMotivation(nn.Module):
    def __init__(self, cfg: CuriosityConfig | None = None) -> None:
        super().__init__()
        self.cfg = cfg or CuriosityConfig()
        c = self.cfg
        self.target = _Net(c.obs_dim, c.hidden)
        self.predictor = nn.Sequential(nn.Linear(c.obs_dim, c.hidden), nn.Tanh(),
                                       nn.Linear(c.hidden, c.hidden))
        self.opt = torch.optim.Adam(self.predictor.parameters(), lr=c.lr)
        self.register_buffer("_mean", torch.zeros(1))
        self.register_buffer("_m2", torch.ones(1))
        self.register_buffer("_n", torch.tensor(1.0))
        self.visits = 0

    @torch.no_grad()
    def novelty(self, obs: torch.Tensor) -> torch.Tensor:
        err = ((self.predictor(obs) - self.target(obs)) ** 2).mean(-1)
        return err

    def learn(self, obs: torch.Tensor) -> float:
        loss = ((self.predictor(obs) - self.target(obs).detach()) ** 2).mean()
        self.opt.zero_grad()
        loss.backward()
        self.opt.step()
        self.visits += obs.size(0)
        return float(loss.item())

    def bonus(self, obs: torch.Tensor, disagreement: torch.Tensor | None = None,
              surprise: torch.Tensor | None = None) -> Dict[str, torch.Tensor]:
        c = self.cfg
        nov = self.novelty(obs).detach()
        dis = disagreement.detach() if disagreement is not None else torch.zeros_like(nov)
        sur = surprise.detach() if surprise is not None else torch.zeros_like(nov)
        raw = c.w_novelty * nov + c.w_disagreement * dis + c.w_surprise * sur
        with torch.no_grad():  # Welford update on batch mean
            b = raw.mean()
            self._n += 1
            d = b - self._mean
            self._mean += d / self._n
            self._m2 += d * (b - self._mean)
            std = (self._m2 / self._n).sqrt().clamp_min(1e-4)
        return {"bonus": raw / std, "novelty": nov, "disagreement": dis,
                "surprise": sur, "scale": std.detach()}
