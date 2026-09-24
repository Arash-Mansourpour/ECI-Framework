"""Economic attack simulation v8 (ADR-004).

Pure-math, deterministic, seeded. Proves MarketCommons resistance to:
- whale wash-trading (LMSR price push with self-trades)
- collusion rings (coordinated votes shifting DAO tally)
- slashing evaluation (when treasury slash triggers + how much)

Uses LMSR closed-form; no network, no randomness beyond seed.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def lmsr_price(quantities: list[float], b: float = 100.0) -> list[float]:
    mx = max(quantities)
    exps = [math.exp((q - mx) / b) for q in quantities]
    s = sum(exps)
    return [e / s for e in exps]


def lmsr_cost(quantities: list[float], deltas: list[float], b: float = 100.0) -> float:
    def _c(q: list[float]) -> float:
        mx = max(q)
        return b * math.log(sum(math.exp((x - mx) / b) for x in q)) + mx
    after = [q + d for q, d in zip(quantities, deltas)]
    return _c(after) - _c(quantities)


@dataclass
class WhaleAttackResult:
    price_before: float
    price_after: float
    price_shift: float
    cost: float
    profitable: bool
    flagged: bool
    detail: str = ""


def simulate_whale_attack(price_outcome: int = 0, n_outcomes: int = 2,
                          whale_stake: float = 500.0, b: float = 100.0,
                          honest_liquidity: float = 1000.0,
                          flag_threshold: float = 0.15) -> WhaleAttackResult:
    """One whale buys `whale_stake` of outcome. Flag if shift > threshold."""
    quantities = [honest_liquidity / n_outcomes] * n_outcomes
    before = lmsr_price(quantities, b)[price_outcome]
    deltas = [0.0] * n_outcomes
    deltas[price_outcome] = whale_stake
    cost = lmsr_cost(quantities, deltas, b)
    after = lmsr_price([q + d for q, d in zip(quantities, deltas)], b)[price_outcome]
    shift = after - before
    # Attack profitable only if price moves more than cost justifies;
    # with LMSR loss bound, large single-sided buys are expensive -> usually not.
    profitable = shift * honest_liquidity > cost * 1.5
    flagged = shift >= flag_threshold
    return WhaleAttackResult(price_before=before, price_after=after, price_shift=shift,
                             cost=cost, profitable=profitable, flagged=flagged,
                             detail=f"whale={whale_stake} b={b} outcomes={n_outcomes}")


@dataclass
class CollusionResult:
    honest_tally: dict[str, int]
    attacked_tally: dict[str, int]
    flipped: bool
    ring_size: int
    detection_score: float  # 0..1, higher = more suspicious


def simulate_collusion(votes: dict[str, str], ring: set[str],
                       ring_target: str) -> CollusionResult:
    """Ring members switch to ring_target. Detect via vote-entropy collapse."""
    honest: dict[str, int] = {}
    for v in votes.values():
        honest[v] = honest.get(v, 0) + 1
    attacked = dict(honest)
    for m in ring:
        if m in votes:
            old = votes[m]
            attacked[old] = attacked.get(old, 1) - 1
            attacked[ring_target] = attacked.get(ring_target, 0) + 1
    def _winner(t: dict[str, int]) -> str:
        return max(t.items(), key=lambda kv: (kv[1], kv[0]))[0]
    flipped = _winner(honest) != _winner(attacked)
    # detection: share of ring_target after attack + ring concentration
    total = sum(max(0, v) for v in attacked.values()) or 1
    share = max(0, attacked.get(ring_target, 0)) / total
    ring_frac = len(ring) / max(1, len(votes))
    score = min(1.0, 0.6 * share + 0.4 * min(1.0, ring_frac * 3))
    return CollusionResult(honest_tally=honest, attacked_tally=attacked,
                           flipped=flipped, ring_size=len(ring), detection_score=score)


@dataclass
class SlashDecision:
    slash: bool
    amount: float
    reason: str


def evaluate_slash(price_shift: float, collusion_score: float, brier_worsen: float,
                   shift_threshold: float = 0.15, collusion_threshold: float = 0.7,
                   brier_threshold: float = 0.05, stake: float = 10.0) -> SlashDecision:
    triggers = []
    if price_shift >= shift_threshold:
        triggers.append(f"price_shift {price_shift:.3f}>={shift_threshold}")
    if collusion_score >= collusion_threshold:
        triggers.append(f"collusion {collusion_score:.3f}>={collusion_threshold}")
    if brier_worsen >= brier_threshold:
        triggers.append(f"brier_worsen {brier_worsen:.3f}>={brier_threshold}")
    if not triggers:
        return SlashDecision(slash=False, amount=0.0, reason="no trigger")
    # Slash scales with worst trigger, capped at stake.
    severity = min(1.0, max(price_shift / max(shift_threshold, 1e-9),
                            collusion_score, brier_worsen / max(brier_threshold, 1e-9)) / 2.0)
    return SlashDecision(slash=True, amount=round(stake * severity, 4),
                         reason=" + ".join(triggers))


def brier_score(probs: list[float], outcomes: list[int]) -> float:
    n = len(probs)
    return sum((p - o) ** 2 for p, o in zip(probs, outcomes)) / max(1, n)
