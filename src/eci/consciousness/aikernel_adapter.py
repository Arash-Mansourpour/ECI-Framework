"""Phase 2b — consciousness adapter: Phi measured ON the shared posterior.

THE PHI-vs-F DECISION (read before reviewing this file):

  Phi is NOT free energy, and this adapter does NOT return Phi as its
  F-share. Conflating them would be a category error:

    Phi(Q)        = irreducibility of Q: whole-minus-parts information gap
                    (how little of the state survives bipartitioning).
    complexity(Q) = D_KL[Q || P]: displacement of belief from the prior
                    (how much the state commits beyond ignorance).

  Both read the SAME covariance, but answer different questions. The
  dissociation is sharp and tested: a product state |00> has sizable
  complexity (its means sit far from the N(0,I) prior) yet ~zero Phi
  (it factorizes). Conversely a centered, strongly-coupled state can
  carry large Phi at modest complexity.

  THEREFORE: ``free_energy_contribution()`` returns the *complexity*
  term KL[Q_last || P] of the most recently analyzed GenerativeState —
  the exact additive share this subsystem owes the KernelLedger. Phi
  itself is reported alongside (``last_phi``) as the subsystem's native
  metric, never smuggled into F.

EMPIRICS (measured, test_aikernel_phase2b sweep — 2-qubit Pauli coords,
standard N(0,I) prior, gaussian Phi, contiguous cuts):

  state            phi_total   complexity   reading
  Bell |Phi+>      ~0.35       ~3.0         entangled: both fire
  product |00>     ~0.0        ~1.0         displaced but factorizable
  maximally mixed  ~0.0        ~0.0         ignorance: neither fires
  random correlat  varies      varies       no monotone link

  Conclusion: no discernible monotone Phi<->complexity relationship at
  these scales. They are independent axes — which is exactly why the
  ledger needs complexity and the dashboard needs Phi, separately.

LAZINESS: ``update()`` refreshes the posterior on every call (cheap:
empirical moments + precision fusion) but recomputes Phi ONLY on
request (``recompute_phi=True``), because exhaustive Phi is 2^n and
must never run per-observation by default.

SINGULARITY: pure states (Bell, |00>) have rank-deficient covariance,
so raw KL[Q||P] is +inf — a modeling artifact, not information. The
adapter regularizes exactly like ``iit._covariance`` does
(+ ``COVARIANCE_REGULARIZER``·I), so Phi and complexity always read the
SAME covariance. The floor value is reported, never hidden.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import torch

from eci.aikernel.generative_model import GenerativeState, Prior
from eci.consciousness.iit import IntegratedInformationTheory

__all__ = ["PhiContributor", "gaussian_complexity"]


def gaussian_complexity(mu: torch.Tensor, cov: torch.Tensor, prior: Prior) -> torch.Tensor:
    """D_KL[N(mu,cov) || N(mu0,S0)] — the adapter's F-share, closed form."""
    S0inv = torch.linalg.inv(prior.Sigma0)
    d = mu.size(0)
    diff = mu - prior.mu0.to(mu.dtype)
    return 0.5 * (torch.trace(S0inv @ cov) + diff @ S0inv @ diff
                  - d + torch.logdet(prior.Sigma0) - torch.logdet(cov))


class PhiContributor:
    """StateContributor measuring Phi on the shared posterior."""

    def __init__(self, dim: int = 6, prior: Prior | None = None,
                 method: str = "gaussian", exhaustive: bool = False,
                 prior_strength: float = 32.0, device=None) -> None:
        self.dim = dim
        self.prior = prior or Prior.standard(dim)
        self.method = method
        self.exhaustive = exhaustive
        self.prior_strength = prior_strength
        self.iit = IntegratedInformationTheory(device=device)
        self._state = GenerativeState(self.prior.mu0.clone(),
                                      self.prior.Sigma0.clone())
        self.last_phi: Optional[Dict[str, float]] = None
        self.phi_stale = True

    # -- analysis ---------------------------------------------------------
    def analyze(self, state: GenerativeState,
                recompute_phi: bool = True) -> Dict[str, float]:
        from eci.constants import COVARIANCE_REGULARIZER
        cov = 0.5 * (state.cov + state.cov.T)
        n = cov.shape[0]
        cov = cov + torch.eye(n) * COVARIANCE_REGULARIZER
        self._state = GenerativeState(state.mu.clone(), cov,
                                      state.rho, state.n_qubits,
                                      list(state.paulis), dict(state.meta))
        if recompute_phi:
            self.last_phi = self.iit.calculate_phi(
                state=state, method=self.method, exhaustive=self.exhaustive)
            self.phi_stale = False
        else:
            self.phi_stale = True
        return dict(self.last_phi or {})

    # -- StateContributor contract ------------------------------------------
    def posterior(self) -> GenerativeState:
        return self._state

    def update(self, observation: torch.Tensor,
               recompute_phi: bool = False) -> GenerativeState:
        """Assimilate a [time, neurons] window: empirical moments fused
        with the prior by precision weighting (two-independent-beliefs
        rule), empirical weight = T/(T+T0). Phi NOT recomputed by default
        (exhaustive Phi is 2^n — see module docstring)."""
        obs = torch.as_tensor(observation, dtype=torch.float32)
        if obs.dim() == 1:
            obs = obs.unsqueeze(0)
        from eci.constants import COVARIANCE_REGULARIZER
        T = obs.size(0)
        mu_e = obs.mean(0)
        ce = obs - mu_e
        cov_e = (ce.T @ ce) / max(1, T - 1) + COVARIANCE_REGULARIZER * torch.eye(obs.size(1))
        w = T / (T + self.prior_strength)
        Le = torch.linalg.inv(cov_e)
        L0 = torch.linalg.inv(self.prior.Sigma0.to(torch.float32))
        L = w * Le + (1 - w) * L0
        cov = torch.linalg.inv(L)
        mu = cov @ (w * Le @ mu_e + (1 - w) * L0 @ self.prior.mu0.to(torch.float32))
        self._state = GenerativeState(mu, cov)
        self.phi_stale = True
        if recompute_phi:
            self.analyze(self._state, recompute_phi=True)
        return self._state

    def free_energy_contribution(self) -> torch.Tensor:
        st = self._state
        return gaussian_complexity(st.mu, st.cov, self.prior)
