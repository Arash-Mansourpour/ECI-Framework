"""Dirac operator algebra: Hilbert-space operators, commutators, spectral theory.

Formalism
---------
* Hilbert space H = C^d, operators L(H) with Hilbert-Schmidt inner product
  <A,B>_HS = Tr(A^dagger B).
* Pauli basis {I,X,Y,Z}^{⊗n} / sqrt(d) is an orthonormal basis of L(H).
* Every Hermitian H admits spectral decomposition H = Σ_k λ_k |k><k|,
  and unitary evolution U(t) = exp(-iHt) = Σ_k e^{-iλ_k t} |k><k|.
* Heisenberg: dA/dt = i[H,A] + ∂A/∂t.  Uncertainty: ΔA ΔB ≥ ½|<[A,B]>|.
"""

from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

import torch

from eci.constants import EPS
from eci.quantum import gates as qg

__all__ = [
    "hilbert_schmidt_inner",
    "operator_norm",
    "trace_norm",
    "commutator",
    "anticommutator",
    "spectral_decomposition",
    "matrix_exponential_hermitian",
    "unitary_evolution",
    "heisenberg_evolution",
    "uncertainty_bound",
    "pauli_decomposition",
    "pauli_reconstruction",
    "is_hermitian",
    "is_unitary",
    "is_positive",
    "operator_entropy",
    "fidelity_unitary",
]


def hilbert_schmidt_inner(A: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    """<A,B>_HS = Tr(A† B), batched over leading dim."""
    return torch.einsum("...ji,...jk->...", A.conj(), B)


def operator_norm(A: torch.Tensor) -> torch.Tensor:
    """Spectral norm ||A||_∞ = σ_max(A)."""
    s = torch.linalg.svdvals(A)
    return s[..., 0]


def trace_norm(A: torch.Tensor) -> torch.Tensor:
    """Trace norm ||A||_1 = Σ σ_i."""
    return torch.linalg.svdvals(A).sum(dim=-1)


def commutator(A: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    """[A,B] = AB - BA."""
    return A @ B - B @ A


def anticommutator(A: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    """{A,B} = AB + BA."""
    return A @ B + B @ A


def is_hermitian(A: torch.Tensor, tol: float = 1e-5) -> bool:
    return bool(torch.allclose(A, A.conj().transpose(-1, -2), atol=tol))


def is_unitary(U: torch.Tensor, tol: float = 1e-5) -> bool:
    d = U.shape[-1]
    eye = torch.eye(d, dtype=U.dtype, device=U.device).expand(U.shape)
    return bool(torch.allclose(U.conj().transpose(-1, -2) @ U, eye, atol=tol))


def is_positive(A: torch.Tensor, tol: float = 1e-6) -> bool:
    evals = torch.linalg.eigvalsh(A)
    return bool((evals.real >= -tol).all().item())


def spectral_decomposition(H: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
    """Eigendecomposition of Hermitian H -> (eigenvalues asc, eigenvectors).

    H = V diag(λ) V†.
    """
    evals, evecs = torch.linalg.eigh(H)
    return evals, evecs


def matrix_exponential_hermitian(H: torch.Tensor, t: float | torch.Tensor = 1.0) -> torch.Tensor:
    """exp(-i H t) via spectral theorem (exact, differentiable in t)."""
    evals, evecs = spectral_decomposition(H)
    phases = torch.exp(-1j * evals * t).to(evecs.dtype)
    D = torch.diag_embed(phases)
    Vd = evecs.conj().transpose(-1, -2)
    return evecs @ D @ Vd


def unitary_evolution(H: torch.Tensor, t: float, psi: torch.Tensor) -> torch.Tensor:
    """|ψ(t)> = e^{-iHt} |ψ(0)>."""
    U = matrix_exponential_hermitian(H, t)
    if psi.dim() == 1:
        return (U @ psi.unsqueeze(-1)).squeeze(-1)
    if psi.dim() == 2:
        return torch.einsum("ij,bj->bi", U, psi)
    return torch.einsum("...ij,...j->...i", U, psi)


def heisenberg_evolution(H: torch.Tensor, A0: torch.Tensor, t: float) -> torch.Tensor:
    """A(t) = e^{iHt} A0 e^{-iHt}."""
    U = matrix_exponential_hermitian(H, t)
    Ud = U.conj().transpose(-1, -2)
    return U @ A0 @ Ud


def uncertainty_bound(
    A: torch.Tensor, B: torch.Tensor, psi: torch.Tensor
) -> Dict[str, float]:
    """Robertson-Schrödinger bound: ΔA ΔB ≥ ½ |<[A,B]>|.

    Returns variances, commutator expectation and bound saturation.
    """
    if psi.dim() == 2:
        psi = psi[0]
    psi = psi / torch.linalg.vector_norm(psi).clamp_min(EPS)
    rho = torch.outer(psi, psi.conj())

    def _var(O: torch.Tensor) -> float:
        m1 = torch.trace(rho @ O).real.item()
        m2 = torch.trace(rho @ O @ O).real.item()
        return max(0.0, m2 - m1 ** 2)

    dA = _var(A)
    dB = _var(B)
    comm_exp = abs(torch.trace(rho @ commutator(A, B)).item())
    bound = 0.5 * comm_exp
    lhs = (dA ** 0.5) * (dB ** 0.5)
    return {
        "delta_A": dA ** 0.5,
        "delta_B": dB ** 0.5,
        "lhs": lhs,
        "rhs_bound": bound,
        "saturated_fraction": (bound / lhs) if lhs > EPS else 0.0,
    }


def pauli_decomposition(
    A: torch.Tensor, n_qubits: int
) -> Dict[Tuple[str, ...], complex]:
    """Expand operator A in the n-qubit Pauli basis: A = Σ_P c_P P.

    c_P = Tr(P A)/d.
    """
    labels = ["I", "X", "Y", "Z"]
    single = {"I": qg.I, "X": qg.X, "Y": qg.Y, "Z": qg.Z}
    d = 2 ** n_qubits
    out: Dict[Tuple[str, ...], complex] = {}
    # Recursive enumeration (n ≤ 6 tractable; larger uses sampling path elsewhere)
    def _rec(k: int, prefix: List[str], mat: torch.Tensor):
        if k == n_qubits:
            c = torch.trace(mat.conj().transpose(-1, -2) @ A.to(mat.dtype)) / d
            if abs(c.item()) > 1e-9:
                out[tuple(prefix)] = complex(c.item())
            return
        for lab in labels:
            _rec(k + 1, prefix + [lab], torch.kron(mat, single[lab]) if k > 0 else single[lab])
    _rec(0, [], torch.ones(1, 1, dtype=A.dtype))
    return out


def pauli_reconstruction(
    coeffs: Dict[Tuple[str, ...] | str, complex],
    n_qubits: int,
    dtype: torch.dtype = torch.complex64,
) -> torch.Tensor:
    """Reconstruct dense matrix from Pauli coefficients."""
    single = {"I": qg.I, "X": qg.X, "Y": qg.Y, "Z": qg.Z}
    d = 2 ** n_qubits
    out = torch.zeros(d, d, dtype=dtype)
    for key, c in coeffs.items():
        labs = list(key) if isinstance(key, str) else list(key)
        mats = [single[l] for l in labs]
        P = mats[0]
        for m in mats[1:]:
            P = torch.kron(P, m)
        out = out + complex(c) * P.to(dtype)
    return out


def operator_entropy(A: torch.Tensor, base: float = 2.0) -> torch.Tensor:
    """Von Neumann entropy of normalized A†A (operator entanglement proxy)."""
    import math as _math

    M = A.conj().transpose(-1, -2) @ A
    M = M / torch.trace(M).real.clamp_min(EPS)
    evals = torch.linalg.eigvalsh(M).clamp_min(EPS)
    ent = -(evals * torch.log(evals)).sum(dim=-1) / _math.log(base)
    return ent.real if torch.is_complex(ent) else ent


def fidelity_unitary(U: torch.Tensor, V: torch.Tensor) -> float:
    """Average gate fidelity proxy: |Tr(U†V)|/d."""
    d = U.shape[-1]
    return float((torch.abs(torch.trace(U.conj().transpose(-1, -2) @ V)) / d).real.item())
