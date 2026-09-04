"""Quantum gate library.

All gates are torch complex tensors. Single-qubit gates are 2x2, two-qubit
gates 4x4, and the multi-controlled helpers assemble arbitrary control
masks. Qubit 0 is the most significant bit (big-endian) everywhere in the
package: basis index ``i`` of an ``n``-qubit state encodes
``b_0 b_1 ... b_{n-1}``.
"""

from __future__ import annotations

import cmath
import math
from typing import Dict, List, Optional, Sequence, Tuple

import torch

__all__ = [
    "I", "X", "Y", "Z", "H", "S", "SDAG", "T", "TDAG",
    "RX", "RY", "RZ", "PHASE", "U3", "batched_RY",
    "CNOT", "CZ", "SWAP", "CRZ", "CRX", "CCX",
    "controlled", "pauli_string_matrix", "kron_list",
    "STANDARD_GATES",
]

_COMPLEX = torch.complex64


def _c(mat: List[List[complex]], dtype: torch.dtype = _COMPLEX) -> torch.Tensor:
    return torch.tensor(mat, dtype=dtype)


# ---------------------------------------------------------------------------
# Single-qubit gates
# ---------------------------------------------------------------------------

I = _c([[1, 0], [0, 1]])
X = _c([[0, 1], [1, 0]])
Y = _c([[0, -1j], [1j, 0]])
Z = _c([[1, 0], [0, -1]])
H = _c([[1, 1], [1, -1]]) / math.sqrt(2.0)
S = _c([[1, 0], [0, 1j]])
SDAG = S.conj().T.contiguous()
T = _c([[1, 0], [0, cmath.exp(1j * math.pi / 4)]])
TDAG = T.conj().T.contiguous()

STANDARD_GATES: Dict[str, torch.Tensor] = {
    "I": I, "X": X, "Y": Y, "Z": Z, "H": H,
    "S": S, "Sdag": SDAG, "T": T, "Tdag": TDAG,
}


def RX(theta: torch.Tensor | float, dtype: torch.dtype = _COMPLEX) -> torch.Tensor:
    """Rotation about the X axis: exp(-i theta X / 2)."""
    theta = torch.as_tensor(theta, dtype=torch.float64)
    cos = torch.cos(theta / 2).to(dtype)
    isin = (-1j * torch.sin(theta / 2)).to(dtype)
    top = torch.stack([cos, isin])
    bot = torch.stack([isin, cos])
    return torch.stack([top, bot])


def RY(theta: torch.Tensor | float, dtype: torch.dtype = _COMPLEX) -> torch.Tensor:
    """Rotation about the Y axis: exp(-i theta Y / 2)."""
    theta = torch.as_tensor(theta, dtype=torch.float64)
    cos = torch.cos(theta / 2).to(dtype)
    sin = torch.sin(theta / 2).to(dtype)
    top = torch.stack([cos, -sin])
    bot = torch.stack([sin, cos])
    return torch.stack([top, bot])


def RZ(theta: torch.Tensor | float, dtype: torch.dtype = _COMPLEX) -> torch.Tensor:
    """Rotation about the Z axis: exp(-i theta Z / 2)."""
    t = torch.as_tensor(theta, dtype=torch.float64)
    e_plus = torch.exp(-0.5j * t).to(dtype)
    e_minus = torch.exp(0.5j * t).to(dtype)
    zero = torch.zeros((), dtype=dtype)
    return torch.stack([torch.stack([e_plus.to(dtype), zero]),
                        torch.stack([zero, e_minus.to(dtype)])])


def PHASE(theta: torch.Tensor | float, dtype: torch.dtype = _COMPLEX) -> torch.Tensor:
    """Phase gate P(theta) = diag(1, e^{i theta})."""
    t = torch.as_tensor(theta, dtype=torch.float64)
    e = torch.exp(1j * t).to(dtype)
    zero = torch.zeros((), dtype=dtype)
    one = torch.ones((), dtype=dtype)
    return torch.stack([torch.stack([one, zero]),
                        torch.stack([zero, e])])


def U3(theta: float, phi: float, lam: float, dtype: torch.dtype = _COMPLEX) -> torch.Tensor:
    """Generic single-qubit unitary (IBM convention)."""
    c, s = math.cos(theta / 2), math.sin(theta / 2)
    return _c(
        [
            [c, -s * math.exp(1j * lam)],
            [s * math.exp(1j * phi), c * math.exp(1j * (phi + lam))],
        ],
        dtype=dtype,
    )


# ---------------------------------------------------------------------------
# Two-qubit gates
# ---------------------------------------------------------------------------

#: CNOT with qubit order (control, target).
CNOT = _c([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]])

#: Controlled-Z with qubit order (q0, q1).
CZ = _c([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, -1]])

#: SWAP with qubit order (q0, q1).
SWAP = _c(
    [
        [1, 0, 0, 0],
        [0, 0, 1, 0],
        [0, 1, 0, 0],
        [0, 0, 0, 1],
    ]
)


def CRZ(theta: float, dtype: torch.dtype = _COMPLEX) -> torch.Tensor:
    """Controlled-RZ with (control, target) ordering.

    diag(1, 1, e^{-iθ/2}, e^{+iθ/2}) = |0><0|⊗I + |1><1|⊗RZ(θ).
    """
    e_plus = cmath.exp(-0.5j * theta)
    e_minus = cmath.exp(0.5j * theta)
    return _c(
        [
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, e_plus, 0],
            [0, 0, 0, e_minus],
        ],
        dtype=dtype,
    )


def CRX(theta: float, dtype: torch.dtype = _COMPLEX) -> torch.Tensor:
    """Controlled-RX with (control, target) ordering."""
    c = math.cos(theta / 2)
    s = math.sin(theta / 2)
    return _c(
        [
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, c, -1j * s],
            [0, 0, -1j * s, c],
        ],
        dtype=dtype,
    )


#: Toffoli (CCX) with qubit order (control, control, target).
CCX = torch.zeros(8, 8, dtype=_COMPLEX)
CCX[0, 0] = 1
CCX[1, 1] = 1
CCX[2, 2] = 1
CCX[3, 3] = 1
CCX[4, 4] = 1
CCX[5, 5] = 1
CCX[6, 7] = 1
CCX[7, 6] = 1


def controlled(gate: torch.Tensor, n_controls: int = 1) -> torch.Tensor:
    """Promote a unitary to a controlled unitary acting on n_controls + k qubits."""
    dim = gate.shape[0]
    full = torch.eye(dim * (2 ** n_controls), dtype=gate.dtype, device=gate.device)
    full[-dim:, -dim:] = gate
    return full


def batched_RY(theta: torch.Tensor, dtype: torch.dtype = _COMPLEX) -> torch.Tensor:
    """Vectorized RY for a (batch,) angle tensor → (batch, 2, 2).

    Replaces the per-sample Python loop in QNN/VQE with one broadcast op.
    """
    t = torch.as_tensor(theta, dtype=torch.float64)
    cos = torch.cos(t / 2).to(dtype).unsqueeze(-1).unsqueeze(-1)
    sin = torch.sin(t / 2).to(dtype).unsqueeze(-1).unsqueeze(-1)
    zero = torch.zeros((), dtype=dtype).expand(t.shape)
    # Build [[c,-s],[s,c]] batched without Python loop.
    row0 = torch.cat([cos.expand(*t.shape, 1, 1), (-sin).expand(*t.shape, 1, 1)], dim=-1)
    row1 = torch.cat([sin.expand(*t.shape, 1, 1), cos.expand(*t.shape, 1, 1)], dim=-1)
    return torch.cat([row0, row1], dim=-2)


def kron_list(mats: Sequence[torch.Tensor]) -> torch.Tensor:
    """Tensor (Kronecker) product of an ordered sequence of matrices."""
    out = mats[0]
    for m in mats[1:]:
        out = torch.kron(out, m)
    return out


def pauli_string_matrix(
    paulis: Dict[int, str],
    n_qubits: int,
    dtype: torch.dtype = _COMPLEX,
    device: Optional[torch.device] = None,
) -> torch.Tensor:
    """Dense matrix of a Pauli string, e.g. ``{0: 'X', 2: 'Z'}``.

    Positions without an entry act as identity. Qubit 0 is the most
    significant factor in the Kronecker order (matching the statevector
    convention).
    """
    single: Dict[str, torch.Tensor] = {"I": I, "X": X, "Y": Y, "Z": Z}
    factors: List[torch.Tensor] = []
    for q in range(n_qubits):
        p = paulis.get(q, "I").upper()
        if p not in single:
            raise ValueError(f"invalid Pauli label '{p}' for qubit {q}")
        factors.append(single[p].to(device if device is not None else single[p].device))
    return kron_list(factors).to(dtype)
