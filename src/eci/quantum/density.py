"""Density-matrix calculus: purity, entropy, fidelity, partial trace.

Conventions
-----------
* ``rho`` tensors have shape ``(batch, D, D)`` and are Hermitian, PSD, unit-trace.
* Statevectors have shape ``(batch, D)``; qubit 0 is the most significant bit.
"""

from __future__ import annotations

import math
from typing import List, Sequence

import torch

from eci.constants import EPS

__all__ = [
    "from_statevector",
    "purity",
    "von_neumann_entropy",
    "fidelity",
    "trace_distance",
    "relative_entropy",
    "partial_trace",
    "sqrtm_psd",
    "logm_psd",
    "apply_kraus",
    "is_cptp",
]


def from_statevector(psi: torch.Tensor) -> torch.Tensor:
    """rho = |psi><psi| for a batch of statevectors."""
    if psi.dim() == 1:
        psi = psi.unsqueeze(0)
    return torch.einsum("bi,bj->bij", psi, psi.conj())


def sqrtm_psd(mat: torch.Tensor, tol: float = 1e-9) -> torch.Tensor:
    """Matrix square root of an Hermitian PSD matrix (batched over leading dim)."""
    evals, evecs = torch.linalg.eigh(mat)
    evals = evals.clamp_min(0.0).to(evecs.dtype)
    sqrt_evals = torch.diag_embed(evals.sqrt())
    conj = evecs.conj().transpose(-1, -2)
    return torch.einsum("bij,bjk,bkl->bil", evecs, sqrt_evals, conj)


def logm_psd(mat: torch.Tensor, tol: float = 1e-12) -> torch.Tensor:
    """Matrix logarithm of an Hermitian PSD matrix (batched)."""
    evals, evecs = torch.linalg.eigh(mat)
    evals = evals.clamp_min(tol).to(evecs.dtype)
    log_evals = torch.diag_embed(evals.log())
    conj = evecs.conj().transpose(-1, -2)
    return torch.einsum("bij,bjk,bkl->bil", evecs, log_evals, conj)


def purity(rho: torch.Tensor) -> torch.Tensor:
    """Tr(rho^2), shape ``(batch,)``."""
    return torch.einsum("bij,bji->b", rho, rho).real


def von_neumann_entropy(rho: torch.Tensor, base: float = 2.0) -> torch.Tensor:
    """S(rho) = -Tr(rho log rho), shape ``(batch,)``."""
    evals = torch.linalg.eigvalsh(rho).clamp_min(EPS)
    entropy = -(evals * torch.log(evals)).sum(dim=-1) / math.log(base)
    return entropy.real if torch.is_complex(entropy) else entropy


def fidelity(rho_a: torch.Tensor, rho_b: torch.Tensor) -> torch.Tensor:
    """Uhlmann fidelity F = [Tr sqrt(sqrt(rho_a) rho_b sqrt(rho_a))]^2."""
    sqrt_a = sqrtm_psd(rho_a)
    inner = sqrt_a @ rho_b @ sqrt_a
    evals = torch.linalg.eigvalsh(inner).clamp_min(0.0)
    return evals.sqrt().sum(dim=-1) ** 2


def trace_distance(rho_a: torch.Tensor, rho_b: torch.Tensor) -> torch.Tensor:
    """D(rho_a, rho_b) = 1/2 Tr |rho_a - rho_b|."""
    diff = rho_a - rho_b
    evals = torch.linalg.eigvalsh(diff)
    return 0.5 * torch.abs(evals).sum(dim=-1).real


def relative_entropy(rho: torch.Tensor, sigma: torch.Tensor) -> torch.Tensor:
    """S(rho || sigma) = Tr rho log rho - Tr rho log sigma (nats, batched).

    ``sigma`` is regularized for numerical invertibility.
    """
    d = sigma.shape[-1]
    reg = 1e-9 * torch.eye(d, dtype=sigma.dtype, device=sigma.device) / d
    log_rho = logm_psd(rho)
    log_sigma = logm_psd(sigma + reg)
    return torch.einsum("bij,bji->b", rho, log_rho - log_sigma).real


def partial_trace(
    rho: torch.Tensor,
    n_qubits: int,
    keep: Sequence[int],
) -> torch.Tensor:
    """Partial trace over all qubits except ``keep``.

    Accepts a statevector ``(batch, D)`` or a density matrix
    ``(batch, D, D)``. Output axes follow the sorted ``keep`` order
    (big-endian, qubit 0 most significant).
    """
    keep = sorted(set(keep))
    if rho.dim() == 2:  # statevector -> density matrix
        rho = from_statevector(rho)
    if not keep:
        return torch.ones(rho.shape[0], 1, 1, dtype=rho.dtype, device=rho.device)
    if len(keep) == n_qubits:
        return rho

    dims = [2] * n_qubits
    trace_out = [q for q in range(n_qubits) if q not in keep]

    # axes: 0 batch, 1..n bra qubits, n+1..2n ket qubits
    view = rho.reshape(rho.shape[0], *dims, *dims)
    order = [0]
    order += [1 + q for q in keep]
    order += [1 + n_qubits + q for q in keep]
    for q in trace_out:  # interleave bra/ket of each traced qubit
        order += [1 + q, 1 + n_qubits + q]

    view = view.permute(*order)
    d_keep = 2 ** len(keep)
    d_trace = 2 ** len(trace_out)
    m = view.reshape(rho.shape[0], d_keep, d_keep, d_trace, d_trace)
    return m.diagonal(dim1=-2, dim2=-1).sum(dim=-1)


def apply_kraus(rho: torch.Tensor, kraus_ops: Sequence[torch.Tensor]) -> torch.Tensor:
    """Apply a Kraus map: rho -> sum_i K_i rho K_i^dagger."""
    out = torch.zeros_like(rho)
    for k in kraus_ops:
        k = k.to(rho.dtype)
        out = out + k @ rho @ k.conj().T
    return out


def is_cptp(kraus_ops: Sequence[torch.Tensor], tol: float = 1e-5) -> bool:
    """Check the completeness relation: sum_i K_i^dagger K_i == I."""
    d = kraus_ops[0].shape[0]
    acc = torch.zeros(d, d, dtype=kraus_ops[0].dtype, device=kraus_ops[0].device)
    for k in kraus_ops:
        acc = acc + k.conj().T @ k
    return bool(torch.allclose(acc, torch.eye(d, dtype=acc.dtype, device=acc.device), atol=tol))
