"""ECI-TRUTH — Epistemic Core: Evidence Keeper + Truth Guardian.

Separation of generation/evaluation (Smith's veto-grade guardian).
Confidence levels: CONFIRMED/HIGH/PROVISIONAL/DISPUTED/LOW/REJECTED
Provenance: every claim has source, evidence, counter-evidence, dependencies.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

__all__ = ["ConfidenceLevel", "Claim", "EvidenceKeeper", "TruthGuardian"]


class ConfidenceLevel(str, Enum):
    CONFIRMED = "confirmed"
    HIGH = "high"
    PROVISIONAL = "provisional"
    DISPUTED = "disputed"
    LOW = "low"
    REJECTED = "rejected"


@dataclass
class Claim:
    statement: str
    source: str
    evidence: list[str] = field(default_factory=list)
    counter_evidence: list[str] = field(default_factory=list)
    confidence: float = 0.5
    level: ConfidenceLevel = ConfidenceLevel.PROVISIONAL
    provenance: dict[str, Any] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    ts: float = field(default_factory=time.time)

    def update_confidence(self, supporting: int = 0, counter: int = 0) -> ConfidenceLevel:
        total = len(self.evidence) + supporting + len(self.counter_evidence) + counter
        if total == 0:
            self.level = ConfidenceLevel.PROVISIONAL
            return self.level
        ratio = (len(self.evidence) + supporting) / total
        self.confidence = 0.5 + 0.5 * (ratio - 0.5) * 2  # 0..1
        if ratio >= 0.9 and total >= 5:
            self.level = ConfidenceLevel.CONFIRMED
        elif ratio >= 0.7:
            self.level = ConfidenceLevel.HIGH
        elif 0.4 <= ratio < 0.7:
            self.level = ConfidenceLevel.PROVISIONAL
        elif 0.2 <= ratio < 0.4:
            self.level = ConfidenceLevel.DISPUTED
        elif ratio < 0.2:
            self.level = ConfidenceLevel.REJECTED
        else:
            self.level = ConfidenceLevel.LOW
        return self.level


class EvidenceKeeper:
    def __init__(self) -> None:
        self.claims: dict[str, Claim] = {}

    def assert_claim(self, statement: str, source: str, evidence: list[str] | None = None) -> Claim:
        claim = Claim(statement=statement, source=source, evidence=evidence or [],
                      provenance={"asserted_at": time.time(), "source": source})
        self.claims[claim.id] = claim
        return claim

    def add_evidence(self, claim_id: str, evidence: str, supporting: bool = True) -> Claim:
        claim = self.claims[claim_id]
        if supporting:
            claim.evidence.append(evidence)
        else:
            claim.counter_evidence.append(evidence)
        claim.update_confidence()
        return claim

    def to_dict(self) -> dict[str, Any]:
        return {k: {"statement": v.statement, "level": v.level.value, "confidence": round(v.confidence, 2),
                    "evidence": len(v.evidence), "counter": len(v.counter_evidence)} for k, v in self.claims.items()}


class TruthGuardian:
    """Veto-grade evaluator: separate from generator, can refuse/revise."""

    def evaluate(self, claim: Claim, threshold: float = 0.6) -> dict[str, Any]:
        if claim.confidence >= threshold and claim.level not in (ConfidenceLevel.REJECTED, ConfidenceLevel.DISPUTED):
            return {"verdict": "supported", "emit": True, "claim_id": claim.id}
        if claim.level == ConfidenceLevel.DISPUTED:
            return {"verdict": "disputed", "emit": False, "action": "revise_or_refuse", "claim_id": claim.id}
        return {"verdict": "unsupported", "emit": False, "action": "revise_or_refuse", "claim_id": claim.id}

    def veto(self, claim: Claim) -> dict[str, Any]:
        return {"verdict": "vetoed", "emit": False, "claim_id": claim.id}
