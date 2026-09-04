"""Leaky Integrate-and-Fire neurons (Gerstner & Kistler 2002).

Batched over ``(batch, n_neurons)`` membrane states. The spike
non-linearity optionally uses a sigmoid surrogate gradient so the network
remains trainable with backprop-through-time; the hard threshold is used
for faithful simulation when ``surrogate=False``.
"""

from __future__ import annotations

import math
from typing import Optional

import torch
import torch.nn as nn

__all__ = ["LIFNeuron"]


class LIFNeuron(nn.Module):
    """Leaky Integrate-and-Fire neuron layer with learnable recurrence."""

    def __init__(
        self,
        n_neurons: int,
        tau_m: float = 20.0,
        v_threshold: float = 1.0,
        v_reset: float = 0.0,
        surrogate: bool = False,
        batch_size: int = 1,
    ) -> None:
        super().__init__()
        if n_neurons < 1:
            raise ValueError("n_neurons must be >= 1")
        if tau_m <= 0:
            raise ValueError("tau_m must be positive")
        self.n_neurons = n_neurons
        self.tau_m = tau_m
        self.v_threshold = v_threshold
        self.v_reset = v_reset
        self.surrogate = surrogate

        self.weight = nn.Parameter(torch.randn(n_neurons, n_neurons) * (1.0 / math.sqrt(n_neurons)))
        self.register_buffer("membrane_potential", torch.zeros(batch_size, n_neurons))
        self.register_buffer("spike_history", torch.zeros(batch_size, n_neurons, 100))

    # ------------------------------------------------------------------
    def reset_state(self, batch_size: Optional[int] = None) -> None:
        if batch_size is None:
            batch_size = self.membrane_potential.shape[0]
        device = self.membrane_potential.device
        self.membrane_potential = torch.zeros(batch_size, self.n_neurons, device=device)
        self.spike_history = torch.zeros(batch_size, self.n_neurons, 100, device=device)

    def _spike_fn(self, v: torch.Tensor) -> torch.Tensor:
        if self.surrogate:
            # Sigmoid surrogate: forward ~ threshold behavior, gradient flows.
            return torch.sigmoid(4.0 * (v - self.v_threshold))
        return (v >= self.v_threshold).to(v.dtype)

    def forward(
        self,
        input_current: torch.Tensor,
        dt: float = 1.0,
        learnable_recurrence: bool = True,
    ) -> torch.Tensor:
        """One simulation step.

        Args:
            input_current: ``(batch, n_neurons)`` synaptic current.
            dt: time step (ms).
            learnable_recurrence: apply the internal weight matrix (this
                makes the layer's recurrent current learnable).

        Returns:
            Spikes ``(batch, n_neurons)``.
        """
        if input_current.shape != self.membrane_potential.shape:
            raise ValueError(
                f"input_current shape {tuple(input_current.shape)} does not match "
                f"state {tuple(self.membrane_potential.shape)}"
            )
        recurrent = self.weight @ self.membrane_potential.T if learnable_recurrence else 0.0
        recurrent = recurrent.T if learnable_recurrence else 0.0
        dv = (-(self.membrane_potential - self.v_reset) + input_current + recurrent) / self.tau_m
        self.membrane_potential = self.membrane_potential + dv * dt

        spikes = self._spike_fn(self.membrane_potential)
        if not self.surrogate:
            self.membrane_potential = torch.where(
                spikes.bool(),
                torch.full_like(self.membrane_potential, self.v_reset),
                self.membrane_potential,
            )
        else:
            # Soft reset for surrogate-gradient training.
            self.membrane_potential = self.membrane_potential * (1.0 - spikes.detach())

        self.spike_history = torch.roll(self.spike_history, -1, dims=2)
        self.spike_history[:, :, -1] = spikes.detach()
        return spikes

    def firing_rates(self, window: int = 100) -> torch.Tensor:
        """Estimated firing rates over the recorded history window."""
        return self.spike_history[:, :, -window:].mean(dim=2)
