"""Verification gate (P0-2): no claim enters the ledger without a green verifier.

MLReplicate-style reproducibility: a Claim carries an executable verifier;
the gate runs it (seeded, budgeted) and the verdict BLOCKS admission.
Falsification evidence from redteam attaches to the verdict either way.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

__all__ = ["Claim", "VerificationGate", "Verdict"]


@dataclass
class Claim:
    id: str
    statement: str
    verifier: Callable[[], dict[str, Any]]
    context: dict[str, Any] = field(default_factory=dict)
    submitted_at: float = field(default_factory=time.time)


@dataclass
class Verdict:
    claim_id: str
    admitted: bool
    checks: dict[str, Any]
    falsifiers: list[str] = field(default_factory=list)
    elapsed_s: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {"claim_id": self.claim_id, "admitted": self.admitted,
                "checks": self.checks, "falsifiers": self.falsifiers,
                "elapsed_s": round(self.elapsed_s, 4)}


class VerificationGate:
    """Blocking admission control for ledger claims."""

    def __init__(self, budget_s: float = 30.0) -> None:
        self.budget_s = budget_s
        self.verdicts: list[Verdict] = []
        self.admitted_ids: set[str] = set()

    def _falsify(self, claim: Claim) -> list[str]:
        try:
            from eci.redteam import Challenger

            ch = Challenger(seed=hash(claim.id) % (2 ** 31))
            probes = ch.falsify(claim.statement, str(claim.context.get("domain", "")))
            return [str(getattr(p, "prompt", p))[:120] for p in probes[:3]]
        except Exception:  # noqa: BLE001
            return []

    def evaluate(self, claim: Claim) -> Verdict:
        t0 = time.time()
        falsifiers = self._falsify(claim)
        try:
            raw = claim.verifier()
            ok = bool(raw.get("ok", False)) if isinstance(raw, dict) else bool(raw)
            checks = raw if isinstance(raw, dict) else {"ok": ok}
        except Exception as exc:  # noqa: BLE001
            ok, checks = False, {"ok": False, "error": repr(exc)[:200]}
        elapsed = time.time() - t0
        if elapsed > self.budget_s:
            ok = False
            checks = {**checks, "ok": False, "over_budget": True}
        verdict = Verdict(claim_id=claim.id, admitted=ok, checks=checks,
                          falsifiers=falsifiers, elapsed_s=elapsed)
        self.verdicts.append(verdict)
        if ok:
            self.admitted_ids.add(claim.id)
        return verdict

    def admitted(self, claim_id: str) -> bool:
        return claim_id in self.admitted_ids

    def admission_rate(self) -> float:
        if not self.verdicts:
            return 0.0
        return sum(1 for v in self.verdicts if v.admitted) / len(self.verdicts)

    def to_dict(self) -> dict[str, Any]:
        return {"evaluated": len(self.verdicts), "admitted": len(self.admitted_ids),
                "admission_rate": round(self.admission_rate(), 4)}
