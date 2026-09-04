"""Second-order cybernetics & autopoiesis for ECI (paper §2.3).

* Autopoietic closure: network of processes that recursively produce the
  components (and boundary) that produce them (Maturana & Varela).
* Second-order: the observer is inside the system; viability = continued
  autopoiesis under structural coupling with the environment.
* Viability theory (Aubin): state must remain in constraint set K under
  differential inclusion dx/dt ∈ F(x); viability kernel = survivable states.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List

import torch

__all__ = ["AutopoieticNetwork", "viability_margin", "ashby_requisite_variety"]


@dataclass
class AutopoieticNetwork:
    n_components: int = 6
    production_rate: float = 0.5
    decay_rate: float = 0.2
    boundary_threshold: float = 0.4
    concentrations: torch.Tensor | None = None
    history: List[Dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.concentrations is None:
            self.concentrations = torch.full((self.n_components,), 0.6, dtype=torch.float64)

    def step(self, environment: torch.Tensor | None = None) -> Dict[str, float]:
        """c' = P·c(1-c) - D·c + coupling(env); boundary intact if mean(c)>θ."""
        c = self.concentrations.double()
        production = self.production_rate * c * (1 - c)
        decay = self.decay_rate * c
        drive = 0.0
        if environment is not None:
            drive = float(environment.double().mean().item()) * 0.05
        c = (c + production - decay + drive).clamp(0.0, 1.0)
        self.concentrations = c
        closure = float((production.sum() / (decay.sum() + 1e-12)).item())
        boundary = float(c.mean().item())
        viable = bool(boundary > self.boundary_threshold and closure > 0.8)
        rec = {"closure": closure, "boundary": boundary, "viable": viable}
        self.history.append(rec)
        return rec

    def viability_rate(self) -> float:
        if not self.history:
            return 0.0
        return sum(1 for r in self.history if r["viable"]) / len(self.history)


def viability_margin(state: torch.Tensor, lower: float = 0.1, upper: float = 0.9) -> float:
    """Distance of state to constraint-set boundary (Aubin viability margin)."""
    d = torch.minimum(state - lower, upper - state)
    return float(d.min().item())


def ashby_requisite_variety(disturbances: int, responses: int) -> Dict[str, float]:
    """Ashby's law: regulator needs H(R) ≥ H(D) - H(acceptable)."""
    import math as _m

    Hd = _m.log2(max(2, disturbances))
    Hr = _m.log2(max(2, responses))
    return {"H_disturbance": Hd, "H_response": Hr, "sufficient": 1.0 if Hr >= Hd - 1.0 else 0.0}
