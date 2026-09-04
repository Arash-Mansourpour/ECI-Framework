"""Entanglement measures: Schmidt decomposition, concurrence, negativity.

References
----------
* Schmidt decomposition & entanglement entropy: Nielsen & Chuang, Ch. 2.5.
* Concurrence: Wootters (1998) PRL 80, 2245.
* Negativity: Vidal & Werner (2002) PRA 65, 032314.
"""

from __future__ import annotations

import math
from typing import Sequence, Tuple

import torch

from eci.constants import EPS
from eci.quantum.density import from_statevector

__all__ = [
    "schmidt_decomposition",
    "schmidt_spectrum",
    "entanglement_entropy",
    "concurrence",
    "entanglement_of_formation",
    "negativity",
    "partial_transpose",
    "bell_state",
]


def _tensor_view(state: torch.Tensor, n_qubits: int) -> torch.Tensor:
    return state.reshape(state.shape[0], *([2] * n_qubits))


def schmidt_decomposition(
    state: torch.Tensor,
    n_qubits: int,
    qubits_a: Sequence[int],
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Schmidt decomposition |psi> = sum_i s_i |u_i>_A |v_i>_B.

    Returns ``(u, s, vh)`` where ``u`` acts on subsystem A (rows = Schmidt
    modes, columns = A basis amplitudes) and ``vh`` on subsystem B.
    """
    if state.dim() == 1:
        state = state.unsqueeze(0)
    qubits_a = sorted(set(qubits_a))
    if not (0 < len(qubits_a) < n_qubits):
        raise ValueError("qubits_a must be a proper non-empty subset")
    qubits_b = [q for q in range(n_qubits) if q not in qubits_a]

    view = _tensor_view(state, n_qubits)
    order = [0] + [1 + q for q in qubits_a] + [1 + q for q in qubits_b]
    view = view.permute(*order)

    d_a = 2 ** len(qubits_a)
    d_b = 2 ** len(qubits_b)
    mat = view.reshape(state.shape[0], d_a, d_b)
    u, s, vh = torch.linalg.svd(mat, full_matrices=False)
    return u, s, vh


def schmidt_spectrum(state: torch.Tensor, n_qubits: int, qubits_a: Sequence[int]) -> torch.Tensor:
    """Squared Schmidt coefficients (a probability distribution)."""
    _, s, _ = schmidt_decomposition(state, n_qubits, qubits_a)
    return s ** 2


def entanglement_entropy(state: torch.Tensor, n_qubits: int, qubits_a: Sequence[int]) -> torch.Tensor:
    """Von Neumann entanglement entropy in bits, shape ``(batch,)``."""
    spec = schmidt_spectrum(state, n_qubits, qubits_a)
    p = spec.clamp_min(EPS)
    return -(p * torch.log2(p)).sum(dim=-1)


def concurrence(rho: torch.Tensor) -> torch.Tensor:
    """Wootters concurrence for a batch of two-qubit density matrices.

    C(rho) = max(0, lambda_1 - lambda_2 - lambda_3 - lambda_4) where the
    lambdas are the square roots of the eigenvalues of
    rho (sigma_y x sigma_y) rho* (sigma_y x sigma_y).
    """
    if rho.dim() == 2:
        rho = rho.unsqueeze(0)
    sy_sy = torch.kron(torch.tensor([[0.0, -1j], [1j, 0.0]], dtype=rho.dtype, device=rho.device),
                       torch.tensor([[0.0, -1j], [1j, 0.0]], dtype=rho.dtype, device=rho.device))
    rho_star = rho.conj()
    r_tilde = rho @ sy_sy @ rho_star @ sy_sy
    evals = torch.linalg.eigvalsh(r_tilde).clamp_min(0.0).sqrt()
    evals_sorted, _ = torch.sort(evals, dim=-1, descending=True)
    c = evals_sorted[..., 0] - evals_sorted[..., 1] - evals_sorted[..., 2] - evals_sorted[..., 3]
    return c.clamp_min(0.0)


def entanglement_of_formation(rho: torch.Tensor) -> torch.Tensor:
    """Entanglement of formation from the concurrence (bits)."""
    c = concurrence(rho).clamp(0.0, 1.0)
    x = (1.0 + 4.0 * c * (1.0 - c)).clamp(0.0, 1.0)
    h2 = -(0.5 * (1 + x.sqrt().clamp_max(1.0)) * torch.log2(0.5 * (1 + x.sqrt().clamp_max(1.0))) +
           0.5 * (1 - x.sqrt()) * torch.log2(0.5 * (1 - x.sqrt())).nan_to_num(0.0))
    return h2


def partial_transpose(rho: torch.Tensor, n_qubits: int, qubits: Sequence[int]) -> torch.Tensor:
    """Partial transpose over ``qubits`` of subsystem B (for negativity)."""
    if rho.dim() == 2:
        rho = rho.unsqueeze(0)
    dims = [2] * n_qubits
    view = rho.reshape(rho.shape[0], *dims, *dims)
    for q in qubits:
        view = view.transpose(1 + q, 1 + n_qubits + q)
    return view.reshape(rho.shape)


def negativity(rho: torch.Tensor, n_qubits: int, qubits_b: Sequence[int]) -> torch.Tensor:
    """Negativity N = (||rho^T_B||_1 - 1) / 2, shape ``(batch,)``."""
    rho_pt = partial_transpose(rho, n_qubits, qubits_b)
    evals = torch.linalg.eigvalsh(rho_pt).real
    return (torch.abs(evals).sum(dim=-1) - 1.0) / 2.0


def bell_state(
    kind: str = "phi+",
    device: torch.device | None = None,
    dtype: torch.dtype = torch.complex64,
) -> torch.Tensor:
    """One of the four maximally entangled two-qubit Bell states."""
    device = device or torch.device("cpu")
    s = torch.zeros(1, 4, dtype=dtype, device=device)
    table = {
        "phi+": (0, 3),
        "phi-": (0, 3),
        "psi+": (1, 2),
        "psi-": (1, 2),
    }
    if kind not in table:
        raise ValueError(f"unknown Bell state '{kind}'")
    i0, i1 = table[kind]
    s[0, i0] = 1.0 / math.sqrt(2)
    s[0, i1] = (1.0 if kind.endswith("+") else -1.0) / math.sqrt(2)
    return s
