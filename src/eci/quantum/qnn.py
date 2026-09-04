"""Differentiable quantum neural networks.

``QuantumLayer`` encodes classical features as RY rotations (per-sample,
batched) and applies a variational hardware-efficient ansatz; the output is
the vector of <Z> expectations. ``QuantumNeuralNetwork`` wraps it with
classical pre/post processing layers, forming a full hybrid model.

All operations flow through the differentiable simulator, so gradients
propagate from the classical loss back into the rotation parameters.
"""

from __future__ import annotations

import math
from typing import Optional

import torch
import torch.nn as nn

from eci.core.device import get_device
from eci.quantum import gates as qg
from eci.quantum.statevector import StatevectorSimulator

__all__ = ["QuantumLayer", "QuantumNeuralNetwork"]


class QuantumLayer(nn.Module):
    """Variational quantum circuit layer with angle encoding.

    Input:  ``(batch, n_qubits)`` real features (any scale; tanh-bounded).
    Output: ``(batch, n_qubits)`` real <Z> expectations.
    """

    def __init__(
        self,
        n_qubits: int,
        n_layers: int = 2,
        device: Optional[torch.device] = None,
    ) -> None:
        super().__init__()
        if n_qubits < 1:
            raise ValueError("n_qubits must be >= 1")
        if n_layers < 1:
            raise ValueError("n_layers must be >= 1")
        self.n_qubits = n_qubits
        self.n_layers = n_layers
        self.device = device if device is not None else get_device()
        # angles[0] = RY, angles[1] = RZ per (layer, qubit)
        self.angles = nn.Parameter(0.1 * torch.randn(2, n_layers, n_qubits))
        self._sim = StatevectorSimulator(n_qubits, device=self.device)

    @property
    def sim(self) -> StatevectorSimulator:
        return self._sim

    def _encode(self, x: torch.Tensor) -> torch.Tensor:
        """Angle encoding: RY(pi * tanh(x_q)) applied per sample per qubit."""
        batch = x.shape[0]
        theta = math.pi * torch.tanh(x.to(torch.float64))  # (batch, n_qubits)
        cos = torch.cos(theta / 2)
        sin = torch.sin(theta / 2)
        gates = torch.zeros(
            batch, self.n_qubits, 2, 2,
            dtype=self._sim.dtype, device=self._sim.device,
        )
        gates[:, :, 0, 0] = cos.to(self._sim.dtype)
        gates[:, :, 0, 1] = (-sin).to(self._sim.dtype)
        gates[:, :, 1, 0] = sin.to(self._sim.dtype)
        gates[:, :, 1, 1] = cos.to(self._sim.dtype)

        state = self._sim.zero_state(batch)
        for q in range(self.n_qubits):
            state = self._sim.apply_1q_per_sample(state, gates[:, q], q)
        return state

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() != 2 or x.shape[1] != self.n_qubits:
            raise ValueError(
                f"expected input of shape (batch, {self.n_qubits}), got {tuple(x.shape)}"
            )
        state = self._encode(x)
        ry, rz = self.angles[0], self.angles[1]
        for layer in range(self.n_layers):
            for q in range(self.n_qubits):
                state = self._sim.apply_1q(state, qg.RY(ry[layer, q]), q)
                state = self._sim.apply_1q(state, qg.RZ(rz[layer, q]), q)
            for q in range(self.n_qubits):
                state = self._sim.apply_2q(state, qg.CNOT, q, (q + 1) % self.n_qubits)
        expectations = torch.stack(
            [self._sim.expectation_z(state, q) for q in range(self.n_qubits)], dim=1
        )
        return expectations


class QuantumNeuralNetwork(nn.Module):
    """Hybrid classical -> quantum -> classical network.

    Args:
        in_features: dimension of the classical input.
        n_qubits: number of qubits (must be <= in_features alignment handled
            internally by the preprocessing layer).
        out_features: dimension of the classical output.
        n_layers: variational depth.
    """

    def __init__(
        self,
        in_features: int,
        n_qubits: int = 6,
        out_features: int = 2,
        n_layers: int = 2,
        device: Optional[torch.device] = None,
    ) -> None:
        super().__init__()
        if in_features < 1 or out_features < 1:
            raise ValueError("in_features and out_features must be >= 1")
        self.in_features = in_features
        self.out_features = out_features
        self.q_layer = QuantumLayer(n_qubits, n_layers=n_layers, device=device)
        self.classical_in = nn.Linear(in_features, n_qubits)
        self.classical_out = nn.Linear(n_qubits, out_features)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = torch.tanh(self.classical_in(x))
        q = self.q_layer(h)
        return self.classical_out(q)
