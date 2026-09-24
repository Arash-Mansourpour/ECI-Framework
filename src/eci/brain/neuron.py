"""BrainNeuron: adaptive-threshold LIF with Dale E/I + short-term plasticity.

Synthesis of 2026 advances:
- ALIF (SpikingBrain/PHC): threshold adapts up on spike, decays back
- Tsodyks-Markram (PHC): release prob U + resources x gate the output
- Homeostasis: slow threshold drift toward target firing rate
- Dale's law: neuron is fixed excitatory (+1) or inhibitory (-1) for life

Pure torch, CPU-first, deterministic given seed. No autograd needed.
"""

from __future__ import annotations

import torch

__all__ = ["BrainNeuron"]


class BrainNeuron:
    def __init__(self, n: int, excitatory: bool = True, seed: int = 0,
                 tau_m: float = 20.0, v_rest: float = 0.0, v_reset: float = 0.0,
                 v_th0: float = 1.0, adapt_strength: float = 0.3, adapt_decay: float = 0.95,
                 u0: float = 0.5, tau_rec: float = 100.0, tau_fac: float = 50.0,
                 target_rate: float = 0.05, homeo_rate: float = 0.001) -> None:
        g = torch.Generator().manual_seed(seed)
        self.n = n
        self.sign = 1.0 if excitatory else -1.0
        self.tau_m = tau_m
        self.v_rest = v_rest
        self.v_reset = v_reset
        self.v_th0 = v_th0
        self.adapt_strength = adapt_strength
        self.adapt_decay = adapt_decay
        self.u0 = u0
        self.tau_rec = tau_rec
        self.tau_fac = tau_fac
        self.target_rate = target_rate
        self.homeo_rate = homeo_rate
        self.v = torch.full((n,), v_rest)
        self.th = torch.full((n,), v_th0)
        self.u = torch.full((n,), u0)  # release probability
        self.x = torch.ones(n)  # available resources
        self.rate_ema = torch.full((n,), target_rate)
        self.steps = 0
        self.spike_count = 0
        self._gen = g

    def reset(self) -> None:
        self.v.fill_(self.v_rest)
        self.th.fill_(self.v_th0)
        self.u.fill_(self.u0)
        self.x.fill_(1.0)
        self.rate_ema.fill_(self.target_rate)
        self.steps = 0
        self.spike_count = 0

    def step(self, current: torch.Tensor, dt: float = 1.0) -> torch.Tensor:
        """One ms tick. current: (n,) input. Returns binary spikes (n,)."""
        cur = current.to(torch.float32).reshape(self.n)
        # membrane integration
        self.v = self.v + (dt / self.tau_m) * ((self.v_rest - self.v) + cur)
        # short-term plasticity dynamics (Tsodyks-Markram, discrete)
        self.u = self.u + (dt / self.tau_fac) * (self.u0 - self.u)
        self.x = self.x + (dt / self.tau_rec) * (1.0 - self.x)
        spikes = (self.v >= self.th).float()
        # gate spikes by available resources (depression); update on spike
        eff = spikes * self.x * self.u
        fired = (eff > 0).float()
        # reset + adaptation + facilitation/depletion
        self.v = torch.where(fired > 0, torch.full_like(self.v, self.v_reset), self.v)
        self.th = self.adapt_decay * self.th + self.adapt_strength * fired
        self.th = self.th + self.homeo_rate * (self.rate_ema - self.target_rate)
        self.u = torch.where(fired > 0, self.u + 0.1 * (1.0 - self.u), self.u)
        self.x = torch.where(fired > 0, self.x * 0.7, self.x)
        # threshold homeostasis bounds
        self.th.clamp_(0.5 * self.v_th0, 3.0 * self.v_th0)
        self.rate_ema = 0.99 * self.rate_ema + 0.01 * fired
        self.steps += 1
        self.spike_count += int(fired.sum().item())
        return fired * self.sign  # signed spikes enforce Dale downstream
