"""MAPE-K autonomic loop: the system operating on itself, safely.

Monitor (metrics/health) -> Analyze (SLO violations + z-anomalies) ->
Plan (remediation DAG, twin dry-run first) -> Execute (saga with
compensation) over shared Knowledge. Degradation is a *ladder*, not a
cliff: normal -> throttled -> degraded -> safe-mode, each rung declaring
which tool namespaces stay live. Every cycle is a provenance-recorded,
auditable, reversible act — autonomy with a paper trail.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

__all__ = ["SLO", "Strategy", "MAPEK", "LADDER"]

LADDER = ["normal", "throttled", "degraded", "safe-mode"]
LIVE_NS = {"normal": ["*"], "throttled": ["*.read", "workflow.*", "agent.*"],
           "degraded": ["*.read", "system.*"], "safe-mode": ["system.*", "p0.*"]}


@dataclass
class SLO:
    name: str
    metric: str
    threshold: float
    above: bool = True   # violate when metric > threshold (else < threshold)
    window: int = 8

    def violated(self, series: list[float]) -> bool:
        if not series:
            return False
        v = sum(series[-self.window:]) / min(len(series), self.window)
        return v > self.threshold if self.above else v < self.threshold


@dataclass
class Strategy:
    name: str
    applies: Callable[[str], bool]          # slo name -> relevant?
    dry: Callable[[], dict[str, Any]]       # twin simulation
    apply: Callable[[], Any]                # real effect (sync or async)
    compensate: Callable[[], Any] | None = None


class MAPEK:
    name = "mapek"

    def __init__(self, bus=None, provenance=None, audit=None) -> None:
        self.slos: list[SLO] = []
        self.strategies: list[Strategy] = []
        self.hist: dict[str, list[float]] = {}
        self.rung = "normal"
        self.bus = bus
        self.provenance = provenance
        self.audit = audit
        self.cycles = 0
        self.remediations = 0

    def add_slo(self, slo: SLO) -> None:
        self.slos.append(slo)

    def add_strategy(self, s: Strategy) -> None:
        self.strategies.append(s)

    def defaults(self) -> None:
        self.add_slo(SLO("error-rate", "errors", 5.0))
        self.add_slo(SLO("dlq-depth", "dlq", 20.0))
        self.add_strategy(Strategy("throttle-entry", lambda n: True,
                                   lambda: {"sim": "rate halved", "risk": "low"},
                                   lambda: self._set_rung("throttled"),
                                   lambda: self._set_rung("normal")))
        self.add_strategy(Strategy("shed-to-safe", lambda n: "dlq" in n,
                                   lambda: {"sim": "non-read tools parked", "risk": "medium"},
                                   lambda: self._set_rung("safe-mode"),
                                   lambda: self._set_rung("normal")))

    def _set_rung(self, rung: str) -> dict[str, str]:
        old, self.rung = self.rung, rung
        return {"from": old, "to": rung, "live": LIVE_NS[rung]}

    # -- cycle ------------------------------------------------------------
    async def cycle(self, metrics: dict[str, float]) -> dict[str, Any]:
        t0 = time.time()
        for k, v in metrics.items():
            self.hist.setdefault(k, []).append(float(v))
        # Analyze: SLO breach + z-anomaly(|z|>3 on 16-sample baseline)
        breaches = [s.name for s in self.slos if s.violated(self.hist.get(s.metric, []))]
        anomalies = []
        for k, series in self.hist.items():
            if len(series) >= 17:
                base, cur = series[-17:-1], series[-1]
                mu = sum(base) / len(base)
                sd = (sum((x - mu) ** 2 for x in base) / len(base)) ** 0.5 or 1e-9
                if abs(cur - mu) / sd > 3.0:
                    anomalies.append({"metric": k, "z": round((cur - mu) / sd, 2)})
        # Plan: first applicable strategy per breach, twin first
        plans = []
        for b in breaches:
            strat = next((s for s in self.strategies if s.applies(b)), None)
            if strat is None:
                plans.append({"slo": b, "strategy": None, "dry": {"sim": "no strategy"}})
                continue
            try:
                sim = strat.dry()
            except Exception as exc:  # noqa: BLE001
                sim = {"sim": f"dry-run failed: {exc}"}
            plans.append({"slo": b, "strategy": strat.name, "dry": sim})
        # Execute with compensation ledger
        applied, compensated = [], []
        for p in plans:
            strat = next((s for s in self.strategies if s.name == p["strategy"]), None)
            if strat is None:
                continue
            try:
                r = strat.apply()
                if asyncio.iscoroutine(r):
                    await r
                applied.append(strat.name)
                self.remediations += 1
            except Exception as exc:  # noqa: BLE001
                if strat.compensate is not None:
                    try:
                        rr = strat.compensate()
                        if asyncio.iscoroutine(rr):
                            await rr
                        compensated.append(strat.name)
                    except Exception:  # noqa: BLE001
                        pass
                p["error"] = repr(exc)
        self.cycles += 1
        report = {"cycle": self.cycles, "breaches": breaches, "anomalies": anomalies,
                  "plans": plans, "applied": applied, "compensated": compensated,
                  "rung": self.rung, "live": LIVE_NS[self.rung],
                  "duration_s": time.time() - t0}
        try:
            if self.provenance is not None:
                self.provenance.record("mapek.cycle", "mapek",
                                       {"metrics": sorted(metrics)}, {"rung": self.rung, "applied": applied}, {})
            if self.audit is not None:
                self.audit.append("mapek", "mapek.cycle", {"breaches": breaches, "rung": self.rung})
            if self.bus is not None:
                from eci.kernel.bus import Event
                self.bus.publish(Event(type="mapek.cycle.done", source="mapek",
                                       payload={"rung": self.rung, "breaches": breaches}))
        except Exception:  # noqa: BLE001
            pass
        return report

    def start(self) -> None: ...
    def stop(self) -> None: ...
    def health(self) -> dict[str, Any]:
        return {"ok": True, "rung": self.rung, "cycles": self.cycles,
                "remediations": self.remediations, "slos": len(self.slos)}
