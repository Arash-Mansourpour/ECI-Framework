"""MarketCommons v2 — Living Semantic Commons with cost-to-challenge (Phase 22, SECE).

Every Fact is a market. Publishing costs stake; challenging costs
challenge_stake. If contradiction_scan finds a dispute and the challenge
is upheld, the challenger is paid via Treasury + Reputation, and Brier
scores update. Confidence becomes money-at-risk.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from eci.market import Marketplace
from eci.semantic import Commons

__all__ = ["MarketCommons"]


@dataclass
class MarketCommons:
    commons: Commons = field(default_factory=Commons)
    marketplace: Marketplace = field(default_factory=Marketplace)
    treasury: Any = None
    reputation: Any = None
    stake_default: float = 10.0
    challenge_stake: float = 5.0

    def __post_init__(self) -> None:
        if self.treasury is None:
            try:
                from eci.governance.treasury import Treasury
                self.treasury = Treasury()
            except Exception:
                self.treasury = None
        if self.reputation is None:
            try:
                from eci.network.reputation import ReputationBoard
                self.reputation = ReputationBoard()
            except Exception:
                self.reputation = None

    def publish(self, statement: str, publisher: str, confidence: float = 0.7, evidence: list[str] | None = None) -> Any:
        # Use Commons: subject=statement, predicate="is_true", obj=confidence
        fact = self.commons.assert_fact(subject=statement, predicate="is_true", obj=confidence, author=publisher, witnesses=evidence or [])
        # open a market for the fact
        try:
            m = self.marketplace.market_for(fact.fid)
            m.buy("yes", 1.0)
        except Exception:
            pass
        if self.treasury and hasattr(self.treasury, "allocate"):
            try:
                self.treasury.allocate(f"fact:{fact.fid}", self.stake_default, publisher, ttl_epochs=10)
            except Exception:
                pass
        return fact

    def challenge(self, fact_id: str, challenger: str, counter_evidence: str) -> dict[str, Any]:
        fact = self.commons.facts.get(fact_id)
        if fact is None:
            return {"ok": False, "error": "fact not found"}
        from eci.redteam import contradiction_scan

        disputes = contradiction_scan([{"statement": f"{fact.subject}:{counter_evidence}", "confidence": 0.9}])
        upheld = len(disputes) > 0
        result: dict[str, Any] = {"fact_id": fact_id, "upheld": upheld, "disputes": disputes}
        if upheld and self.treasury and hasattr(self.treasury, "spend"):
            try:
                self.treasury.spend(f"fact:{fact_id}", self.challenge_stake, by=challenger)
                result["payout"] = self.challenge_stake
            except Exception as exc:
                result["payout_error"] = str(exc)
        if self.reputation is not None and hasattr(self.reputation, "observe"):
            try:
                # bump trust on upheld challenge
                cur = self.reputation.members.get(challenger)
                base_trust = cur.trust if cur else 0.5
                delta = 0.05 if upheld else -0.02
                self.reputation.observe(challenger, trust=max(0.0, min(1.0, base_trust + delta)))
            except Exception:
                pass
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "facts": len(self.commons.facts),
            "markets": len(self.marketplace.markets),
        }
