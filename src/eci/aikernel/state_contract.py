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

from typing import Any, Protocol, runtime_checkable

import torch

from eci.aikernel.generative_model import GenerativeState

__all__ = ["StateContributor", "KernelLedger", "conforms", "require_finite"]


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
        return bool(torch.isfinite(share.detach()).item())
    except Exception:  # noqa: BLE001
        return False


class KernelLedger:
    """Accumulates per-subsystem F shares into the one shared objective."""

    def __init__(self) -> None:
        self._members: dict[str, StateContributor] = {}

    def register(self, name: str, member: StateContributor) -> None:
        if not conforms(member):
            raise TypeError(f"{name!r} does not conform to StateContributor")
        self._members[name] = member

    def members(self) -> dict[str, StateContributor]:
        return dict(self._members)

    def shares(self) -> dict[str, float]:
        return {k: float(m.free_energy_contribution().detach().item())
                for k, m in self._members.items()}

    def total_free_energy(self) -> torch.Tensor:
        """THE shared objective: one sum, every subsystem's share."""
        total = torch.tensor(0.0)
        for m in self._members.values():
            total = total + m.free_energy_contribution()
        return total

    def snapshot(self) -> dict[str, Any]:
        """Audit artifact: shares + posteriors, JSON-safe (Phase 15).

        This is a RECORD, not a resurrection: optimizer states, RNG
        cursors and training histories are deliberately NOT captured, so
        a snapshot can verify the past but never replay it bit-for-bit.
        Anyone promising full state restore from this dict is overselling.
        """
        return {"members": {k: {"share": float(m.free_energy_contribution().detach().item()),
                                "posterior": m.posterior().to_dict()}
                            for k, m in self._members.items()}}


def require_finite(observation: Any, who: str) -> torch.Tensor:
    """Contract-level precondition (Phase 16 hardening).

    NaN/Inf observations used to be absorbed silently (agent/fep shares
    went NaN and poisoned the ledger total) or crashed deep inside
    numerics (quantum eigh ``_LinAlgError``). Both are now a loud,
    attributable ``ValueError`` at the boundary. Shape is preserved
    (callers that need windows keep them); valid-input behavior unchanged.
    """
    t = (observation if torch.is_tensor(observation)
         else torch.as_tensor(observation, dtype=torch.float32))
    try:
        ok = bool(torch.isfinite(t.float()).all().item())
    except Exception:  # noqa: BLE001
        ok = False
    if not ok:
        raise ValueError(f"{who}: non-finite observation")
    return t
