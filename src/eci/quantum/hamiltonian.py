"""Pauli-sum Hamiltonians and Trotter-Suzuki evolution.

A ``PauliTerm`` is (coeff, {qubit: 'X'|'Y'|'Z'}); a ``PauliSum`` is a sum
of terms. Evolution e^{-i H t} for H = sum_k c_k P_k is approximated with
first-order Trotterization:

    e^{-i H t} ~= prod_k e^{-i c_k P_k t / steps} ^ steps

and each e^{-i c P t} is implemented exactly via basis rotations + a
CNOT ladder + a parameterized RZ, which keeps everything differentiable.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

import torch

from eci.quantum import gates as qg
from eci.quantum.gates import kron_list
from eci.quantum.statevector import GateOp, StatevectorSimulator

__all__ = ["PauliTerm", "PauliSum"]

_PauliLabel = str


@dataclass
class PauliTerm:
    """Single Pauli term: coeff * prod_q P_q."""

    coeff: float
    paulis: Dict[int, _PauliLabel] = field(default_factory=dict)

    def normalized(self) -> "PauliTerm":
        return PauliTerm(float(self.coeff), {int(q): p.upper() for q, p in self.paulis.items()})


class PauliSum:
    """Sum of Pauli terms representing an Hermitian operator."""

    def __init__(self, terms: Sequence[PauliTerm] | None = None) -> None:
        self.terms: List[PauliTerm] = [t.normalized() for t in (terms or [])]

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------
    @classmethod
    def from_maxcut_edges(cls, edges: Sequence[Tuple[int, int]], n_qubits: int) -> "PauliSum":
        """MaxCut cost Hamiltonian C = sum_{(i,j)} (I - Z_i Z_j)/2."""
        terms = []
        for (i, j) in edges:
            if not (0 <= i < n_qubits and 0 <= j < n_qubits):
                raise ValueError(f"edge ({i},{j}) out of range for {n_qubits} qubits")
            if i == j:
                raise ValueError("self-loops are not allowed")
            terms.append(PauliTerm(-0.5, {i: "Z", j: "Z"}))  # constant I/2 dropped for QAOA phases
        return cls(terms)

    @classmethod
    def from_dict(cls, spec: Sequence[Tuple[float, Dict[int, str]]]) -> "PauliSum":
        return cls([PauliTerm(c, p) for c, p in spec])

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    @property
    def n_terms(self) -> int:
        return len(self.terms)

    def max_qubit(self) -> int:
        q = -1
        for term in self.terms:
            for qb in term.paulis:
                q = max(q, qb)
        return q

    # ------------------------------------------------------------------
    # Observables
    # ------------------------------------------------------------------
    def expectation(self, state: torch.Tensor, sim: StatevectorSimulator) -> torch.Tensor:
        """<H> per batch element via exact Pauli-string measurement."""
        total = torch.zeros(state.shape[0], dtype=torch.float64, device=state.device)
        for term in self.terms:
            if not term.paulis:
                total = total + term.coeff
                continue
            total = total + term.coeff * sim.expectation_pauli(state, term.paulis).double()
        return total

    def to_matrix(self, n_qubits: int, dtype: torch.dtype = torch.complex64) -> torch.Tensor:
        """Dense matrix (only for small n_qubits)."""
        single = {"I": qg.I, "X": qg.X, "Y": qg.Y, "Z": qg.Z}
        dim = 2 ** n_qubits
        out = torch.zeros(dim, dim, dtype=dtype)
        for term in self.terms:
            factors = []
            for q in range(n_qubits):
                p = term.paulis.get(q, "I")
                factors.append(single[p])
            out = out + term.coeff * kron_list(factors).to(dtype)
        return out

    # ------------------------------------------------------------------
    # Evolution
    # ------------------------------------------------------------------
    def _basis_change_ops(self, term: PauliTerm) -> Tuple[List[GateOp], List[GateOp]]:
        """Pre/post ops rotating X/Y onto the Z axis (verified identities)."""
        pre: List[GateOp] = []
        post: List[GateOp] = []
        for q, p in sorted(term.paulis.items()):
            if p == "X":
                pre.append(("1q", qg.H, q))
                post.append(("1q", qg.H, q))
            elif p == "Y":
                # e^{-i t Y} = S H e^{-i t Z} H S^dag
                pre.append(("1q", qg.S.conj(), q))
                pre.append(("1q", qg.H, q))
                post.append(("1q", qg.H, q))
                post.append(("1q", qg.S, q))
        return pre, post

    def _pauli_evolution_ops(self, term: PauliTerm, t: float | torch.Tensor) -> List[GateOp]:
        """Ops implementing e^{-i * coeff * P * t} exactly (circuit level)."""
        term = term.normalized()
        qubits = sorted(term.paulis)
        if not qubits:
            return []  # global phase only
        if len(qubits) == 1:
            pre, post = self._basis_change_ops(term)
            angle = 2.0 * term.coeff * t
            return pre + [("1q", qg.RZ(angle), qubits[0])] + post

        pre, post = self._basis_change_ops(term)
        ops: List[GateOp] = list(pre)
        # CNOT ladder: q0 -> q1 -> ... -> qm
        for a, b in zip(qubits[:-1], qubits[1:]):
            ops.append(("2q", qg.CNOT, a, b))
        angle = 2.0 * term.coeff * t
        ops.append(("1q", qg.RZ(angle), qubits[-1]))
        for a, b in reversed(list(zip(qubits[:-1], qubits[1:]))):
            ops.append(("2q", qg.CNOT, a, b))
        ops.extend(post)
        return ops

    def evolve(
        self,
        state: torch.Tensor,
        sim: StatevectorSimulator,
        t: float | torch.Tensor,
        trotter_steps: int = 1,
    ) -> torch.Tensor:
        """Apply e^{-i H t} via Trotterization; differentiable in ``t``."""
        if trotter_steps < 1:
            raise ValueError("trotter_steps must be >= 1")
        dt = t / trotter_steps
        for _ in range(trotter_steps):
            for term in self.terms:
                ops = self._pauli_evolution_ops(term, dt)
                state = sim.apply_ops(state, ops)
        return state
