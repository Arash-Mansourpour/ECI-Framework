"""Friston Free-Energy Principle (FEP) for ECI agents.

Theory
------
* Any self-organizing system at non-equilibrium steady state minimizes
  variational free energy F = E_q[ln q(s) - ln p(o,s)] ≥ -ln p(o)
  (surprise). Perception = gradient descent on F w.r.t. beliefs;
  action = gradient descent on F w.r.t. observations (active inference).
* Decomposition: F = D_KL(q(s)||p(s)) - E_q[ln p(o|s)]
                = complexity - accuracy.
* ECI use: each agent maintains a Gaussian belief over hidden causes of
  network observations; free-energy gradients drive learning and the
  consciousness level modulates precision (attention).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

import torch

__all__ = ["FreeEnergyAgent", "expected_free_energy"]


@dataclass
class FreeEnergyAgent:
    n_hidden: int = 4
    n_obs: int = 4
    precision: float = 1.0
    lr: float = 0.05
    mu: torch.Tensor | None = None
    A: torch.Tensor | None = None  # likelihood mapping hidden -> obs
    free_energy_history: List[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        g = torch.Generator().manual_seed(0)
        if self.mu is None:
            self.mu = torch.zeros(self.n_hidden, dtype=torch.float64)
        if self.A is None:
            self.A = torch.randn(self.n_obs, self.n_hidden, generator=g, dtype=torch.float64) / (self.n_hidden ** 0.5)

    def free_energy(self, obs: torch.Tensor) -> torch.Tensor:
        """F(μ) = ½[||o - Aμ||²_Π + ||μ||²] - ½ln|Π| + const."""
        o = obs.double()
        pred = self.A.double() @ self.mu.double()
        err = o - pred
        F = 0.5 * (self.precision * (err ** 2).sum() + (self.mu.double() ** 2).sum())
        return F

    def perceive(self, obs: torch.Tensor, steps: int = 20) -> Dict[str, float]:
        """Gradient descent on F w.r.t. beliefs μ (perception)."""
        mu = self.mu.double().clone().requires_grad_(True)
        opt = torch.optim.SGD([mu], lr=self.lr)
        for _ in range(steps):
            opt.zero_grad()
            pred = self.A.double() @ mu
            F = 0.5 * (self.precision * (((obs.double() - pred)) ** 2).sum() + (mu ** 2).sum())
            F.backward()
            opt.step()
        self.mu = mu.detach()
        Fval = float(self.free_energy(obs).item())
        self.free_energy_history.append(Fval)
        # complexity / accuracy split
        with torch.no_grad():
            pred = self.A.double() @ self.mu.double()
            accuracy = float((0.5 * self.precision * ((obs.double() - pred) ** 2).sum()).item())
            complexity = float((0.5 * (self.mu.double() ** 2).sum()).item())
        return {"F": Fval, "complexity": complexity, "accuracy": accuracy}

    def precision_from_consciousness(self, phi: float) -> float:
        """Attention = precision modulated by integrated information."""
        self.precision = 1.0 + float(min(max(phi, 0.0), 5.0))
        return self.precision

    def select_action(self, obs: torch.Tensor, actions: torch.Tensor, preferences: torch.Tensor) -> Dict[str, object]:
        """Active inference: pick the action minimizing expected free energy.

        Args:
            obs: current observation (n_obs).
            actions: (n_actions, n_obs) predicted observation shifts.
            preferences: prior preference distribution over obs bins
                (or a preferred observation vector — converted to softmax).
        Returns {action, G_values, F_after}.
        """
        g_vals = []
        for a in actions:
            pred = (self.A.double() @ self.mu.double() + a.double())
            # Softmax over predicted obs as Q(o|pi); preferences as P(o).
            q = torch.softmax(pred, dim=0)
            p = preferences.double()
            if p.shape != q.shape:
                p = torch.softmax(p.flatten()[: q.numel()], dim=0)
            p = p / p.sum().clamp_min(1e-12)
            g_vals.append(expected_free_energy(p, q))
        best = int(torch.argmin(torch.tensor(g_vals)).item())
        # Execute best action in belief space (one perception step after).
        self.mu = (self.mu.double() + 0.1 * (self.A.double().T @ actions[best].double())).detach()
        return {"action": best, "G_values": g_vals, "F_after": float(self.free_energy(obs).item())}


def expected_free_energy(pref_prob: torch.Tensor, predicted_prob: torch.Tensor) -> float:
    """G(π) = D_KL(Q(o|π)||P(o)) - E[H[Q]] ≈ risk - ambiguity (discrete)."""
    q = predicted_prob.clamp_min(1e-12)
    p = pref_prob.clamp_min(1e-12)
    q = q / q.sum()
    p = p / p.sum()
    risk = float((q * torch.log(q / p)).sum().item())
    ambiguity = float((-(q * torch.log(q))).sum().item())
    return risk - ambiguity
