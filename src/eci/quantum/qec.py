"""Quantum error correction: bit-flip [[3,1,3]] and Shor [[9,1,3]] codes.

Implementation notes
--------------------
* Encoding/decoding operate on batched statevectors via the simulator.
* Syndromes are extracted as stabilizer eigenvalues, which are exact (+-1)
  for Pauli errors on the encoded state.
* :meth:`ShorCode.run_trial` and :meth:`BitFlipCode.run_trial` demonstrate
  full encode -> error -> syndrome -> correct -> decode -> fidelity cycles.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

import torch

from eci.quantum import gates as qg
from eci.quantum.density import from_statevector, fidelity as rho_fidelity
from eci.quantum.gates import pauli_string_matrix
from eci.quantum.statevector import StatevectorSimulator

__all__ = ["BitFlipCode", "ShorCode"]


class BitFlipCode:
    """Three-qubit repetition code correcting a single X (bit-flip) error."""

    n_qubits = 3
    name = "[[3,1,3]] bit-flip"

    def __init__(self, sim: Optional[StatevectorSimulator] = None) -> None:
        self.sim = sim or StatevectorSimulator(self.n_qubits)

    def _embed_logical(self, logical: torch.Tensor) -> torch.Tensor:
        """|psi> (1 qubit) -> |psi>|0...0> on the full code register."""
        if logical.dim() == 1:
            logical = logical.unsqueeze(0)
        n_rest = self.n_qubits - 1
        rest = torch.zeros(1, 2 ** n_rest, dtype=logical.dtype, device=logical.device)
        rest[0, 0] = 1.0
        return torch.kron(logical[0], rest[0]).unsqueeze(0)

    # ------------------------------------------------------------------
    def encode(self, state: torch.Tensor) -> torch.Tensor:
        """|psi> = a|0> + b|1>  ->  a|000> + b|111>."""
        state = self.sim.apply_2q(state, qg.CNOT, 0, 1)
        state = self.sim.apply_2q(state, qg.CNOT, 0, 2)
        return state

    def decode(self, state: torch.Tensor) -> torch.Tensor:
        state = self.sim.apply_2q(state, qg.CNOT, 0, 2)
        state = self.sim.apply_2q(state, qg.CNOT, 0, 1)
        return state

    # ------------------------------------------------------------------
    def syndrome(self, state: torch.Tensor) -> torch.Tensor:
        """(batch, 2) stabilizer eigenvalues for Z0Z1 and Z1Z2 (+1 agree)."""
        s0 = self.sim.expectation_pauli(state, {0: "Z", 1: "Z"})
        s1 = self.sim.expectation_pauli(state, {1: "Z", 2: "Z"})
        return torch.stack([s0, s1], dim=1)

    @staticmethod
    def correction_qubit(syndrome: Sequence[float]) -> Optional[int]:
        """Map (Z0Z1, Z1Z2) eigenvalues to the erroneous qubit (None = clean)."""
        s0 = 1 if syndrome[0] > 0 else -1
        s1 = 1 if syndrome[1] > 0 else -1
        if s0 < 0 and s1 > 0:
            return 0
        if s0 < 0 and s1 < 0:
            return 1
        if s0 > 0 and s1 < 0:
            return 2
        return None

    def correct(self, state: torch.Tensor) -> Tuple[torch.Tensor, Optional[int]]:
        syn = self.syndrome(state)[0].tolist()
        qubit = self.correction_qubit(syn)
        if qubit is not None:
            state = self.sim.apply_1q(state, qg.X, qubit)
        return state, qubit

    # ------------------------------------------------------------------
    def run_trial(
        self,
        error_qubit: int = 1,
        error_gate: torch.Tensor = qg.X,
        alpha: float = math.cos(0.3),
        beta: float = math.sin(0.3),
    ) -> Dict[str, object]:
        """Encode a known state, corrupt one qubit, correct, verify."""
        prep = StatevectorSimulator(1)
        logical = alpha * prep.basis_state(0)[0] + beta * prep.basis_state(1)[0]
        logical = logical / torch.linalg.vector_norm(logical)
        state = self._embed_logical(logical)

        encoded = self.encode(state)
        corrupted = self.sim.apply_1q(encoded, error_gate, error_qubit)
        syn_before = self.syndrome(corrupted)[0].tolist()
        corrected, qubit_flag = self.correct(corrupted)
        decoded = self.decode(corrected)

        decoded_logical = decoded[0].reshape(2, -1)[:, 0]
        overlap = torch.abs(torch.einsum("i,i->", logical.conj(), decoded_logical)) ** 2
        return {
            "code": self.name,
            "error_qubit": error_qubit,
            "syndrome_before_correction": syn_before,
            "corrected_qubit": qubit_flag,
            "logical_fidelity": float(overlap.real.item()),
        }


class ShorCode(BitFlipCode):
    """Shor nine-qubit code [[9,1,3]] correcting any single-qubit error."""

    n_qubits = 9
    name = "[[9,1,3]] Shor"

    def __init__(self, sim: Optional[StatevectorSimulator] = None) -> None:
        self.sim = sim or StatevectorSimulator(self.n_qubits)

    # ------------------------------------------------------------------
    def encode(self, state: torch.Tensor) -> torch.Tensor:
        """Shor encoding: phase-cat on block heads, then bit-flip triplication.

        Circuit (time order):
        1. CNOT(0->1), CNOT(0->2)        : a|000> + b|111> on (0,1,2)
        2. H on (0,1,2)                  : a|+++> + b|--->
        3. SWAP(1,3), SWAP(2,6)          : phase cat now on heads (0,3,6)
        4. Triplicate each head into its block
        """
        state = self.sim.apply_2q(state, qg.CNOT, 0, 1)
        state = self.sim.apply_2q(state, qg.CNOT, 0, 2)
        for q in range(3):
            state = self.sim.apply_1q(state, qg.H, q)
        state = self.sim.apply_2q(state, qg.SWAP, 1, 3)
        state = self.sim.apply_2q(state, qg.SWAP, 2, 6)
        for block in range(3):
            base = 3 * block
            state = self.sim.apply_2q(state, qg.CNOT, base, base + 1)
            state = self.sim.apply_2q(state, qg.CNOT, base, base + 2)
        return state

    def decode(self, state: torch.Tensor) -> torch.Tensor:
        for block in reversed(range(3)):
            base = 3 * block
            state = self.sim.apply_2q(state, qg.CNOT, base, base + 2)
            state = self.sim.apply_2q(state, qg.CNOT, base, base + 1)
        state = self.sim.apply_2q(state, qg.SWAP, 2, 6)
        state = self.sim.apply_2q(state, qg.SWAP, 1, 3)
        for q in range(3):
            state = self.sim.apply_1q(state, qg.H, q)
        state = self.sim.apply_2q(state, qg.CNOT, 0, 2)
        state = self.sim.apply_2q(state, qg.CNOT, 0, 1)
        return state

    # ------------------------------------------------------------------
    # Stabilizers (as Pauli-string dicts) - eigenvalues are exact +-1 for
    # Pauli errors on the encoded state.
    # ------------------------------------------------------------------
    def z_stabilizers(self) -> List[Dict[int, str]]:
        """Bit-flip syndromes: Z_i Z_j within each block."""
        stabs = []
        for block in range(3):
            base = 3 * block
            stabs.append({base: "Z", base + 1: "Z"})
            stabs.append({base + 1: "Z", base + 2: "Z"})
        return stabs

    def x_stabilizers(self) -> List[Dict[int, str]]:
        """Phase-flip syndromes: XXXXXX comparisons across blocks."""
        b0, b1, b2 = (list(range(3 * k, 3 * k + 3)) for k in range(3))
        s01: Dict[int, str] = {}
        for q in b0 + b1:
            s01[q] = "X"
        s12: Dict[int, str] = {}
        for q in b1 + b2:
            s12[q] = "X"
        return [s01, s12]

    def syndrome(self, state: torch.Tensor) -> Tuple[List[float], List[float]]:
        z_syn = [float(self.sim.expectation_pauli(state, s)[0].item()) for s in self.z_stabilizers()]
        x_syn = [float(self.sim.expectation_pauli(state, s)[0].item()) for s in self.x_stabilizers()]
        return z_syn, x_syn

    @staticmethod
    def _bit_flip_qubit(z_syn: Sequence[float]) -> Optional[int]:
        """Locate the X error from the six Z-type eigenvalues."""
        signs = [1 if s > 0 else -1 for s in z_syn]
        for block in range(3):
            s0, s1 = signs[2 * block], signs[2 * block + 1]
            if s0 < 0 and s1 > 0:
                return 3 * block
            if s0 < 0 and s1 < 0:
                return 3 * block + 1
            if s0 > 0 and s1 < 0:
                return 3 * block + 2
        return None

    @staticmethod
    def _phase_block(x_syn: Sequence[float]) -> Optional[int]:
        """Locate the Z (phase) error block from X-type eigenvalues."""
        signs = [1 if s > 0 else -1 for s in x_syn]
        if signs[0] < 0 and signs[1] > 0:
            return 0
        if signs[0] < 0 and signs[1] < 0:
            return 1
        if signs[0] > 0 and signs[1] < 0:
            return 2
        return None

    def correct(self, state: torch.Tensor) -> Tuple[torch.Tensor, Dict[str, object]]:
        z_syn, x_syn = self.syndrome(state)
        flip_qubit = self._bit_flip_qubit(z_syn)
        phase_block = self._phase_block(x_syn)
        if flip_qubit is not None:
            state = self.sim.apply_1q(state, qg.X, flip_qubit)
        if phase_block is not None:
            state = self.sim.apply_1q(state, qg.Z, 3 * phase_block)
        info = {
            "bit_flip_qubit": flip_qubit,
            "phase_error_block": phase_block,
            "z_syndrome": z_syn,
            "x_syndrome": x_syn,
        }
        return state, info

    # ------------------------------------------------------------------
    def run_trial(
        self,
        error_qubit: int = 4,
        error_gate: str = "X",
        theta: float = 0.3,
    ) -> Dict[str, object]:
        """Full encode -> error -> correct -> decode -> fidelity cycle."""
        if error_gate not in ("X", "Y", "Z", "I"):
            raise ValueError("error_gate must be one of X, Y, Z, I")
        if not (0 <= error_qubit < self.n_qubits):
            raise ValueError("error_qubit out of range")

        prep = StatevectorSimulator(1)
        logical = math.cos(theta) * prep.basis_state(0)[0] + math.sin(theta) * prep.basis_state(1)[0]
        state = self._embed_logical(logical)

        encoded = self.encode(state)
        gate = {"X": qg.X, "Y": qg.Y, "Z": qg.Z, "I": qg.I}[error_gate]
        corrupted = self.sim.apply_1q(encoded, gate, error_qubit)
        corrected, info = self.correct(corrupted)
        decoded_full = self.decode(corrected)
        decoded_logical = decoded_full[0].reshape(2, -1)[:, 0]

        overlap = torch.abs(torch.einsum("i,i->", logical.conj(), decoded_logical)) ** 2
        return {
            "code": self.name,
            "error_gate": error_gate,
            "error_qubit": error_qubit,
            "correction_info": info,
            "logical_fidelity": float(overlap.real.item()),
        }
