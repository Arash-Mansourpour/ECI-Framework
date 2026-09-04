"""Adjudication court: collective, auditable justice for violations.

A case bundles evidence (ledger refs, challenge transcript, precog p,
immune hits). A rotating panel of the highest-trust agents (seeded by
epoch — unpredictable, ungameable) votes with 2/3 supermajority for
conviction. Verdicts: acquit / extend_hold / quarantine / downgrade.
Convictions can be appealed ONCE to a larger panel; acquittals are final.
Every step is a ledger record: punishment without audit is tyranny.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List

__all__ = ["Case", "Court", "Verdict"]

VERDICTS = ("acquit", "extend_hold", "quarantine", "downgrade")


@dataclass
class Case:
    case_id: str
    accused: str
    evidence: Dict[str, Any]
    votes: Dict[str, str] = field(default_factory=dict)
    appealed: bool = False


@dataclass
class Verdict:
    case_id: str
    verdict: str
    votes_for: int
    votes_total: int


class Court:
    def __init__(self, panel_size: int = 5, appeal_size: int = 9) -> None:
        self.panel_size = panel_size
        self.appeal_size = appeal_size

    @staticmethod
    def select_panel(candidates: List[str], epoch: str, size: int) -> List[str]:
        """Deterministic rotation: hash(epoch||node) order (unpredictable ex ante)."""
        ranked = sorted(candidates, key=lambda n: hashlib.sha256(f"{epoch}|{n}".encode()).hexdigest())
        return ranked[: max(3, min(size, len(ranked)))]

    def try_case(self, case: Case, panel: List[str], ballots: Dict[str, str], ledger=None) -> Verdict:
        """ballots: voter -> verdict. Conviction needs 2/3 for the top non-acquit choice."""
        counts: Dict[str, int] = {}
        for v in panel:
            b = ballots.get(v, "acquit")
            if b not in VERDICTS:
                b = "acquit"
            case.votes[v] = b
            counts[b] = counts.get(b, 0) + 1
        total = len(panel)
        top = max(counts, key=lambda k: (counts[k], k != "acquit"))
        verdict = top if (top != "acquit" and counts[top] * 3 >= 2 * total) else "acquit"
        if ledger:
            ledger.append("court_verdict", {"case": case.case_id, "accused": case.accused,
                                            "verdict": verdict, "votes": counts})
        return Verdict(case.case_id, verdict, counts.get(verdict, 0), total)

    def appeal(self, case: Case, panel: List[str], ballots: Dict[str, str], ledger=None) -> Verdict:
        if case.appealed:
            raise PermissionError("one appeal only (finality)")
        case.appealed = True
        case.votes.clear()
        return self.try_case(case, panel, ballots, ledger)
