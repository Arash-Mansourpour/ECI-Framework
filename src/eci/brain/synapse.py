"""PlasticSynapse: local three-factor STDP + metaplasticity (Loihi2-style).

- Eligibility traces per pre/post; weight update only on spikes (event-driven)
- Third factor m (dopamine-like broadcast from workspace ignition) gates LTP
- Metaplasticity: consolidation c in [0,1] freezes important synapses
  (EWC-like, but local); c grows with |w| change, decays slowly
- Dale: sign mask fixed at init; weights stay non-negative magnitudes
"""

from __future__ import annotations

import torch

__all__ = ["PlasticSynapse"]


class PlasticSynapse:
    def __init__(self, n_pre: int, n_post: int, seed: int = 0,
                 a_plus: float = 0.01, a_minus: float = 0.012,
                 tau_plus: float = 20.0, tau_minus: float = 20.0,
                 w_min: float = 0.0, w_max: float = 2.0,
                 excitatory: bool = True) -> None:
        g = torch.Generator().manual_seed(seed)
        self.n_pre = n_pre
        self.n_post = n_post
        self.a_plus = a_plus
        self.a_minus = a_minus
        self.tau_plus = tau_plus
        self.tau_minus = tau_minus
        self.w_min = w_min
        self.w_max = w_max
        self.sign = 1.0 if excitatory else -1.0
        self.w = (torch.rand(n_pre, n_post, generator=g) * 0.2 + 0.05)
        self.pre_trace = torch.zeros(n_pre)
        self.post_trace = torch.zeros(n_post)
        self.consolidation = torch.zeros(n_pre, n_post)  # metaplasticity 0..1
        self.updates = 0

    def forward(self, pre_spikes: torch.Tensor) -> torch.Tensor:
        """pre_spikes signed (n_pre,) -> postsynaptic current (n_post,)."""
        mag = pre_spikes.abs()
        return (mag @ self.w) * self.sign

    def stdp(self, pre: torch.Tensor, post: torch.Tensor, mod: float = 1.0) -> float:
        """Event-driven update. Returns mean |dW| applied."""
        pre_b = (pre.abs() > 0).float()
        post_b = (post.abs() > 0).float()
        if pre_b.sum() == 0 and post_b.sum() == 0:
            # traces still decay
            self.pre_trace *= 0.95
            self.post_trace *= 0.95
            return 0.0
        self.pre_trace = self.pre_trace * 0.95 + pre_b
        self.post_trace = self.post_trace * 0.95 + post_b
        # LTP on post spike gated by pre trace + third factor; LTD reverse
        ltp = self.a_plus * mod * (self.pre_trace.unsqueeze(1) * post_b.unsqueeze(0))
        ltd = self.a_minus * (pre_b.unsqueeze(1) * self.post_trace.unsqueeze(0))
        dw = (ltp - ltd) * (1.0 - self.consolidation)  # frozen synapses resist
        if dw.abs().max() == 0:
            return 0.0
        self.w = (self.w + dw).clamp_(self.w_min, self.w_max)
        # metaplasticity: important changes consolidate
        self.consolidation = (self.consolidation + 0.001 * dw.abs()).clamp_(0.0, 0.9)
        self.updates += 1
        return float(dw.abs().mean().item())
