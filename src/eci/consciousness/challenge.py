"""Challenge-response awareness: prove it, don't claim it.

The network issues unpredictable probes (calibration targets + noise
discrimination + range holds); the agent must respond within tolerance.
Score = fraction passed with difficulty weighting. Unlike self-reported
awareness_index, a challenge transcript is *evidence*: seeded, replayable,
and auditable in the ledger.

Flow: issue(seed, n) -> challenges -> respond(agent_fn) -> verdict.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Tuple

__all__ = ["Challenge", "Transcript", "issue", "grade"]


@dataclass
class Challenge:
    kind: str  # "hold" | "discriminate" | "repeat"
    target: float
    tolerance: float
    difficulty: float  # weight in final score
    nonce: str = ""


@dataclass
class Transcript:
    challenges: List[Challenge] = field(default_factory=list)
    responses: List[float] = field(default_factory=list)
    passed: List[bool] = field(default_factory=list)

    def score(self) -> float:
        if not self.challenges:
            return 0.0
        w = [c.difficulty for c in self.challenges]
        return sum(wi for wi, p in zip(w, self.passed) if p) / sum(w)


def issue(n: int = 8, seed: int | None = None) -> List[Challenge]:
    """Issue n unpredictable challenges (seeded when given, secret otherwise)."""
    import random as _r

    rng = _r.Random(seed) if seed is not None else _r.Random(secrets.token_hex(8))
    kinds = ["hold", "discriminate", "repeat"]
    out = []
    for _ in range(n):
        kind = rng.choice(kinds)
        target = round(rng.uniform(0.0, 1.0), 3)
        tol = {"hold": 0.15, "discriminate": 0.1, "repeat": 0.2}[kind]
        diff = {"hold": 1.0, "discriminate": 1.5, "repeat": 0.75}[kind]
        out.append(Challenge(kind, target, tol, diff, nonce=secrets.token_hex(6)))
    return out


def grade(challenges: List[Challenge], respond: Callable[[Challenge], float]) -> Transcript:
    t = Transcript()
    for c in challenges:
        try:
            r = float(respond(c))
            ok = abs(r - c.target) <= c.tolerance
        except Exception:  # noqa: BLE001 — non-response is a failure
            r, ok = float("nan"), False
        t.challenges.append(c)
        t.responses.append(r)
        t.passed.append(ok)
    return t


def to_dict(t: Transcript) -> Dict:
    return {
        "score": t.score(), "n": len(t.challenges),
        "passed": sum(t.passed),
        "detail": [(c.kind, c.target, r, p) for c, r, p in zip(t.challenges, t.responses, t.passed)],
    }
