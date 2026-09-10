"""Phase 6 — cognition adapters: imagination and science as contributors.

Two framings, one subsystem (cognition/), each with its honest mapping:

WORLD MODEL (LatentWorldModel -> WorldModelContributor). Good fit: the
model ALREADY maintains a posterior Gaussian (mu_q, lv_q) over its latent
and minimizes a VFE-shaped loss. posterior() returns that Gaussian
(N(mu_q, diag(exp(lv_q))), refreshed deterministically with sample=False).
update() takes one flat transition [obs | act | rew | next_obs] split by
config dims and runs exactly one train_step — the engine's own update.
free_energy_contribution() returns the engine's native loss total, whose
decomposition is reported alongside (recon + reward | 0.1*KL | 0.5*ens):
the 0.1/0.5 weights mean this share is a WEIGHTED-F variant, not the unit
KL of Phase 2a — stated here, asserted in tests via the parts dict, never
silently equated. Before any update the share is a forward-only loss on a
null transition (no optimizer step, no mutation).

SCIENTIST (Scientist/Hypothesis -> ScientistContributor). Good fit with
one encoding decision: each Hypothesis already holds an EXACT conjugate
Gaussian belief N(mean, 1/prec) over its headline effect, starting from
the implicit prior N(0,1) (prec=1.0, mean=0.0 at construction). The adapter
binds ONE hypothesis by name; posterior() is its Gaussian; update() takes
a flat [ys..., pred...] vector (split in half — xs provably unused by the
conjugate mean update, carried as zeros for API compat, documented not
hidden); free_energy_contribution() is the closed-form KL to N(0,1).
"""

from __future__ import annotations

import math
from typing import Any, Dict, List

import torch

from eci.aikernel.generative_model import GenerativeState
from eci.cognition.scientist import Scientist
from eci.cognition.world_model import LatentWorldModel, WorldModelConfig

__all__ = ["WorldModelContributor", "ScientistContributor"]


class WorldModelContributor:
    """StateContributor over the RSSM-lite imagination substrate."""

    def __init__(self, cfg: WorldModelConfig | None = None) -> None:
        self.model = LatentWorldModel(cfg or WorldModelConfig())
        self.cfg = self.model.cfg
        self._post: GenerativeState | None = None
        self._parts: Dict[str, float] = {}
        self._refresh_posterior()

    def _split(self, observation: torch.Tensor) -> Any:
        flat = torch.as_tensor(observation, dtype=torch.float32).reshape(-1)
        c = self.cfg
        expect = 2 * c.obs_dim + c.act_dim + 1
        if flat.numel() != expect:
            raise ValueError(f"transition needs {expect} values "
                             f"[obs({c.obs_dim})|act({c.act_dim})|rew(1)|next({c.obs_dim})], "
                             f"got {flat.numel()}")
        o = flat[:c.obs_dim].unsqueeze(0)
        a = flat[c.obs_dim:c.obs_dim + c.act_dim].unsqueeze(0)
        r = flat[c.obs_dim + c.act_dim:c.obs_dim + c.act_dim + 1]
        n = flat[c.obs_dim + c.act_dim + 1:].unsqueeze(0)
        return o, a, r, n

    def _refresh_posterior(self, o=None, a=None) -> None:
        c = self.cfg
        with torch.no_grad():
            h = torch.zeros(1, c.hidden)
            oo = torch.zeros(1, c.obs_dim) if o is None else o
            aa = torch.zeros(1, c.act_dim) if a is None else a
            s = self.model.step(h, oo, aa, sample=False)
            var = s["lv_q"].exp().squeeze(0)
            self._post = GenerativeState(s["mu_q"].squeeze(0).clone(), torch.diag(var))

    # -- StateContributor contract ------------------------------------------
    def posterior(self) -> GenerativeState:
        assert self._post is not None
        return self._post

    def update(self, observation: torch.Tensor) -> GenerativeState:
        o, a, r, n = self._split(observation)
        parts = self.model.train_step(o, a, r, n)
        self._parts = dict(parts)
        self._refresh_posterior(o, a)
        assert self._post is not None
        return self._post

    def free_energy_contribution(self) -> torch.Tensor:
        if not self._parts:
            o = torch.zeros(1, self.cfg.obs_dim)
            a = torch.zeros(1, self.cfg.act_dim)
            r = torch.zeros(1)
            L = self.model.loss(o, a, r, o)
            return L["total"]
        return torch.as_tensor(self._parts["total"], dtype=torch.float32)

    def last_parts(self) -> Dict[str, float]:
        return dict(self._parts)


class ScientistContributor:
    """StateContributor over one hypothesis' conjugate Gaussian belief."""

    def __init__(self, name: str, equation: str = "y = a*x + b", k: int = 2) -> None:
        self.scientist = Scientist()
        self.scientist.propose(name, equation, k)
        self.name = name

    def _hypo(self):
        return self.scientist.hypos[self.name]

    # -- StateContributor contract ------------------------------------------
    def posterior(self) -> GenerativeState:
        h = self._hypo()
        return GenerativeState(torch.tensor([h.mean]),
                               torch.tensor([[1.0 / h.prec]]))

    def update(self, observation: torch.Tensor) -> GenerativeState:
        flat = torch.as_tensor(observation, dtype=torch.float32).reshape(-1)
        if flat.numel() < 2 or flat.numel() % 2:
            raise ValueError("observation must be [ys..., pred...] with even length >= 2")
        k = flat.numel() // 2
        ys = flat[:k].tolist()
        pred = flat[k:].tolist()
        self.scientist.observe(self.name, [0.0] * k, ys, pred)
        return self.posterior()

    def free_energy_contribution(self) -> torch.Tensor:
        """Closed-form KL[N(mean,1/prec) || N(0,1)] (the engine's own prior)."""
        h = self._hypo()
        v = 1.0 / h.prec
        m = h.mean
        return torch.as_tensor(0.5 * (v + m * m - 1.0 + math.log(h.prec)),
                               dtype=torch.float32)
