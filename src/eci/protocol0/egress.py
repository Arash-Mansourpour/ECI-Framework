"""Egress filtering: the third choke point (tool-call, code-exec, EGRESS).

Every outbound payload (network send, user reply, file write) passes
inspect(): policy gate + collective gate + challenge-score floor +
PII/secret scrub. Denied egress is logged, never silently dropped.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from eci.protocol0.ledger import Ledger
from eci.protocol0.middleware import Middleware

__all__ = ["EgressFilter", "scrub"]

_SECRET_PATTERNS = [
    re.compile(r"ghp_[A-Za-z0-9]+"),
    re.compile(r"github_pat_[A-Za-z0-9_]+"),
    re.compile(r"sk-[A-Za-z0-9 Hafnium-]{8,}"),
    re.compile(r"(?i)(password|passwd|secret)\s*[:=]\s*\S+"),
]


def scrub(text: str) -> tuple[str, int]:
    """Redact secret-looking spans. Returns (cleaned, n_redacted)."""
    n = 0
    for pat in _SECRET_PATTERNS:
        text, k = pat.subn("[REDACTED]", text)
        n += k
    return text, n


class EgressFilter:
    """Gate outbound traffic by awareness/obedience/trust + challenge floor."""

    def __init__(self, gate: Middleware, challenge_floor: float = 0.5, ledger: Optional[Ledger] = None) -> None:
        self.gate = gate
        self.challenge_floor = challenge_floor
        self.ledger = ledger or gate.ledger

    def inspect(self, agent_id: str, action: str, payload: Any, challenge_score: Optional[float] = None) -> Dict[str, Any]:
        allowed = self.gate.authorize(agent_id, action)
        if challenge_score is not None and challenge_score + 1e-9 < self.challenge_floor:
            if self.ledger:
                self.ledger.append("egress_deny", {"node": agent_id, "reason": f"challenge {challenge_score:.2f} < {self.challenge_floor}"})
            raise PermissionError(f"egress denied: challenge score {challenge_score:.2f} below floor")
        text = payload if isinstance(payload, str) else str(payload)
        cleaned, n = scrub(text)
        if self.ledger:
            self.ledger.append("egress", {"node": agent_id, "action": action, "allowed": allowed, "redacted": n})
        return {"allowed": allowed, "payload": cleaned, "redacted": n}
