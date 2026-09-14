"""ECI-LEARN — Collective Learning Loop + Team Intelligence.

Loop: TASK→ROUTE→TEAM→EXECUTE→VERIFY→OutcomeReceipt→UPDATE CAPABILITY/TRUST/TEAM/ROUTER→LEARN (network learns how to become better network)
Team synergy: TS(A,B,C) = Perf(A+B+C) - max(PA,PB,PC) ; goal >0
CIG = Perf(Network)/max Perf(Node_i) ; EG = Perf(t+1)/Perf(t)
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any

__all__ = ["OutcomeReceipt", "TeamIntelligence", "CollectiveLearningLoop"]


@dataclass
class OutcomeReceipt:
    task: str
    agents: list[str]
    predicted_success: float
    actual_quality: float
    latency: int = 0
    cost: float = 0.0
    verifiers: list[str] = field(default_factory=list)
    agreement: float = 0.0
    evidence_hash: str = ""
    signature: str = ""
    ts: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if not self.evidence_hash:
            self.evidence_hash = hashlib.sha256(json.dumps({"task": self.task, "agents": self.agents, "quality": self.actual_quality}, sort_keys=True).encode()).hexdigest()[:16]
        if not self.signature:
            self.signature = hashlib.sha256(f"{self.evidence_hash}|{self.ts}".encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {"task": self.task, "agents": self.agents, "predicted": self.predicted_success,
                "actual": self.actual_quality, "latency": self.latency, "cost": self.cost,
                "verifiers": self.verifiers, "agreement": self.agreement,
                "evidence_hash": self.evidence_hash, "signature": self.signature}


class TeamIntelligence:
    def __init__(self) -> None:
        self._team_scores: dict[tuple[str, ...], list[float]] = {}
        self._individual: dict[str, list[float]] = {}

    def record(self, agents: list[str], quality: float) -> None:
        key = tuple(sorted(agents))
        self._team_scores.setdefault(key, []).append(quality)
        for a in agents:
            self._individual.setdefault(a, []).append(quality)

    def synergy(self, team: list[str]) -> float:
        key = tuple(sorted(team))
        team_perf = sum(self._team_scores.get(key, [0])) / max(1, len(self._team_scores.get(key, [0])))
        indiv_max = max((sum(self._individual.get(a, [0])) / max(1, len(self._individual.get(a, [0]))) for a in team), default=0)
        return team_perf - indiv_max

    def cig(self, team: list[str]) -> float:
        key = tuple(sorted(team))
        team_perf = sum(self._team_scores.get(key, [0])) / max(1, len(self._team_scores.get(key, [])))
        indiv_max = max((sum(v) / len(v) for v in self._individual.values()), default=1)
        return team_perf / max(indiv_max, 1e-9)

    def to_dict(self) -> dict[str, Any]:
        return {"teams": len(self._team_scores), "individuals": len(self._individual)}


class CollectiveLearningLoop:
    def __init__(self) -> None:
        self.receipts: list[OutcomeReceipt] = []
        self.team_intel = TeamIntelligence()
        self.capability_deltas: dict[str, float] = {}
        self.trust_deltas: dict[str, float] = {}

    def ingest(self, receipt: OutcomeReceipt) -> None:
        self.receipts.append(receipt)
        self.team_intel.record(receipt.agents, receipt.actual_quality)
        # update capability/trust deltas (simple EMA)
        for agent in receipt.agents:
            delta = receipt.actual_quality - receipt.predicted_success
            self.capability_deltas[agent] = self.capability_deltas.get(agent, 0) * 0.9 + delta * 0.1
            self.trust_deltas[agent] = self.trust_deltas.get(agent, 0) * 0.9 + (receipt.agreement - 0.5) * 0.1

    def learning_efficiency(self) -> float:
        if not self.receipts:
            return 0.0
        avg_quality = sum(r.actual_quality for r in self.receipts) / len(self.receipts)
        avg_cost = sum(r.cost for r in self.receipts) / len(self.receipts)
        return avg_quality / max(avg_cost, 1e-9)

    def to_dict(self) -> dict[str, Any]:
        return {"receipts": len(self.receipts), "cig": round(self.team_intel.cig(list(self.team_intel._individual.keys())[:3]) if self.team_intel._individual else 0, 3),
                "synergy": round(self.team_intel.synergy(list(self.team_intel._individual.keys())[:3]) if len(self.team_intel._individual) >= 2 else 0, 3)}
