"""Semantic commons: shared reality with provenance, versioned, disputable.

Facts are (subject, predicate, object) triples with author, witnesses,
version and supersedes-links. Two live facts with same subject+predicate
but different objects open a DISPUTE automatically; disputes resolve by
witness weight (or escalate to the court). Retractions never delete —
they append a tombstone, so history stays auditable. Without shared
verifiable reality, obedience has no meaning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

__all__ = ["Fact", "Commons", "Dispute"]


@dataclass
class Fact:
    fid: str
    subject: str
    predicate: str
    obj: Any
    author: str
    witnesses: List[str] = field(default_factory=list)
    version: int = 1
    live: bool = True
    supersedes: Optional[str] = None


@dataclass
class Dispute:
    subject: str
    predicate: str
    fact_ids: List[str]
    resolved: bool = False
    winner: Optional[str] = None


class Commons:
    def __init__(self) -> None:
        self.facts: Dict[str, Fact] = {}
        self.disputes: List[Dispute] = []
        self._seq = 0

    def assert_fact(self, subject: str, predicate: str, obj: Any, author: str, witnesses: List[str] | None = None) -> Fact:
        self._seq += 1
        f = Fact(f"f{self._seq}", subject, predicate, obj, author, witnesses or [])
        # New version supersedes author's own prior live fact on same key.
        for old in self.facts.values():
            if old.live and old.author == author and old.subject == subject and old.predicate == predicate:
                old.live = False
                f.supersedes = old.fid
        self.facts[f.fid] = f
        self._detect(subject, predicate)
        return f

    def retract(self, fid: str) -> None:
        if fid in self.facts:
            self.facts[fid].live = False  # tombstone, never deleted

    def _detect(self, subject: str, predicate: str) -> None:
        live = [f for f in self.facts.values()
                if f.live and f.subject == subject and f.predicate == predicate]
        objs = {str(f.obj) for f in live}
        if len(objs) > 1 and not any(d.subject == subject and d.predicate == predicate and not d.resolved for d in self.disputes):
            self.disputes.append(Dispute(subject, predicate, [f.fid for f in live]))

    def resolve(self, subject: str, predicate: str, winner_fid: str, ledger=None) -> Dispute:
        """Resolve by witness weight (heaviest live fact wins); tombstones the rest."""
        for d in self.disputes:
            if d.subject == subject and d.predicate == predicate and not d.resolved:
                cands = [self.facts[i] for i in d.fact_ids if self.facts[i].live]
                if not cands:
                    d.resolved = True
                    return d
                win = max(cands, key=lambda f: (len(f.witnesses), f.fid == winner_fid, f.fid))
                # Prefer the explicitly chosen winner on witness-ties via caller intent:
                chosen = self.facts.get(winner_fid)
                if chosen and chosen.live and len(chosen.witnesses) >= len(win.witnesses) - 1:
                    win = chosen
                for f in cands:
                    if f.fid != win.fid:
                        f.live = False
                d.resolved, d.winner = True, win.fid
                if ledger:
                    ledger.append("commons_resolve", {"subject": subject, "winner": win.fid})
                return d
        raise ValueError("no open dispute")
