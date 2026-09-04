"""Quantum noise channels in Kraus representation.

Every factory returns a list of Kraus operators satisfying the
completeness relation sum_i K_i^dagger K_i = I (verified by
:meth:`eci.quantum.density.is_cptp`).
"""

from __future__ import annotations

import math
from typing import Callable, Dict, List, Sequence

import torch

from eci.quantum import density as qd
from eci.quantum import gates as qg

__all__ = [
    "depolarizing",
    "bit_flip",
    "phase_flip",
    "amplitude_damping",
    "phase_damping",
    "bit_phase_flip",
    "CHANNEL_FACTORIES",
    "apply_channel_on_qubit",
    "NoiseModel",
]


def depolarizing(p: float, dtype: torch.dtype = torch.complex64) -> List[torch.Tensor]:
    """Single-qubit depolarizing channel: rho -> (1-p) rho + p I/2."""
    sqrt_p = math.sqrt(p)
    sqrt_1mp = math.sqrt(max(0.0, 1.0 - p))
    return [
        sqrt_1mp * qg.I.to(dtype),
        (sqrt_p / math.sqrt(3)) * qg.X.to(dtype),
        (sqrt_p / math.sqrt(3)) * qg.Y.to(dtype),
        (sqrt_p / math.sqrt(3)) * qg.Z.to(dtype),
    ]


def bit_flip(p: float, dtype: torch.dtype = torch.complex64) -> List[torch.Tensor]:
    """Bit-flip channel with Kraus operators sqrt(1-p) I, sqrt(p) X."""
    return [
        math.sqrt(1 - p) * qg.I.to(dtype),
        math.sqrt(p) * qg.X.to(dtype),
    ]


def phase_flip(p: float, dtype: torch.dtype = torch.complex64) -> List[torch.Tensor]:
    """Phase-flip (dephasing) channel with sqrt(1-p) I, sqrt(p) Z."""
    return [
        math.sqrt(1 - p) * qg.I.to(dtype),
        math.sqrt(p) * qg.Z.to(dtype),
    ]


def bit_phase_flip(p: float, dtype: torch.dtype = torch.complex64) -> List[torch.Tensor]:
    """Bit-phase-flip channel with sqrt(1-p) I, sqrt(p) Y."""
    return [
        math.sqrt(1 - p) * qg.I.to(dtype),
        math.sqrt(p) * qg.Y.to(dtype),
    ]


def amplitude_damping(gamma: float, dtype: torch.dtype = torch.complex64) -> List[torch.Tensor]:
    """Amplitude damping (T1 decay) with relaxation probability gamma."""
    k0 = torch.tensor([[1.0, 0.0], [0.0, math.sqrt(1 - gamma)]], dtype=dtype)
    k1 = torch.tensor([[0.0, math.sqrt(gamma)], [0.0, 0.0]], dtype=dtype)
    return [k0, k1]


def phase_damping(gamma: float, dtype: torch.dtype = torch.complex64) -> List[torch.Tensor]:
    """Phase damping (T2 decay without energy loss)."""
    a = math.sqrt(1 - gamma)
    k0 = torch.tensor([[1.0, 0.0], [0.0, a]], dtype=dtype)
    k1 = torch.tensor([[0.0, 0.0], [0.0, math.sqrt(gamma)]], dtype=dtype)
    k2 = torch.tensor([[a, 0.0], [0.0, 0.0]], dtype=dtype)
    return [k0, k1, k2]


CHANNEL_FACTORIES: Dict[str, Callable[..., List[torch.Tensor]]] = {
    "depolarizing": depolarizing,
    "bit_flip": bit_flip,
    "phase_flip": phase_flip,
    "bit_phase_flip": bit_phase_flip,
    "amplitude_damping": amplitude_damping,
    "phase_damping": phase_damping,
}


def _embed_single_qubit(
    kraus_ops: Sequence[torch.Tensor],
    n_qubits: int,
    qubit: int,
    dtype: torch.dtype,
) -> List[torch.Tensor]:
    """Embed 1-qubit Kraus operators into the full n-qubit Hilbert space."""
    eye = qg.I.to(dtype)
    embedded: List[torch.Tensor] = []
    for k in kraus_ops:
        k = k.to(dtype)
        factors = [k if q == qubit else eye for q in range(n_qubits)]
        embedded.append(qg.kron_list(factors))
    return embedded


def apply_channel_on_qubit(
    rho: torch.Tensor,
    n_qubits: int,
    qubit: int,
    kraus_ops: Sequence[torch.Tensor],
) -> torch.Tensor:
    """Apply a single-qubit Kraus channel to ``qubit`` of an n-qubit state.

    ``rho`` may be a statevector (converted to density matrix) or a density
    matrix. Returns a density matrix.
    """
    if rho.dim() == 2:  # statevector
        rho = qd.from_statevector(rho)
    dtype = rho.dtype
    embedded = _embed_single_qubit(kraus_ops, n_qubits, qubit, dtype)
    return qd.apply_kraus(rho, embedded)


class NoiseModel:
    """Configurable per-qubit noise model for simulation experiments."""

    def __init__(self, default_channel: str = "depolarizing", default_param: float = 0.01) -> None:
        if default_channel not in CHANNEL_FACTORIES:
            raise ValueError(f"unknown channel '{default_channel}'")
        self.default_channel = default_channel
        self.default_param = default_param
        self._per_qubit: Dict[int, List[str]] = {}

    def set_qubit_noise(self, qubit: int, channel: str, param: float) -> None:
        if channel not in CHANNEL_FACTORIES:
            raise ValueError(f"unknown channel '{channel}'")
        self._per_qubit[qubit] = [channel, str(param)]

    def apply(self, rho: torch.Tensor, n_qubits: int) -> torch.Tensor:
        """Apply the configured noise to every qubit of ``rho``."""
        if rho.dim() == 2:
            rho = qd.from_statevector(rho)
        for q in range(n_qubits):
            channel, param = self._per_qubit.get(q, [self.default_channel, str(self.default_param)])
            kraus = CHANNEL_FACTORIES[channel](float(param), rho.dtype)
            rho = apply_channel_on_qubit(rho, n_qubits, q, kraus)
        return rho
