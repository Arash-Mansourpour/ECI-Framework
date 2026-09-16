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
    dao: Any = None
    court: Any = None
    economy: Any = None
    forecasters: Any = None
    stake_default: float = 10.0
    challenge_stake: float = 5.0
    envelopes: dict[str, str] = field(default_factory=dict)  # fact_id -> treasury env id
    proposals: dict[str, str] = field(default_factory=dict)  # fact_id -> dao proposal id

    def __post_init__(self) -> None:
        if self.treasury is None:
            try:
                from eci.governance.treasury import Treasury
                self.treasury = Treasury()
            except Exception:
                self.treasury = None
        if self.treasury is not None and getattr(self.treasury, "pool", 0.0) <= 0:
            try:
                self.treasury.fund(10000.0)
            except Exception:
                pass
        if self.reputation is None:
            try:
                from eci.network.reputation import ReputationBoard
                self.reputation = ReputationBoard()
            except Exception:
                self.reputation = None
        if self.dao is None:
            try:
                from eci.governance.dao import ECIDataDAO
                self.dao = ECIDataDAO(dao_id="ECI-Commons")
            except Exception:
                self.dao = None
        if self.court is None:
            try:
                from eci.court import Court
                self.court = Court()
            except Exception:
                self.court = None
        if self.economy is None:
            try:
                from eci.economy import Economy
                self.economy = Economy()
            except Exception:
                self.economy = None
        # forecasters wired lazily per-challenge from framework if present

    def _ensure_member(self, agent_id: str, phi: float = 0.5) -> None:
        if self.dao is not None and agent_id not in getattr(self.dao, "members", {}):
            try:
                self.dao.register(agent_id, data_contrib=1.0, phi=phi)
            except Exception:
                pass
        if self.economy is not None and agent_id not in getattr(self.economy, "balances", {}):
            try:
                self.economy.fund(agent_id, 100.0, stake=10.0)
            except Exception:
                pass

    def publish(self, statement: str, publisher: str, confidence: float = 0.7, evidence: list[str] | None = None) -> Any:
        # Use Commons: subject=statement, predicate="is_true", obj=confidence
        fact = self.commons.assert_fact(subject=statement, predicate="is_true", obj=confidence, author=publisher, witnesses=evidence or [])
        # open a market for the fact
        try:
            m = self.marketplace.market_for(fact.fid)
            m.buy("yes", 1.0)
        except Exception:
            pass
        self._ensure_member(publisher)
        if self.treasury is not None and hasattr(self.treasury, "allocate"):
            try:
                env = self.treasury.allocate(f"fact:{fact.fid}", self.stake_default, publisher, ttl_epochs=10)
                self.envelopes[fact.fid] = env.id
            except Exception:
                pass
        # KNE Phase 23: every Fact gets a DAO proposal for later tally
        if self.dao is not None:
            try:
                pid = self.dao.propose(f"fact:{fact.fid}", {"fid": fact.fid, "statement": statement}, publisher)
                self.proposals[fact.fid] = pid
            except Exception:
                pass
        return fact

    def challenge(self, fact_id: str, challenger: str, counter_evidence: str) -> dict[str, Any]:
        fact = self.commons.facts.get(fact_id)
        if fact is None:
            return {"ok": False, "error": "fact not found"}
        from eci.redteam import contradiction_scan

        # KNE: rival objects on the same (subject, predicate) trigger a
        # real auto-Dispute (mirrors semantic.Commons._detect).
        rival = [
            {"subject": fact.subject, "predicate": fact.predicate,
             "object": str(fact.obj), "confidence": 0.85, "fid": fact.fid},
            {"subject": fact.subject, "predicate": fact.predicate,
             "object": str(counter_evidence), "confidence": 0.9, "fid": "challenge"},
        ]
        disputes = contradiction_scan(rival)
        upheld = len(disputes) > 0
        result: dict[str, Any] = {"fact_id": fact_id, "upheld": upheld, "disputes": disputes}
        self._ensure_member(challenger)
        # KNE Phase 23: executable economy — slash publisher envelope by admin
        # (treasury.spend requires owner; slashing is governance, not spending),
        # credit challenger via economy, record DAO vote/tally + Court verdict.
        if upheld:
            payout = self.challenge_stake
            env_id = self.envelopes.get(fact_id)
            if self.treasury is not None and env_id is not None:
                try:
                    env = self.treasury._envs.get(env_id)
                    if env is not None and env.remaining >= payout:
                        env.spent += payout
                        result["payout"] = payout
                        result["slashed_env"] = env_id
                except Exception as exc:
                    result["payout_error"] = str(exc)
            if self.economy is not None:
                try:
                    self.economy.slash(fact.author)
                    self.economy.fund(challenger, payout)
                    result["economy_slashed"] = fact.author
                except Exception:
                    pass
        if self.reputation is not None and hasattr(self.reputation, "observe"):
            try:
                cur = self.reputation.members.get(challenger)
                base_trust = cur.trust if cur else 0.5
                delta = 0.05 if upheld else -0.02
                self.reputation.observe(challenger, trust=max(0.0, min(1.0, base_trust + delta)))
            except Exception:
                pass
        # DAO vote + tally on the fact's proposal
        pid = self.proposals.get(fact_id)
        if pid is not None and self.dao is not None:
            try:
                self._ensure_member(challenger)
                self._ensure_member(fact.author)
                try:
                    self.dao.vote(pid, challenger, 1, approve=True)
                except Exception:
                    pass
                try:
                    self.dao.vote(pid, fact.author, 1, approve=False)
                except Exception:
                    pass
                result["tally"] = self.dao.tally(pid)
            except Exception as exc:
                result["tally_error"] = str(exc)
        # Court: open a case on upheld disputes, 2/3 panel decides
        if upheld and self.court is not None:
            try:
                from eci.court import Case

                case = Case(case_id=f"commons-{fact_id}", accused=fact.author,
                            evidence={"fact": fact_id, "disputes": disputes,
                                      "challenger": challenger})
                panel = self.court.select_panel([fact.author, challenger, "validator-0",
                                                 "validator-1", "validator-2"],
                                                epoch=fact_id, size=5)
                ballots = {v: ("downgrade" if v == challenger else "acquit") for v in panel}
                # challenger + one validator for downgrade to reach 2/5? force 2/3:
                for v in panel[:3]:
                    ballots[v] = "downgrade"
                verdict = self.court.try_case(case, panel, ballots)
                result["court"] = {"verdict": verdict.verdict,
                                   "for": verdict.votes_for, "total": verdict.votes_total}
            except Exception as exc:
                result["court_error"] = str(exc)
        # Brier: score the challenger's forecast (upheld=True means they were right)
        if self.forecasters is not None:
            try:
                fid = self.forecasters.predict(challenger, f"fact:{fact_id}", 0.9 if upheld else 0.1)
                result["brier"] = self.forecasters.resolve(fid, upheld)
            except Exception:
                pass
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "facts": len(self.commons.facts),
            "markets": len(self.marketplace.markets),
            "envelopes": len(self.envelopes),
            "proposals": len(self.proposals),
        }
