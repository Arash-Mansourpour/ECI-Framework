"""Variational free energy: the single shared objective.

For Q(s) = N(mu, cov), prior P(s) = N(mu0, Sigma0), likelihood
o = A·s + N(0, R), the variational free energy has an exact closed form,
differentiable end-to-end by torch autograd:

    F = KL[Q(s) || P(s)]  +  E_Q[-log p(o|s)]      (complexity + inaccuracy)
      = 0.5·[tr(S0⁻¹S) + (mu-mu0)ᵀS0⁻¹(mu-mu0) - d + log|S0|/|S|]
      + 0.5·[(o-Amu)ᵀR⁻¹(o-Amu) + tr(AᵀR⁻¹A · S)]

Quantum branch (``quantum_free_energy``): same decomposition with
  complexity = Tr[rho (log rho - log rho_prior)]  (quantum relative entropy)
  inaccuracy = 0.5·(o-m)ᵀR⁻¹(o-m),  m_k = Tr[rho · O_k]
for a declared observable list {O_k}. Cross-checked against
``eci.quantum.density.relative_entropy`` in tests (agreement, not alias:
independent code paths, same math).

Lower F == better model. Every subsystem's loss must be an instance of,
or a documented additive contribution to, this F (Phase 2 adapters).
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence

import torch

from eci.aikernel.functors import pauli_string_matrix
from eci.aikernel.generative_model import GenerativeState, Likelihood, Prior

__all__ = ["free_energy", "free_energy_parts", "quantum_free_energy", "neg_log_evidence"]


def free_energy_parts(state: GenerativeState, obs: torch.Tensor,
                      likelihood: Likelihood, prior: Prior) -> Dict[str, torch.Tensor]:
    mu, S = state.mu, state.cov
    mu0, S0 = prior.mu0, prior.Sigma0
    A, R = likelihood.A, likelihood.R
    d = mu.size(0)
    S0inv = torch.linalg.inv(S0)
    Rinv = torch.linalg.inv(R)
    diff = mu - mu0
    complexity = 0.5 * (torch.trace(S0inv @ S) + diff @ S0inv @ diff
                        - d + torch.logdet(S0) - torch.logdet(S))
    resid = obs - A @ mu
    m = obs.size(0)
    # NOTE: the Gaussian normalizer 0.5·(log|R| + m·log2π) is load-bearing:
    # without it F is off by a constant and F = -log p(o) fails. Constants
    # matter because shares are compared ACROSS subsystems in the ledger.
    inaccuracy = 0.5 * (resid @ Rinv @ resid + torch.trace(A.T @ Rinv @ A @ S)
                        + torch.logdet(R) + m * math.log(2 * math.pi))
    return {"complexity": complexity, "inaccuracy": inaccuracy,
            "total": complexity + inaccuracy}


def free_energy(state: GenerativeState, obs: torch.Tensor,
                likelihood: Likelihood, prior: Prior) -> torch.Tensor:
    return free_energy_parts(state, obs, likelihood, prior)["total"]


def neg_log_evidence(obs: torch.Tensor, likelihood: Likelihood,
                     prior: Prior) -> torch.Tensor:
    """Exact -log p(o) for the linear-Gaussian model (F's lower bound target)."""
    A, R = likelihood.A, likelihood.R
    C = R + A @ prior.Sigma0 @ A.T
    resid = obs - A @ prior.mu0
    m = obs.size(0)
    return 0.5 * (resid @ torch.linalg.inv(C) @ resid + torch.logdet(C)
                  + m * torch.log(torch.tensor(2 * torch.pi)))


def quantum_free_energy(rho: torch.Tensor, observables: Sequence[str],
                        obs: Sequence[float] | torch.Tensor,
                        R: torch.Tensor,
                        rho_prior: Optional[torch.Tensor] = None) -> Dict[str, torch.Tensor]:
    """F over a density matrix. All ops autograd-safe (eigvalsh backward)."""
    import math as _math
    D = rho.size(0)
    n_qubits = int(round(_math.log2(D)))
    if 2 ** n_qubits != D:
        raise ValueError(f"rho dim {D} is not a power of 2")
    o = torch.as_tensor(obs, dtype=torch.float32).reshape(-1)
    mats = [pauli_string_matrix(lab, n_qubits).to(rho.dtype) for lab in observables]
    m = torch.stack([torch.trace(rho @ M).real for M in mats]).to(torch.float32)
    # von Neumann entropy via eigenvalues (clamped for log safety)
    vals = torch.linalg.eigvalsh(rho).real.clamp_min(1e-12)
    ent = -(vals * torch.log(vals)).sum()
    if rho_prior is None:
        rho_prior = torch.eye(D, dtype=rho.dtype) / D
    pv = torch.linalg.eigvalsh(rho_prior).real.clamp_min(1e-12)
    # cross entropy -Tr[rho log sigma]: log sigma is diagonal in sigma's
    # eigenbasis, so by cyclicity of the trace this is EXACT, no approximation:
    #   Tr[rho log sigma] = Tr[U' rho U diag(log w)] = sum_i (rho_eb)_ii log w_i
    w, U = torch.linalg.eigh(rho_prior)
    w = w.real.clamp_min(1e-12)
    rho_eb = (U.conj().T @ rho @ U)
    cross = -(rho_eb.diagonal().real.clamp_min(0.0) * torch.log(w)).sum()
    complexity = (-ent) - (-cross)  # == quantum relative entropy D(rho||sigma), exact
    Rinv = torch.linalg.inv(R)
    resid = o - m
    inaccuracy = 0.5 * (resid @ Rinv @ resid)
    return {"complexity": complexity, "inaccuracy": inaccuracy,
            "total": complexity + inaccuracy, "mean": m}
