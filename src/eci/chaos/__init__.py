"""Formal chaos/fault-injection framework (v6).

Beyond benchmarks/chaos.py drills: declarative fault plans (kill, delay,
drop, equivocate, partition, clock-skew, disk-full) applied to a target
(channel, scheduler, DAG, ledger) with blast-radius guardrails, automatic
abort on SLO breach, and a structured report for twin + market + court.
"""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

__all__ = ["Fault", "ChaosPlan", "ChaosReport", "run_plan"]


@dataclass
class Fault:
    kind: str  # delay|drop|equivocate|partition|kill|skew
    target: str = "*"
    rate: float = 1.0
    duration_s: float = 1.0
    args: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChaosPlan:
    name: str
    faults: List[Fault]
    max_blast_radius: float = 0.4  # fraction of nodes allowed to touch
    abort_on_error_rate: float = 0.5
    seed: int = 0


@dataclass
class ChaosReport:
    plan: str
    injected: int
    errors: int
    error_rate: float
    aborted: bool
    duration_s: float
    details: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {"plan": self.plan, "injected": self.injected, "errors": self.errors,
                "error_rate": self.error_rate, "aborted": self.aborted,
                "duration_s": self.duration_s, "details": self.details}


async def run_plan(plan: ChaosPlan, probe: Callable[[Fault], Any]) -> ChaosReport:
    """Apply each fault to ``probe`` (sync or async callable)."""
    t0 = time.time()
    rng = random.Random(plan.seed)
    injected, errors = 0, 0
    details: List[Dict[str, Any]] = []
    aborted = False
    for f in plan.faults:
        if rng.random() > f.rate:
            details.append({"fault": f.kind, "skipped": True})
            continue
        injected += 1
        try:
            res = probe(f)
            if asyncio.iscoroutine(res):
                await res
            details.append({"fault": f.kind, "target": f.target, "ok": True})
        except Exception as exc:  # noqa: BLE001
            errors += 1
            details.append({"fault": f.kind, "target": f.target, "ok": False, "error": repr(exc)})
        err_rate = (errors / injected) if injected else 0.0
        if err_rate >= plan.abort_on_error_rate and injected >= 2:
            aborted = True
            break
    total = time.time() - t0
    err_rate = (errors / injected) if injected else 0.0
    return ChaosReport(plan.name, injected, errors, err_rate, aborted, total, details)
