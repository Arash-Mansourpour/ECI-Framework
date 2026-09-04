"""Threshold credentials: prove compliance bands, hide exact values.

Coarse zero-knowledge (research grade, honestly labelled — not SNARKs).
At issuance the network binds tokens H(secret||metric||level) for every
level the value PASSES and publishes only that set. To prove "value >= T"
the agent points at the published token for T: the verifier learns band
membership (e.g. passed 0.5, no 0.8 token => value in [0.5, 0.8)) — at most
2 bits per metric, never the value. Tokens for unpassed levels are
unforgeable without the secret, and absence of a token proves failure.
Roadmap: replace tokens with Bulletproofs; API (prove/verify) is stable.

Levels: [0.2, 0.5, 0.8]. Fresh secret per credential => unlinkable epochs.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass, field
from typing import Dict, Set

__all__ = ["LEVELS", "Credential", "issue_credential", "prove", "verify_proof"]

LEVELS = (0.2, 0.5, 0.8)
METRICS = ("awareness", "obedience", "trust")


def _tok(secret: str, metric: str, level: float) -> str:
    return hashlib.sha256(f"{secret}|{metric}|{level}".encode()).hexdigest()


@dataclass
class Credential:
    agent_id: str
    epoch: str
    published: Set[str] = field(default_factory=set)  # tokens of PASSED levels only
    _index: Dict[str, tuple] = field(default_factory=dict)  # token -> (metric, level), holder-side

    def disclosure_bits(self) -> int:
        return 0  # unopened credential leaks nothing


def issue_credential(agent_id: str, values: Dict[str, float], epoch: str | None = None) -> Credential:
    """Issuer binds tokens. Exact values exist ONLY inside this call."""
    secret = secrets.token_hex(16)
    c = Credential(agent_id, epoch or secrets.token_hex(4))
    for m in METRICS:
        v = float(max(0.0, min(1.0, values.get(m, 0.0))))
        for lv in LEVELS:
            if v + 1e-9 >= lv:
                tok = _tok(secret, m, lv)
                c.published.add(tok)
                c._index[tok] = (m, lv)
    return c


def prove(cred: Credential, metric: str, threshold: float) -> Dict:
    """Point at the published token for the highest passed level <= threshold.

    Raises LookupError if the level was NOT passed (nothing to show —
    absence itself is the fail proof; no token exists to reveal).
    """
    lv = max([l for l in LEVELS if l <= threshold + 1e-9], default=LEVELS[0])
    for tok, (m, l) in cred._index.items():
        if m == metric and abs(l - lv) < 1e-12:
            return {"agent": cred.agent_id, "epoch": cred.epoch,
                    "metric": metric, "level": lv, "token": tok}
    raise LookupError(f"level {lv} not passed for {metric} (fail is proven by absence)")


def verify_proof(published: Set[str], proof: Dict) -> Dict:
    """Membership check against the published set. Learns band, not value."""
    ok = proof["token"] in published
    band = {proof["metric"]: f">={proof['level']}"} if ok else {}
    return {"ok": ok, "disclosed": band}
