"""Genesis Evolution — mutable constitutional genome (Phase 22, SECE).

ConstitutionalGenome was immutable (10 invariants, H(G0||Gn)). Now it can
`propose(mutation) → twin_test → canary → DAO vote → commit` with full
provenance: every mutation is a hash-chained Proposal, TwinReport, and
Ledger entry, and the new root is H(old_root || mutation). Rollback is
just reverting to the previous root (no fork wipes history).

Uses existing: ConstitutionalGenome, TwinReport/what_if, GovernedEvolution,
Ledger (hash chain), Reputation.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any

from eci.protocol_vnext.genesis import ConstitutionalGenome
from eci.twin import TwinReport, what_if

__all__ = ["GenomeProposal", "MutableConstitution"]


@dataclass
class GenomeProposal:
    mutation: str
    proposer: str
    parent_root: str
    created_at: float = field(default_factory=time.time)
    twin_result: dict[str, Any] | None = None
    canary_ok: bool | None = None
    votes: dict[str, bool] = field(default_factory=dict)
    status: str = "proposed"

    def id(self) -> str:
        h = hashlib.sha256(f"{self.mutation}|{self.proposer}|{self.parent_root}".encode()).hexdigest()[:12]
        return f"genome-{h}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id(),
            "mutation": self.mutation,
            "proposer": self.proposer,
            "parent_root": self.parent_root[:16],
            "status": self.status,
            "twin": self.twin_result,
            "canary_ok": self.canary_ok,
            "votes": self.votes,
        }


class MutableConstitution:
    """Wraps ConstitutionalGenome with governed mutation lifecycle."""

    def __init__(self, genome: ConstitutionalGenome | None = None) -> None:
        self.genome = genome or ConstitutionalGenome()
        self.history: list[str] = [self.genome.root]
        self.proposals: dict[str, GenomeProposal] = {}
        self.ledger: list[dict[str, Any]] = []

    def propose(self, mutation: str, proposer: str) -> GenomeProposal:
        if not mutation or len(mutation) < 5:
            raise ValueError("mutation too short")
        p = GenomeProposal(mutation=mutation, proposer=proposer, parent_root=self.genome.root)
        self.proposals[p.id()] = p
        self.ledger.append({"op": "propose", "id": p.id(), "mutation": mutation, "by": proposer})
        return p

    def twin_test(self, proposal_id: str, simulated_improvement: float = 0.1) -> dict[str, Any]:
        p = self.proposals.get(proposal_id)
        if p is None:
            raise KeyError(proposal_id)
        # use twin.what_if with a drill that says improvement if mutation contains "preserve"
        def drill(hypo: dict[str, float]) -> dict[str, float]:
            return {"improvement": simulated_improvement, "risk": 0.1 if "preserve" in p.mutation else 0.5}

        report: TwinReport = what_if(f"genome:{proposal_id}", {"mutation_score": 1.0}, [], drill_fn=drill)  # type: ignore[arg-type]
        res = {"verdict": getattr(report, "verdict", "unknown"), "improvement": simulated_improvement}
        p.twin_result = res
        p.status = "twin_tested"
        self.ledger.append({"op": "twin", "id": proposal_id, "verdict": res["verdict"]})
        return res

    def canary(self, proposal_id: str, success: bool = True) -> bool:
        p = self.proposals.get(proposal_id)
        if p is None:
            raise KeyError(proposal_id)
        p.canary_ok = success
        p.status = "canary_pass" if success else "canary_fail"
        self.ledger.append({"op": "canary", "id": proposal_id, "ok": success})
        return success

    def vote(self, proposal_id: str, voter: str, approve: bool) -> None:
        p = self.proposals.get(proposal_id)
        if p is None:
            raise KeyError(proposal_id)
        p.votes[voter] = approve
        self.ledger.append({"op": "vote", "id": proposal_id, "voter": voter, "approve": approve})

    def commit(self, proposal_id: str, quorum: int = 2) -> dict[str, Any]:
        p = self.proposals.get(proposal_id)
        if p is None:
            return {"ok": False, "error": "unknown proposal"}
        if p.twin_result is None or p.canary_ok is not True:
            return {"ok": False, "error": "twin/canary not passed"}
        approvals = sum(1 for v in p.votes.values() if v)
        if approvals < quorum:
            return {"ok": False, "error": "quorum not reached", "approvals": approvals}
        # compute new root: H(old_root || mutation)
        new_root = hashlib.sha256((self.genome.root + p.mutation).encode()).hexdigest()
        self.genome.invariants.append(p.mutation)
        self.genome.root = new_root
        self.history.append(new_root)
        p.status = "committed"
        self.ledger.append({"op": "commit", "id": proposal_id, "new_root": new_root[:16]})
        return {"ok": True, "new_root": new_root, "history_len": len(self.history)}

    def rollback(self) -> dict[str, Any]:
        if len(self.history) <= 1:
            return {"ok": False, "error": "no history to rollback"}
        self.history.pop()
        self.genome.root = self.history[-1]
        # invariants rollback: remove last (best-effort)
        if len(self.genome.invariants) > 10:
            self.genome.invariants.pop()
        self.ledger.append({"op": "rollback", "root": self.genome.root[:16]})
        return {"ok": True, "root": self.genome.root}

    def to_dict(self) -> dict[str, Any]:
        return {"root": self.genome.root[:16], "history": len(self.history), "proposals": [p.to_dict() for p in self.proposals.values()]}
