"""The conformance contract: every subsystem speaks posterior.

``StateContributor`` is the single trait the unification layer requires.
Adapters wrap existing subsystem logic (Phase 2) — internals stay intact,
but each module must expose:

  posterior()                  current Q(s) as a GenerativeState
  update(obs)                  assimilate an observation -> new Q(s)
  free_energy_contribution()   this subsystem's additive share of F

``KernelLedger`` sums contributions: total F is computed ONE way, from
shares every subsystem reports. A subsystem that cannot express its loss
as a share of F fails conformance loudly (missing share, NaN share) —
integration by construction, not by convention.
"""

from __future__ import annotations

from typing import Any, Dict, Protocol, runtime_checkable

import torch

from eci.aikernel.generative_model import GenerativeState

__all__ = ["StateContributor", "KernelLedger", "conforms"]


@runtime_checkable
class StateContributor(Protocol):
    def posterior(self) -> GenerativeState: ...
    def update(self, observation: torch.Tensor) -> GenerativeState: ...
    def free_energy_contribution(self) -> torch.Tensor: ...


def conforms(obj: Any) -> bool:
    """Structural check + smoke call of the three methods."""
    if not isinstance(obj, StateContributor):
        return False
    try:
        st = obj.posterior()
        if not isinstance(st, GenerativeState):
            return False
        share = obj.free_energy_contribution()
        if not torch.is_tensor(share) or share.numel() != 1:
            return False
        if not torch.isfinite(share.detach()):
            return False
        return True
    except Exception:  # noqa: BLE001
        return False


class KernelLedger:
    """Accumulates per-subsystem F shares into the one shared objective."""

    def __init__(self) -> None:
        self._members: Dict[str, StateContributor] = {}

    def register(self, name: str, member: StateContributor) -> None:
        if not conforms(member):
            raise TypeError(f"{name!r} does not conform to StateContributor")
        self._members[name] = member

    def members(self) -> Dict[str, StateContributor]:
        return dict(self._members)

    def shares(self) -> Dict[str, float]:
        return {k: float(m.free_energy_contribution().detach().item())
                for k, m in self._members.items()}

    def total_free_energy(self) -> torch.Tensor:
        """THE shared objective: one sum, every subsystem's share."""
        total = torch.tensor(0.0)
        for m in self._members.values():
            total = total + m.free_energy_contribution()
        return total
