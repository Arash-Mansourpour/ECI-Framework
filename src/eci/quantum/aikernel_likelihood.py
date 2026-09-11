"""Energy-target likelihood: embed ⟨H⟩-observation in Pauli-observable form.

Given Hamiltonian terms (coeffs c_k, Pauli labels O_k), aspiration energy
e_target, energy-noise R_e and slack eps, build (labels, o, R) with

    R^{-1} = (1/R_e)·c·cᵀ + eps·I,     o = (e_target / ||c||²)·c

so that cᵀo = e_target exactly and therefore, with m_k = Tr[rho O_k],

    ½(o−m)ᵀR⁻¹(o−m) = ½(e_target − ⟨H⟩)²/R_e + (eps/2)·||o − m||².

Identity is unit-tested (test_aikernel_phase2a). R is PD by construction
(rank-1 PSD + eps·I, eps > 0 required and enforced).
"""

from __future__ import annotations

import torch

from eci.quantum.hamiltonian import PauliSum

__all__ = ["term_label", "energy_likelihood"]


def term_label(paulis: dict, n_qubits: int) -> str:
    """{0:'Z',1:'Z'} on 2 qubits -> 'ZZ'; {1:'X'} -> 'IX' (big-endian)."""
    chars = ["I"] * n_qubits
    for q, p in paulis.items():
        chars[int(q)] = str(p).upper()
    return "".join(chars)


def energy_likelihood(hamiltonian: PauliSum, n_qubits: int, e_target: float,
                      R_e: float = 1.0, eps: float = 1e-3) -> tuple[list[str], torch.Tensor, torch.Tensor]:
    if eps <= 0:
        raise ValueError("eps must be > 0 (R must stay positive-definite)")
    labels = [term_label(t.paulis, n_qubits) for t in hamiltonian.terms]
    c = torch.tensor([float(t.coeff) for t in hamiltonian.terms], dtype=torch.float32)
    nrm2 = float((c @ c).item())
    if nrm2 == 0:
        raise ValueError("hamiltonian has zero norm")
    o = (e_target / nrm2) * c
    Rinv = torch.outer(c, c) / R_e + eps * torch.eye(len(c))
    R = torch.linalg.inv(Rinv)
    return labels, o, R
