"""Phase 8 — EWC adapter: weight-space posterior as contributor.

Framing (textbook Laplace reading, stated not smuggled): EWC's penalty
  L = (λ/2)·Σᵢ Fᵢ(θᵢ − θ*ᵢ)²
is, up to constants, the negative log of a Gaussian approximate
posterior Q(θ) = N(θ*, diag(1/(λF + ε₀))) — precision = Fisher scaled by
λ plus a prior precision floor ε₀ (keeps unobserved params proper;
without it their variance is infinite and the share is undefined).
posterior() returns that Gaussian flattened (dim = total params);
update(obs) adopts obs as the new MAP snapshot θ* (Fisher refresh needs
a data loader — see consolidate() — so update() is the parameter half,
documented, not hidden); free_energy_contribution() is the engine's OWN
ewc_loss() (the continual-learning share: it prices deviation from
consolidated knowledge; the task data-fit lives in the task loss, same
split as Phase 6's weighted-F reporting).
"""

from __future__ import annotations

import torch

from eci.aikernel.generative_model import GenerativeState
from eci.learning.continual import ElasticWeightConsolidation

__all__ = ["EWCContributor"]


class EWCContributor:
    """StateContributor over consolidated weight beliefs."""

    def __init__(self, ewc: ElasticWeightConsolidation,
                 prior_prec: float = 1.0) -> None:
        if prior_prec <= 0:
            raise ValueError("prior_prec must be > 0 (improper posterior otherwise)")
        self.ewc = ewc
        self.prior_prec = prior_prec

    def _flat(self, d: dict[str, torch.Tensor]) -> torch.Tensor:
        return torch.cat([d[k].reshape(-1).float()
                          for k, _ in self.ewc.model.named_parameters()])

    # -- StateContributor contract ------------------------------------------
    def posterior(self) -> GenerativeState:
        mu = self._flat(self.ewc.optpar_dict)
        fisher = self._flat(self.ewc.fisher_dict)
        var = 1.0 / (self.ewc.lambda_ewc * fisher + self.prior_prec)
        return GenerativeState(mu, torch.diag(var))

    def update(self, observation: torch.Tensor) -> GenerativeState:
        """Adopt a flattened parameter vector as the new snapshot θ*."""
        from eci.aikernel.state_contract import require_finite
        flat = torch.as_tensor(require_finite(observation, "ewc"), dtype=torch.float32).reshape(-1)
        expect = sum(p.numel() for _, p in self.ewc.model.named_parameters())
        if flat.numel() != expect:
            raise ValueError(f"observation needs {expect} values, got {flat.numel()}")
        offset = 0
        with torch.no_grad():
            for _, param in self.ewc.model.named_parameters():
                n = param.numel()
                param.copy_(flat[offset:offset + n].reshape(param.shape))
                offset += n
        self.ewc.update_optimal_params()
        return self.posterior()

    def consolidate(self, data_loader, max_batches=None) -> dict[str, float]:
        """Full EWC cycle half 2: (re)estimate Fisher on task data."""
        self.ewc.compute_fisher(data_loader, max_batches=max_batches)
        total = sum(float(v.sum().item()) for v in self.ewc.fisher_dict.values())
        return {"fisher_total": total}

    def free_energy_contribution(self) -> torch.Tensor:
        return self.ewc.ewc_loss().float()
