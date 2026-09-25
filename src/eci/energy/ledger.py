"""Energy ledger (P1-5): price every decision in Joules.

SpikingBrain lesson: sparsity is energy. AC (accumulate, SNN) costs ~0.9pJ,
MAC (dense ANN) ~4.6pJ (Horowitz 45nm reference numbers, documented as
estimates). The ledger converts op counts + spikes into Joules, tracks
sparsity, and converts energy into economy cost so expensive creativity
pays for itself.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

__all__ = ["EnergyLedger", "EnergyRecord", "JOULE_PER_AC", "JOULE_PER_MAC"]

JOULE_PER_AC = 0.9e-12
JOULE_PER_MAC = 4.6e-12


@dataclass
class EnergyRecord:
    decision_id: str
    joules: float
    ac_ops: int
    mac_ops: int
    sparsity: float
    priced_cost: float = 0.0
    ts: float = field(default_factory=time.time)


class EnergyLedger:
    """Joules accounting with economy pricing hook."""

    def __init__(self, joule_price: float = 1e9) -> None:
        # joule_price: economy credits per Joule (default 1 credit per nJ)
        self.joule_price = joule_price
        self.records: list[EnergyRecord] = []

    def _append(self, rec: EnergyRecord) -> EnergyRecord:
        self.records.append(rec)
        return rec

    def record(self, decision_id: str, ac_ops: int = 0, mac_ops: int = 0,
               active_units: int = 0, total_units: int = 0) -> EnergyRecord:
        joules = ac_ops * JOULE_PER_AC + mac_ops * JOULE_PER_MAC
        sparsity = 1.0 - (active_units / total_units) if total_units else 0.0
        return self._append(EnergyRecord(
            decision_id=decision_id, joules=joules, ac_ops=ac_ops, mac_ops=mac_ops,
            sparsity=max(0.0, min(1.0, sparsity)), priced_cost=joules * self.joule_price))

    def record_brain_cycle(self, decision_id: str, spikes: int, n_neurons: int,
                           ticks: int) -> EnergyRecord:
        if spikes:
            # one AC per spike delivery to the population
            return self.record(decision_id, ac_ops=spikes * n_neurons,
                               active_units=spikes, total_units=n_neurons * ticks)
        # silent cycle: dense baseline would still pay the full matvec
        mac = n_neurons * n_neurons * ticks
        return self._append(EnergyRecord(
            decision_id=decision_id, joules=mac * JOULE_PER_MAC,
            ac_ops=0, mac_ops=mac, sparsity=0.0,
            priced_cost=mac * JOULE_PER_MAC * self.joule_price))

    def total_joules(self) -> float:
        return sum(r.joules for r in self.records)

    def mean_sparsity(self) -> float:
        if not self.records:
            return 0.0
        return sum(r.sparsity for r in self.records) / len(self.records)

    def charge_to_economy(self, economy: Any, agent_id: str) -> dict[str, Any]:
        total = sum(r.priced_cost for r in self.records)
        charge = getattr(economy, "charge", None) or getattr(economy, "spend", None)
        if charge is None:
            return {"ok": False, "error": "economy has no charge/spend", "owed": round(total, 6)}
        try:
            charge(agent_id, total)
            return {"ok": True, "charged": round(total, 6), "decisions": len(self.records)}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": repr(exc)[:160], "owed": round(total, 6)}

    def to_dict(self) -> dict[str, Any]:
        return {"decisions": len(self.records), "joules": self.total_joules(),
                "mean_sparsity": round(self.mean_sparsity(), 4),
                "priced": round(sum(r.priced_cost for r in self.records), 6)}
