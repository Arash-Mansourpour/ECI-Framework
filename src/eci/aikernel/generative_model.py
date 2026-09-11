"""Shared generative state: ONE posterior type for every subsystem.

A ``GenerativeState`` is the common currency of the unification layer:
Q(s) over a latent space ``s``, in one of two documented representations:

Gaussian branch   Q(s) = N(mu, cov),  s in R^d.
Quantum branch    Q ~ rho, a density matrix on n qubits (dim = 2^n).

THE MAPPING (this mapping IS the integration):
  The quantum branch converts to Gaussian coordinates via the *quantum
  covariance matrix* (the exact object used in quantum metrology / spin
  squeezing). For Pauli-string observables {P_k} (normalized so that
  Tr[P_k P_l] = D·delta_kl with D = 2^n):

      mu_k       = Tr[rho · P_k]
      Sigma_kl   = (1/2)·Tr[rho · {P_k, P_l}] - mu_k · mu_l

  where {·,·} is the anticommutator. Sigma is real symmetric PSD by
  construction (it is the covariance of a quasi-probability-free
  observable vector). See ``functors.density_to_cov`` for the executable
  version and its tests. Direction Gaussian -> quantum is intentionally
  ONE-WAY documented as lossy (a Gaussian fixes only first two moments;
  infinitely many rho share them) — the kernel never silently inverts it.

The observation (likelihood) model is linear-Gaussian and shared:
  o = A·s + eta,  eta ~ N(0, R).  See ``Likelihood``.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import torch

__all__ = ["Likelihood", "Prior", "GenerativeState"]


@dataclass
class Likelihood:
    """Shared observation model o = A s + N(0, R)."""

    A: torch.Tensor   # (m, d)
    R: torch.Tensor   # (m, m) PD

    def __post_init__(self) -> None:
        if self.A.dim() != 2 or self.R.dim() != 2:
            raise ValueError("A must be (m,d), R must be (m,m)")
        if self.A.size(0) != self.R.size(0):
            raise ValueError("A rows must match R dim")

    @property
    def obs_dim(self) -> int:
        return self.A.size(0)

    @property
    def latent_dim(self) -> int:
        return self.A.size(1)


@dataclass
class Prior:
    """Shared prior P(s) = N(mu0, Sigma0)."""

    mu0: torch.Tensor  # (d,)
    Sigma0: torch.Tensor  # (d, d) PD

    @classmethod
    def standard(cls, d: int) -> Prior:
        return cls(torch.zeros(d), torch.eye(d))


@dataclass
class GenerativeState:
    """Q(s): Gaussian branch + optional quantum branch (same belief)."""

    mu: torch.Tensor              # (d,) posterior mean
    cov: torch.Tensor             # (d, d) posterior covariance, PD
    rho: torch.Tensor | None = None   # (D, D) density matrix, if quantum-backed
    n_qubits: int = 0
    paulis: list[str] = field(default_factory=list)  # observable labels for mu/cov coords
    meta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.mu.dim() != 1 or self.cov.dim() != 2:
            raise ValueError("mu must be (d,), cov must be (d,d)")
        if self.cov.size(0) != self.cov.size(1) or self.cov.size(0) != self.mu.size(0):
            raise ValueError("cov must be (d,d) matching mu")
        if self.rho is not None and self.n_qubits <= 0:
            raise ValueError("quantum-backed state needs n_qubits > 0")

    @property
    def dim(self) -> int:
        return self.mu.size(0)

    @classmethod
    def gaussian(cls, mu: Sequence[float] | torch.Tensor,
                 cov: Sequence[Sequence[float]] | torch.Tensor,
                 paulis: list[str] | None = None) -> GenerativeState:
        mu_t = torch.as_tensor(mu, dtype=torch.float32)
        cov_t = torch.as_tensor(cov, dtype=torch.float32)
        return cls(mu_t, cov_t, paulis=list(paulis or []))

    @classmethod
    def from_density(cls, rho: torch.Tensor, n_qubits: int,
                     paulis: list[str] | None = None) -> GenerativeState:
        """Quantum-backed state; Gaussian coords via the metrology mapping."""
        from eci.aikernel.functors import density_to_cov
        labels = list(paulis or ["X", "Y", "Z"][: 3 if n_qubits == 1 else 0])
        if not labels:
            from eci.aikernel.functors import default_paulis
            labels = default_paulis(n_qubits)
        mu, cov = density_to_cov(rho, n_qubits, labels)
        return cls(mu.detach(), cov.detach(), rho.detach().clone(),
                   n_qubits, labels)

    def precision(self) -> torch.Tensor:
        return torch.linalg.inv(self.cov)

    def to_dict(self) -> dict[str, Any]:
        """Wire format (Phase 5): JSON-safe, round-trippable via from_dict.

        The density matrix serializes as row-major ``rho_real``/``rho_imag``
        nested float lists (None when Gaussian-only). Cost is O(4^n)
        floats — exact and fine for the small-n states this interface
        carries; large registers should travel as Gaussian coords only
        (pass ``include_rho=False``).
        """
        return self.to_dict_with_rho(include_rho=True)

    def to_dict_with_rho(self, include_rho: bool = True) -> dict[str, Any]:
        d: dict[str, Any] = {"dim": self.dim, "mu": self.mu.tolist(),
                             "cov": self.cov.tolist(), "n_qubits": self.n_qubits,
                             "paulis": self.paulis, "meta": self.meta,
                             "rho_real": None, "rho_imag": None}
        if include_rho and self.rho is not None:
            d["rho_real"] = self.rho.real.tolist()
            d["rho_imag"] = self.rho.imag.tolist()
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> GenerativeState:
        """Inverse of to_dict (accepts dicts that predate rho_* keys too)."""
        mu = torch.as_tensor(d["mu"], dtype=torch.float32)
        cov = torch.as_tensor(d["cov"], dtype=torch.float32)
        rho = None
        n_qubits = int(d.get("n_qubits", 0))
        if d.get("rho_real") is not None and d.get("rho_imag") is not None:
            real = torch.as_tensor(d["rho_real"], dtype=torch.float32)
            imag = torch.as_tensor(d["rho_imag"], dtype=torch.float32)
            if real.shape != imag.shape:
                raise ValueError("rho_real/rho_imag shape mismatch")
            rho = torch.complex(real, imag)
            if rho.dim() != 2 or rho.size(0) != rho.size(1):
                raise ValueError("rho must be a square matrix")
            if n_qubits and rho.size(0) != 2 ** n_qubits:
                raise ValueError("rho dim does not match n_qubits")
        return cls(mu, cov, rho, n_qubits,
                   list(d.get("paulis", [])), dict(d.get("meta", {})))
