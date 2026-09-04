"""Spiking Neural Network with STDP learning (biologically-plausible rule).

The STDP update uses eligibility traces: pre-synaptic activity before a
post-synaptic spike potentiates the weight; post-synaptic activity before a
pre-synaptic spike depresses it. This replaces the legacy implementation
whose update was dimensionally incoherent.
"""

from __future__ import annotations

from typing import Optional, Tuple

import torch
import torch.nn as nn

from eci.neuromorphic.neurons import LIFNeuron

__all__ = ["SpikingNeuralNetwork"]


class SpikingNeuralNetwork(nn.Module):
    """Two-layer spiking network (input -> hidden LIF -> output LIF)."""

    def __init__(
        self,
        n_input: int,
        n_hidden: int,
        n_output: int,
        tau_plus: float = 20.0,
        tau_minus: float = 20.0,
        a_plus: float = 0.01,
        a_minus: float = 0.012,
        w_min: float = 0.0,
        w_max: float = 2.0,
    ) -> None:
        super().__init__()
        if min(n_input, n_hidden, n_output) < 1:
            raise ValueError("layer sizes must be >= 1")
        self.n_input = n_input
        self.n_hidden = n_hidden
        self.n_output = n_output

        self.hidden_layer = LIFNeuron(n_hidden)
        self.output_layer = LIFNeuron(n_output)
        self.input_weights = nn.Parameter(torch.randn(n_input, n_hidden) * 0.1)

        # STDP parameters
        self.tau_plus = tau_plus
        self.tau_minus = tau_minus
        self.a_plus = a_plus
        self.a_minus = a_minus
        self.w_min = w_min
        self.w_max = w_max

        self.register_buffer("pre_trace", torch.zeros(n_input))
        self.register_buffer("post_trace", torch.zeros(n_hidden))

    # ------------------------------------------------------------------
    def reset_state(self, batch_size: int = 1) -> None:
        self.hidden_layer.reset_state(batch_size)
        self.output_layer.reset_state(batch_size)
        self.pre_trace.zero_()
        self.post_trace.zero_()

    def _rate_encode(self, x: torch.Tensor, n_steps: int) -> torch.Tensor:
        """Poisson rate coding: normalized values -> spike probabilities."""
        x = x.to(torch.float64)
        x_norm = (x - x.min()) / (x.max() - x.min() + 1e-12)
        probs = x_norm.clamp(0.0, 1.0).to(torch.float32).unsqueeze(0).expand(n_steps, -1)
        spike_train = torch.rand(n_steps, x.shape[0], device=x.device) < probs
        return spike_train.float()

    # ------------------------------------------------------------------
    def forward(self, x: torch.Tensor, n_steps: int = 100, learn: bool = False) -> torch.Tensor:
        """Simulate ``n_steps`` for each sample; returns output spike counts.

        Args:
            x: ``(batch, n_input)`` analog input.
            n_steps: simulation length.
            learn: apply online STDP to ``input_weights`` while simulating.
        """
        if x.dim() != 2 or x.shape[1] != self.n_input:
            raise ValueError(f"expected input (batch, {self.n_input}), got {tuple(x.shape)}")
        batch = x.shape[0]
        device = x.device
        output_spikes = torch.zeros(batch, self.n_output, device=device)

        # STDP uses a single-sample stream (standard for the rule); for
        # batches we accumulate mean weight change per sample.
        weight_delta = torch.zeros_like(self.input_weights) if learn else None

        for b in range(batch):
            self.reset_state(1)
            input_train = self._rate_encode(x[b], n_steps)
            if learn:
                self.pre_trace.zero_()
                self.post_trace.zero_()

            for t in range(n_steps):
                pre_spikes = input_train[t]  # (n_input,)
                hidden_current = pre_spikes @ self.input_weights
                hidden_spikes = self.hidden_layer(hidden_current.unsqueeze(0))[0]

                out_current = hidden_spikes @ self.hidden_layer.weight
                out_spikes = self.output_layer(out_current.unsqueeze(0))[0]
                output_spikes[b] += out_spikes.detach()

                if learn and weight_delta is not None:
                    # Trace updates (exponential decay, per-time-step)
                    self.pre_trace = self.pre_trace * (1 - 1.0 / self.tau_plus) + pre_spikes
                    self.post_trace = self.post_trace * (1 - 1.0 / self.tau_minus) + hidden_spikes
                    # dw[i,j] = a+ * pre_trace[i] * post_spike[j]
                    #         - a- * post_trace[j] * pre_spike[i]
                    dw = (
                        self.a_plus * torch.outer(self.pre_trace, hidden_spikes)
                        - self.a_minus * (self.post_trace.unsqueeze(0) * pre_spikes.unsqueeze(1))
                    )
                    weight_delta += dw

        if learn and weight_delta is not None:
            with torch.no_grad():
                self.input_weights.add_(weight_delta / batch)
                self.input_weights.clamp_(self.w_min, self.w_max)
        return output_spikes

    # ------------------------------------------------------------------
    def stdp_step(
        self,
        pre_spikes: torch.Tensor,
        post_spikes: torch.Tensor,
    ) -> torch.Tensor:
        """One explicit STDP update; returns the applied weight change.

        Args:
            pre_spikes: ``(n_input,)`` binary pre-synaptic spikes.
            post_spikes: ``(n_hidden,)`` binary post-synaptic spikes.
        """
        self.pre_trace = self.pre_trace * (1 - 1.0 / self.tau_plus) + pre_spikes
        self.post_trace = self.post_trace * (1 - 1.0 / self.tau_minus) + post_spikes
        dw = (
            self.a_plus * torch.outer(self.pre_trace, post_spikes)
            - self.a_minus * (self.post_trace.unsqueeze(0) * pre_spikes.unsqueeze(1))
        )
        with torch.no_grad():
            self.input_weights.add_(dw)
            self.input_weights.clamp_(self.w_min, self.w_max)
        return dw
