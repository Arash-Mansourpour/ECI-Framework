"""Batched, differentiable statevector simulator.

Design notes
------------
* States have shape ``(batch, 2**n)``; qubit 0 is the most significant bit.
* Gates are applied with :func:`torch.einsum` on reshaped tensor views, so
  no ``2^n x 2^n`` operator is ever materialized and gradients flow through
  gate parameters (used by VQE/QAOA/QNN).
* The simulator is stateless: every method takes and returns a state, which
  keeps the API composable and thread-safe.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple, Union

import torch

from eci.constants import EPS
from eci.core.device import get_device
from eci.quantum import gates as qg

__all__ = ["StatevectorSimulator", "GateOp"]

#: A gate operation: ("1q", gate, qubit) | ("2q", gate, q0, q1) | ("c1q", gate, control, target)
GateOp = Union[Tuple[str, torch.Tensor, int], Tuple[str, torch.Tensor, int, int]]


class StatevectorSimulator:
    """Einstein-sum statevector simulator with autograd support."""

    def __init__(
        self,
        n_qubits: int,
        device: Optional[torch.device] = None,
        dtype: torch.dtype = torch.complex64,
    ) -> None:
        if n_qubits < 1:
            raise ValueError("n_qubits must be >= 1")
        self.n_qubits = n_qubits
        self.dim = 2 ** n_qubits
        self.device = device if device is not None else get_device()
        self.dtype = dtype

    # ------------------------------------------------------------------
    # State preparation
    # ------------------------------------------------------------------
    def zero_state(self, batch: int = 1) -> torch.Tensor:
        state = torch.zeros(batch, self.dim, dtype=self.dtype, device=self.device)
        state[:, 0] = 1.0
        return state

    def basis_state(self, index: int, batch: int = 1) -> torch.Tensor:
        if not (0 <= index < self.dim):
            raise ValueError(f"basis index {index} out of range [0, {self.dim})")
        state = torch.zeros(batch, self.dim, dtype=self.dtype, device=self.device)
        state[:, index] = 1.0
        return state

    def uniform_superposition(self, batch: int = 1) -> torch.Tensor:
        state = torch.ones(batch, self.dim, dtype=self.dtype, device=self.device)
        return state / math.sqrt(self.dim)

    def random_state(
        self,
        batch: int = 1,
        generator: Optional[torch.Generator] = None,
    ) -> torch.Tensor:
        real = torch.randn(batch, self.dim, generator=generator, device=self.device)
        imag = torch.randn(batch, self.dim, generator=generator, device=self.device)
        state = torch.complex(real, imag).to(self.dtype)
        return self.normalize(state)

    # ------------------------------------------------------------------
    # Gate application
    # ------------------------------------------------------------------
    def _tensor_view(self, state: torch.Tensor) -> torch.Tensor:
        batch = state.shape[0]
        return state.reshape(batch, *([2] * self.n_qubits))

    def _flatten(self, psi: torch.Tensor) -> torch.Tensor:
        return psi.reshape(psi.shape[0], self.dim)

    def apply_1q(self, state: torch.Tensor, gate: torch.Tensor, qubit: int) -> torch.Tensor:
        """Apply a 2x2 gate to ``qubit`` across the whole batch."""
        if gate.shape != (2, 2):
            raise ValueError(f"expected 2x2 gate, got {tuple(gate.shape)}")
        if not (0 <= qubit < self.n_qubits):
            raise ValueError(f"qubit {qubit} out of range [0, {self.n_qubits})")
        batch = state.shape[0]
        psi = self._tensor_view(state)
        psi = torch.movedim(psi, 1 + qubit, 1)
        psi = psi.reshape(batch, 2, -1)
        psi = torch.einsum("ij,bjk->bik", gate.to(state.dtype), psi)
        psi = psi.reshape(batch, *([2] * self.n_qubits))
        psi = torch.movedim(psi, 1, 1 + qubit)
        return self._flatten(psi)

    def apply_1q_per_sample(
        self,
        state: torch.Tensor,
        gates: torch.Tensor,
        qubit: int,
    ) -> torch.Tensor:
        """Apply a *different* 2x2 gate per batch element.

        ``gates`` has shape ``(batch, 2, 2)``; used for data encoding in
        quantum machine learning. Fully differentiable w.r.t. ``gates``.
        """
        if gates.shape[-2:] != (2, 2):
            raise ValueError(f"expected (batch, 2, 2) gates, got {tuple(gates.shape)}")
        batch = state.shape[0]
        psi = self._tensor_view(state)
        psi = torch.movedim(psi, 1 + qubit, 1)
        psi = psi.reshape(batch, 2, -1)
        psi = torch.einsum("bij,bjk->bik", gates.to(state.dtype), psi)
        psi = psi.reshape(batch, *([2] * self.n_qubits))
        psi = torch.movedim(psi, 1, 1 + qubit)
        return self._flatten(psi)

    def apply_2q(self, state: torch.Tensor, gate: torch.Tensor, q0: int, q1: int) -> torch.Tensor:
        """Apply a 4x4 gate to qubits ``(q0, q1)`` where q0 is the high bit.

        Implemented with an explicit permutation (and its inverse), which is
        correct for any ``q0 != q1`` regardless of ordering.
        """
        if gate.shape != (4, 4):
            raise ValueError(f"expected 4x4 gate, got {tuple(gate.shape)}")
        if q0 == q1:
            raise ValueError("q0 and q1 must differ")
        if not (0 <= q0 < self.n_qubits and 0 <= q1 < self.n_qubits):
            raise ValueError("qubit index out of range")
        batch = state.shape[0]
        psi = self._tensor_view(state)  # axes: [batch, qubit0..n-1]
        others = [q for q in range(self.n_qubits) if q not in (q0, q1)]
        perm = [0, 1 + q0, 1 + q1] + [1 + q for q in others]
        psi = psi.permute(*perm)
        psi = psi.reshape(batch, 4, -1)
        psi = torch.einsum("ij,bjk->bik", gate.to(state.dtype), psi)
        psi = psi.reshape(batch, *([2] * self.n_qubits))
        inverse = sorted(range(len(perm)), key=lambda i: perm[i])
        psi = psi.permute(*inverse)
        return self._flatten(psi)

    def apply_controlled(
        self,
        state: torch.Tensor,
        gate: torch.Tensor,
        control: int,
        target: int,
    ) -> torch.Tensor:
        """Apply ``gate`` on ``target`` conditioned on ``control`` being |1>."""
        gate_4x4 = qg.controlled(gate)
        return self.apply_2q(state, gate_4x4, control, target)

    def apply_ops(self, state: torch.Tensor, ops: Sequence[GateOp]) -> torch.Tensor:
        """Apply a sequence of gate ops."""
        for op in ops:
            kind = op[0]
            if kind == "1q":
                state = self.apply_1q(state, op[1], op[2])  # type: ignore[index]
            elif kind == "2q":
                state = self.apply_2q(state, op[1], op[2], op[3])  # type: ignore[index]
            elif kind == "c1q":
                state = self.apply_controlled(state, op[1], op[2], op[3])  # type: ignore[index]
            else:
                raise ValueError(f"unknown op kind: {kind}")
        return state

    # ------------------------------------------------------------------
    # Measurement & observables
    # ------------------------------------------------------------------
    def probabilities(self, state: torch.Tensor) -> torch.Tensor:
        """Outcome probabilities, shape ``(batch, 2**n)``."""
        probs = torch.abs(state) ** 2
        return probs / probs.sum(dim=1, keepdim=True).clamp_min(EPS)

    def sample(
        self,
        state: torch.Tensor,
        shots: int = 1024,
        generator: Optional[torch.Generator] = None,
    ) -> List[Dict[str, int]]:
        """Sample computational-basis shots; returns per-batch counts dict."""
        probs = self.probabilities(state).clamp_min(0)
        counts: List[Dict[str, int]] = []
        for b in range(state.shape[0]):
            idx = torch.multinomial(probs[b].cpu().float(), shots, replacement=True, generator=generator)
            c: Dict[str, int] = {}
            for i in idx.tolist():
                key = format(i, f"0{self.n_qubits}b")
                c[key] = c.get(key, 0) + 1
            counts.append(c)
        return counts

    def expectation_z(self, state: torch.Tensor, qubit: int) -> torch.Tensor:
        """<Z_qubit> per batch element, shape ``(batch,)``."""
        batch = state.shape[0]
        psi = self._tensor_view(state)
        psi = torch.movedim(psi, 1 + qubit, 1)
        probs = torch.abs(psi.reshape(batch, 2, -1)) ** 2
        sign = torch.tensor([1.0, -1.0], device=state.device, dtype=probs.dtype)
        return (probs * sign.view(1, 2, 1)).sum(dim=(1, 2))

    def _parity_signs(self, z_qubits: Sequence[int]) -> torch.Tensor:
        """Sign vector (+1/-1) over the computational basis for a Z-parity."""
        idx = torch.arange(self.dim, device=self.device)
        parity = torch.zeros(self.dim, dtype=torch.long, device=self.device)
        for q in z_qubits:
            parity = parity ^ ((idx >> (self.n_qubits - 1 - q)) & 1)
        return (1.0 - 2.0 * parity.float())

    def expectation_pauli(
        self,
        state: torch.Tensor,
        paulis: Dict[int, str],
    ) -> torch.Tensor:
        """Expectation of a Pauli string, e.g. ``{0: 'X', 1: 'Z'}``.

        X/Y observables are measured by basis rotation, Z-parities by a
        closed-form sign vector; the result is differentiable.
        """
        if not paulis:
            return torch.ones(state.shape[0], device=state.device)

        work = state
        # Rotate X and Y onto the Z axis (Y -> X via S^dag, X -> Z via H).
        for qubit, p in sorted(paulis.items()):
            p = p.upper()
            if p == "X":
                work = self.apply_1q(work, qg.H.to(state.dtype), qubit)
            elif p == "Y":
                work = self.apply_1q(work, qg.S.to(state.dtype).conj(), qubit)
                work = self.apply_1q(work, qg.H.to(state.dtype), qubit)
            elif p != "Z":
                raise ValueError(f"invalid Pauli label '{p}'")

        # After the rotation every qubit of the string is a Z observable.
        z_qubits = list(paulis.keys())
        probs = self.probabilities(work)
        sign = self._parity_signs(z_qubits).to(state.device)
        return (probs * sign.view(1, -1)).sum(dim=1)

    def expectation_matrix(self, state: torch.Tensor, observable: torch.Tensor) -> torch.Tensor:
        """<psi| O |psi> for a dense ``2^n x 2^n`` observable."""
        obs = observable.to(state.dtype).expand(state.shape[0], -1, -1)
        return torch.einsum("bi,bij,bj->b", state.conj(), obs, state).real

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    def norm(self, state: torch.Tensor) -> torch.Tensor:
        return torch.linalg.vector_norm(state, dim=1)

    def normalize(self, state: torch.Tensor) -> torch.Tensor:
        return state / self.norm(state).clamp_min(EPS).unsqueeze(1)

    def fidelity(self, state_a: torch.Tensor, state_b: torch.Tensor) -> torch.Tensor:
        """|<a|b>|^2 per batch element."""
        overlap = torch.einsum("bi,bi->b", state_a.conj(), state_b)
        return torch.abs(overlap) ** 2

    def entanglement_entropy(self, state: torch.Tensor, qubits_a: Sequence[int]) -> torch.Tensor:
        """Von Neumann entanglement entropy (bits) of the bipartition."""
        from eci.quantum.entanglement import schmidt_spectrum

        spectrum = schmidt_spectrum(state, self.n_qubits, list(qubits_a))
        p = spectrum.clamp_min(EPS)
        entropy = -(p * torch.log2(p)).sum(dim=1)
        return entropy

    def state_info(self, state: torch.Tensor) -> Dict[str, float]:
        """Diagnostic summary of a (single) state."""
        probs = self.probabilities(state[0])
        return {
            "norm": float(self.norm(state)[0].item()),
            "max_probability": float(probs.max().item()),
            "entropy_bits": float(
                (-(probs.clamp_min(EPS) * probs.clamp_min(EPS).log2()).sum()).item()
            ),
        }
