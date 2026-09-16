"""Advanced spiking neuron models (Phase 23+ neuron atlas).

Batched over ``(batch, n_neurons)`` like :class:`LIFNeuron`:

* :class:`AdaptiveLIFNeuron` — LIF + spike-triggered adaptation current ``w``
  (Allen GLIF-style, single adaptation variable; subthreshold coupling ``a``,
  spike-triggered increment ``b``, decay ``tau_w``).
* :class:`IzhikevichNeuron` — canonical (a, b, c, d) dynamics, Euler step,
  hard threshold at 30 mV, surrogate-gradient option for BPTT.
* :class:`HomeostaticLIFNeuron` — LIF with slow threshold adaptation toward
  a target firing rate (intrinsic plasticity; Turrigiano-style).

All models expose ``reset_state(batch_size)``, ``firing_rates(window)`` and
return spikes ``(batch, n_neurons)`` from ``forward``. Deterministic on CPU.
"""

from __future__ import annotations

import math

import torch
import torch.nn as nn

__all__ = ["AdaptiveLIFNeuron", "IzhikevichNeuron", "HomeostaticLIFNeuron"]


class AdaptiveLIFNeuron(nn.Module):
    """LIF + adaptation current w: dv/dt = (-(v-vr) - w + I)/tau_m."""

    def __init__(
        self,
        n_neurons: int,
        tau_m: float = 20.0,
        tau_w: float = 100.0,
        a: float = 0.1,
        b: float = 0.2,
        v_threshold: float = 1.0,
        v_reset: float = 0.0,
        surrogate: bool = False,
        batch_size: int = 1,
    ) -> None:
        super().__init__()
        if n_neurons < 1:
            raise ValueError("n_neurons must be >= 1")
        if tau_m <= 0 or tau_w <= 0:
            raise ValueError("tau_m and tau_w must be positive")
        self.n_neurons = n_neurons
        self.tau_m = tau_m
        self.tau_w = tau_w
        self.a = a
        self.b = b
        self.v_threshold = v_threshold
        self.v_reset = v_reset
        self.surrogate = surrogate
        self.weight = nn.Parameter(torch.randn(n_neurons, n_neurons) * (1.0 / math.sqrt(n_neurons)))
        self.register_buffer("membrane_potential", torch.zeros(batch_size, n_neurons))
        self.register_buffer("adaptation", torch.zeros(batch_size, n_neurons))
        self.register_buffer("spike_history", torch.zeros(batch_size, n_neurons, 100))

    def reset_state(self, batch_size: int | None = None) -> None:
        if batch_size is None:
            batch_size = self.membrane_potential.shape[0]  # type: ignore[has-type]
        device = self.membrane_potential.device  # type: ignore[has-type]
        self.membrane_potential = torch.zeros(batch_size, self.n_neurons, device=device)
        self.adaptation = torch.zeros(batch_size, self.n_neurons, device=device)
        self.spike_history = torch.zeros(batch_size, self.n_neurons, 100, device=device)

    def _spike_fn(self, v: torch.Tensor) -> torch.Tensor:
        if self.surrogate:
            return torch.sigmoid(4.0 * (v - self.v_threshold))
        return (v >= self.v_threshold).to(v.dtype)

    def forward(self, input_current: torch.Tensor, dt: float = 1.0) -> torch.Tensor:
        if input_current.shape != self.membrane_potential.shape:
            raise ValueError(
                f"input_current shape {tuple(input_current.shape)} does not match "
                f"state {tuple(self.membrane_potential.shape)}"
            )
        recurrent = self.weight @ self.membrane_potential.T
        recurrent = recurrent.T
        dv = (-(self.membrane_potential - self.v_reset) - self.adaptation + input_current + recurrent) / self.tau_m
        dw = (self.a * (self.membrane_potential - self.v_reset) - self.adaptation) / self.tau_w
        self.membrane_potential = self.membrane_potential + dv * dt
        self.adaptation = self.adaptation + dw * dt
        spikes = self._spike_fn(self.membrane_potential)
        hard = spikes.bool() if not self.surrogate else (self.membrane_potential >= self.v_threshold)
        self.membrane_potential = torch.where(
            hard, torch.full_like(self.membrane_potential, self.v_reset), self.membrane_potential
        )
        self.adaptation = torch.where(hard, self.adaptation + self.b, self.adaptation)
        self.spike_history = torch.roll(self.spike_history, -1, dims=2)
        self.spike_history[:, :, -1] = spikes.detach()
        return spikes

    def firing_rates(self, window: int = 100) -> torch.Tensor:
        return self.spike_history[:, :, -window:].mean(dim=2)


class IzhikevichNeuron(nn.Module):
    """Canonical Izhikevich (2003) dynamics, Euler-integrated."""

    def __init__(
        self,
        n_neurons: int,
        a: float = 0.02,
        b: float = 0.2,
        c: float = -65.0,
        d: float = 8.0,
        v_threshold: float = 30.0,
        surrogate: bool = False,
        batch_size: int = 1,
    ) -> None:
        super().__init__()
        if n_neurons < 1:
            raise ValueError("n_neurons must be >= 1")
        self.n_neurons = n_neurons
        self.a = a
        self.b = b
        self.c = c
        self.d = d
        self.v_threshold = v_threshold
        self.surrogate = surrogate
        self.weight = nn.Parameter(torch.randn(n_neurons, n_neurons) * 0.05)
        self.register_buffer("v", torch.full((batch_size, n_neurons), c))
        self.register_buffer("u", torch.full((batch_size, n_neurons), b * c))
        self.register_buffer("spike_history", torch.zeros(batch_size, n_neurons, 100))

    def reset_state(self, batch_size: int | None = None) -> None:
        if batch_size is None:
            batch_size = self.v.shape[0]  # type: ignore[has-type]
        device = self.v.device  # type: ignore[has-type]
        self.v = torch.full((batch_size, self.n_neurons), self.c, device=device)
        self.u = torch.full((batch_size, self.n_neurons), self.b * self.c, device=device)
        self.spike_history = torch.zeros(batch_size, self.n_neurons, 100, device=device)

    def forward(self, input_current: torch.Tensor, dt: float = 1.0) -> torch.Tensor:
        if input_current.shape != self.v.shape:
            raise ValueError(
                f"input_current shape {tuple(input_current.shape)} does not match state {tuple(self.v.shape)}"
            )
        recurrent = (self.weight @ self.v.T).T * 0.1
        v, u = self.v, self.u
        dv = 0.04 * v * v + 5.0 * v + 140.0 - u + input_current + recurrent
        du = self.a * (self.b * v - u)
        v = v + dv * dt
        u = u + du * dt
        if self.surrogate:
            spikes = torch.sigmoid(0.5 * (v - self.v_threshold))
            hard = v >= self.v_threshold
        else:
            hard = v >= self.v_threshold
            spikes = hard.to(v.dtype)
        v = torch.where(hard, torch.full_like(v, self.c), v)
        u = torch.where(hard, u + self.d, u)
        self.v, self.u = v, u
        self.spike_history = torch.roll(self.spike_history, -1, dims=2)
        self.spike_history[:, :, -1] = spikes.detach()
        return spikes

    def firing_rates(self, window: int = 100) -> torch.Tensor:
        return self.spike_history[:, :, -window:].mean(dim=2)


class HomeostaticLIFNeuron(nn.Module):
    """LIF with slow threshold adaptation toward a target rate."""

    def __init__(
        self,
        n_neurons: int,
        tau_m: float = 20.0,
        v_reset: float = 0.0,
        target_rate: float = 0.05,
        eta: float = 0.01,
        v_threshold_init: float = 1.0,
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
        self.v_reset = v_reset
        self.target_rate = target_rate
        self.eta = eta
        self.surrogate = surrogate
        self.weight = nn.Parameter(torch.randn(n_neurons, n_neurons) * (1.0 / math.sqrt(n_neurons)))
        self.register_buffer("membrane_potential", torch.zeros(batch_size, n_neurons))
        self.register_buffer("threshold", torch.full((batch_size, n_neurons), v_threshold_init))
        self.register_buffer("spike_history", torch.zeros(batch_size, n_neurons, 100))

    def reset_state(self, batch_size: int | None = None) -> None:
        if batch_size is None:
            batch_size = self.membrane_potential.shape[0]  # type: ignore[has-type]
        device = self.membrane_potential.device  # type: ignore[has-type]
        init = float(self.threshold.mean().item()) if self.threshold.numel() else 1.0  # type: ignore[has-type]
        self.membrane_potential = torch.zeros(batch_size, self.n_neurons, device=device)
        self.threshold = torch.full((batch_size, self.n_neurons), init, device=device)
        self.spike_history = torch.zeros(batch_size, self.n_neurons, 100, device=device)

    def forward(self, input_current: torch.Tensor, dt: float = 1.0) -> torch.Tensor:
        if input_current.shape != self.membrane_potential.shape:
            raise ValueError(
                f"input_current shape {tuple(input_current.shape)} does not match "
                f"state {tuple(self.membrane_potential.shape)}"
            )
        recurrent = (self.weight @ self.membrane_potential.T).T
        dv = (-(self.membrane_potential - self.v_reset) + input_current + recurrent) / self.tau_m
        self.membrane_potential = self.membrane_potential + dv * dt
        if self.surrogate:
            spikes = torch.sigmoid(4.0 * (self.membrane_potential - self.threshold))
            hard = self.membrane_potential >= self.threshold
        else:
            hard = self.membrane_potential >= self.threshold
            spikes = hard.to(self.membrane_potential.dtype)
        self.membrane_potential = torch.where(
            hard, torch.full_like(self.membrane_potential, self.v_reset), self.membrane_potential
        )
        # Intrinsic plasticity: threshold chases observed rate.
        with torch.no_grad():
            inst = hard.to(self.membrane_potential.dtype)
            self.threshold = (self.threshold + self.eta * (inst - self.target_rate)).clamp_min(0.2)
        self.spike_history = torch.roll(self.spike_history, -1, dims=2)
        self.spike_history[:, :, -1] = spikes.detach()
        return spikes

    def firing_rates(self, window: int = 100) -> torch.Tensor:
        return self.spike_history[:, :, -window:].mean(dim=2)
