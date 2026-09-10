"""Drift detection: PSI + KS-style distance over binned distributions.

Used by neural cortex / QNN loop / semantic commons to decide when a
model, channel or commons fact needs retraining, quarantine or dispute.
Stdlib-only so it runs on edge profiles.
"""

from __future__ import annotations

import math
from typing import Dict, List, Sequence

__all__ = ["psi", "ks_distance", "drift_report"]


def _hist(x: Sequence[float], bins: int = 10, lo: float | None = None, hi: float | None = None) -> List[float]:
    xs = list(x)
    if not xs:
        return [0.0] * bins
    lo = min(xs) if lo is None else lo
    hi = max(xs) if hi is None else hi
    if hi <= lo:
        hi = lo + 1e-9
    counts = [0] * bins
    for v in xs:
        i = min(bins - 1, max(0, int((v - lo) / (hi - lo) * bins)))
        counts[i] += 1
    n = len(xs)
    return [c / n for c in counts]


def psi(expected: Sequence[float], actual: Sequence[float], bins: int = 10) -> float:
    lo = min([*expected, *actual]) if expected and actual else 0.0
    hi = max([*expected, *actual]) if expected and actual else 1.0
    pe = _hist(expected, bins, lo, hi)
    pa = _hist(actual, bins, lo, hi)
    total = 0.0
    for e, a in zip(pe, pa):
        e = max(e, 1e-6)
        a = max(a, 1e-6)
        total += (a - e) * math.log(a / e)
    return total


def ks_distance(a: Sequence[float], b: Sequence[float]) -> float:
    sa, sb = sorted(a), sorted(b)
    if not sa or not sb:
        return 0.0
    grid = sorted(set(sa) | set(sb))
    import bisect
    best = 0.0
    for g in grid:
        fa = bisect.bisect_right(sa, g) / len(sa)
        fb = bisect.bisect_right(sb, g) / len(sb)
        best = max(best, abs(fa - fb))
    return best


def drift_report(expected: Sequence[float], actual: Sequence[float]) -> Dict[str, object]:
    p = psi(expected, actual)
    k = ks_distance(expected, actual)
    level = "none" if p < 0.1 and k < 0.1 else ("watch" if p < 0.25 and k < 0.2 else "drift")
    return {"psi": p, "ks": k, "level": level,
            "retrain": bool(level == "drift")}
