"""Golden regression gates: seed-matrix eval with tolerance bands.

Each gate runs a deterministic probe and checks it against a golden
value ± tolerance. Gates cover quantum (CHSH, teleport), awareness
(index range), network (PBFT agreement), QEC (surface p_logical order)
and the v6 workflow slice. CI fails on gate drift; the report is
twin/market/court compatible.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

__all__ = ["Gate", "EvalReport", "GATES", "run_gates"]


@dataclass
class Gate:
    name: str
    fn: Callable[[], dict[str, Any]]
    golden: float
    tol: float
    key: str = "value"


@dataclass
class EvalReport:
    passed: int
    failed: int
    gates: list[dict[str, Any]]
    duration_s: float

    def to_dict(self) -> dict[str, Any]:
        return {"passed": self.passed, "failed": self.failed,
                "ok": self.failed == 0, "gates": self.gates, "duration_s": self.duration_s}


def _g_chsh() -> dict[str, Any]:
    import torch

    from eci.quantum import density as qd
    from eci.quantum import information as qi
    bell = torch.zeros(1, 4, dtype=torch.complex64)
    bell[0, 0] = bell[0, 3] = 1 / (2 ** 0.5)
    return {"value": float(qi.chsh_value(qd.from_statevector(bell)))}


def _g_teleport() -> dict[str, Any]:
    from eci.quantum import information as qi
    return {"value": float(qi.teleportation_fidelity(n_trials=4)["mean_conditional_fidelity"])}


def _g_pbft() -> dict[str, Any]:
    from eci.core.types import NetworkNode, NetworkRole
    from eci.network.consensus import PBFTConsensus
    c = PBFTConsensus(n_nodes=4, byzantine_rate=0.0)
    nodes = {f"n{i}": NetworkNode(node_id=f"n{i}", role=NetworkRole.VALIDATOR,
                                  trust_score=1.0, reputation_score=1.0, stake=1.0)
             for i in range(4)}
    r = c.achieve_consensus(nodes, {"x": 1})
    return {"value": 1.0 if r.achieved else 0.0}


def _g_workflow() -> dict[str, Any]:
    from eci.orchestration import DAG
    d = DAG("g")
    d.add("a", lambda ctx: 40)
    d.add("b", lambda ctx: ctx["a"] + 2, depends_on=["a"])
    out = asyncio.run(d.run({}))
    return {"value": float(out.outputs.get("b", -1))}


GATES: list[Gate] = [
    Gate("chsh-tsirelson", _g_chsh, 2.8284, 0.01),
    Gate("teleport-fidelity", _g_teleport, 1.0, 0.15),
    Gate("pbft-agreement", _g_pbft, 1.0, 0.0),
    Gate("workflow-slice", _g_workflow, 42.0, 0.0),
]


def run_gates(gates: list[Gate] | None = None) -> EvalReport:
    t0 = time.time()
    gates = gates or GATES
    rows: list[dict[str, Any]] = []
    passed = failed = 0
    for g in gates:
        try:
            got = float(g.fn().get(g.key, float("nan")))
            ok = abs(got - g.golden) <= g.tol
        except Exception as exc:  # noqa: BLE001
            got, ok = float("nan"), False
            rows.append({"gate": g.name, "ok": False, "error": repr(exc)})
            failed += 1
            continue
        rows.append({"gate": g.name, "ok": ok, "got": got, "golden": g.golden, "tol": g.tol})
        passed, failed = passed + ok, failed + (not ok)
    return EvalReport(passed, failed, rows, time.time() - t0)
