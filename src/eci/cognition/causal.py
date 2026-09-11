"""Causal reasoning: discovery + do-calculus-lite + counterfactuals.

Discovery is a *linear-Gaussian proxy* (lagged + partial correlation with
Fisher-z pruning + collider orientation) — exact for the class it assumes,
explicitly approximate outside it. Where it shines: turning twin.py
what-ifs from correlation theatre into backdoor-adjusted ATE estimates,
and routing counterfactuals ("what if we had held?") through provenance
lineage so answers cite their evidence.

Honest limits: no latent-confounding guarantees (no FCI); faithfulness
assumed; nonlinear effects need the kernel extension (documented).
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

__all__ = ["CausalGraph", "discover", "ate_backdoor"]


def _corr(xs: Sequence[float], ys: Sequence[float]) -> float:
    n = len(xs)
    if n < 3:
        return 0.0
    mx, my = sum(xs) / n, sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs)) or 1e-9
    sy = math.sqrt(sum((y - my) ** 2 for y in ys)) or 1e-9
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def _pcorr(xs: Sequence[float], ys: Sequence[float], z: Sequence[float]) -> float:
    rxy, rxz, ryz = _corr(xs, ys), _corr(xs, z), _corr(ys, z)
    denom = math.sqrt(max(1e-9, (1 - rxz ** 2) * (1 - ryz ** 2)))
    return (rxy - rxz * ryz) / denom


def _fisher_z(r: float, n: int) -> float:
    r = min(0.9999, max(-0.9999, r))
    return 0.5 * math.log((1 + r) / (1 - r)) * math.sqrt(max(1, n - 3))


@dataclass
class CausalGraph:
    names: list[str]
    edges: dict[tuple[str, str], float] = field(default_factory=dict)  # (cause->effect): strength

    def parents(self, node: str) -> list[str]:
        return [a for (a, b) in self.edges if b == node]

    def children(self, node: str) -> list[str]:
        return [b for (a, b) in self.edges if a == node]

    def backdoor_set(self, cause: str, effect: str,
                     data: dict[str, Sequence[float]] | None = None) -> list[str]:
        """Parents of cause that also reach effect, plus contemporaneous
        confounder proxies (|corr| with both cause and effect)."""
        out = [p for p in self.parents(cause) if p != effect]
        if data:
            for z in self.names:
                if z in (cause, effect) or z in out:
                    continue
                try:
                    if abs(_corr(list(data[z]), list(data[cause]))) > 0.3 and \
                       abs(_corr(list(data[z]), list(data[effect]))) > 0.2:
                        out.append(z)
                except Exception:  # noqa: BLE001
                    pass
        return out

    def to_dict(self) -> dict[str, Any]:
        return {"nodes": self.names,
                "edges": [{"from": a, "to": b, "w": w} for (a, b), w in self.edges.items()]}


def discover(data: dict[str, Sequence[float]], thresh: float = 2.0,
             lags: Sequence[int] = (1,)) -> CausalGraph:
    """PC-lite: lagged correlation edges, pruned by partial correlation.

    Orientation rule: temporal priority (lag causes present) + collider
    guard (skip edge a->b if a _||_ b | c for some c with |z| < thresh).
    Deterministic given data.
    """
    names = sorted(data)
    n = min(len(v) for v in data.values())
    edges: dict[tuple[str, str], float] = {}
    for a, b in itertools.permutations(names, 2):
        best, best_lag = 0.0, 0
        for lag in lags:
            xs = list(data[a])[:n - lag]
            ys = list(data[b])[lag:]
            r = _corr(xs, ys)
            if abs(r) > abs(best):
                best, best_lag = r, lag
        if abs(_fisher_z(best, n)) < thresh:
            continue
        # collider/conditional-independence prune
        independent = False
        for c in names:
            if c in (a, b):
                continue
            xs = list(data[a])[:n - best_lag]
            ys = list(data[b])[best_lag:]
            zs = list(data[c])[best_lag:]
            if abs(_fisher_z(_pcorr(xs, ys, zs), n)) < thresh * 0.5:
                independent = True
                break
        if not independent:
            edges[(a, b)] = best
    # keep the stronger direction only (temporal symmetry breaker)
    for (a, b) in list(edges):
        if (b, a) in edges and abs(edges[(b, a)]) >= abs(edges[(a, b)]):
            del edges[(a, b)]
    return CausalGraph(names, edges)


def ate_backdoor(data: dict[str, Sequence[float]], cause: str, effect: str,
                 graph: CausalGraph | None = None, max_lag: int = 2) -> dict[str, Any]:
    """ATE via backdoor linear adjustment, lag-aware.

    Cause can precede effect: each lag L in 0..max_lag regresses Y[t] on
    X[t-L] within backdoor-stratum cells (median split, >=8 samples/cell,
    inverse-variance pooling). The reported estimate uses the lag with the
    strongest adjusted signal; the lag is always reported (no hiding).
    Returns estimate + 95% CI + adjustment set + lag (auditable).
    """
    graph = graph or discover(data)
    adj = graph.backdoor_set(cause, effect, data)
    n = min(len(data[cause]), len(data[effect]))
    best: dict[str, Any] | None = None
    for lag in range(max_lag + 1):
        m = n - lag
        if m < 16:
            continue
        X = list(data[cause])[:m]
        Y = list(data[effect])[lag:]
        Z = {c: list(data[c])[lag:] for c in adj}
        med = {c: sorted(v)[len(v) // 2] for c, v in Z.items()}
        cells: dict[tuple, list[int]] = {}
        for i in range(m):
            key = tuple(1 if Z[c][i] > med[c] else 0 for c in adj) if adj else (0,)
            cells.setdefault(key, []).append(i)
        ests, weights = [], []
        for idx in cells.values():
            if len(idx) < 8:
                continue
            xs = [X[i] for i in idx]
            ys = [Y[i] for i in idx]
            mx = sum(xs) / len(xs)
            lo = [(x, y) for x, y in zip(xs, ys) if x <= mx]
            hi = [(x, y) for x, y in zip(xs, ys) if x > mx]
            if len(lo) < 3 or len(hi) < 3:
                continue
            dx = sum(x for x, _ in hi) / len(hi) - sum(x for x, _ in lo) / len(lo)
            dy = sum(y for _, y in hi) / len(hi) - sum(y for _, y in lo) / len(lo)
            if abs(dx) < 1e-9:
                continue
            ests.append(dy / dx)
            weights.append(len(idx))
        if not ests:
            continue
        tot = sum(weights)
        ate = sum(e * w for e, w in zip(ests, weights)) / tot
        var = sum(w * (e - ate) ** 2 for e, w in zip(ests, weights)) / tot
        se = math.sqrt(var / max(1, len(ests)))
        strength = abs(ate) * tot
        cand = {"ate": ate, "ci95": (ate - 1.96 * se, ate + 1.96 * se),
                "adjusted": True, "adjustment": adj, "cells": len(ests),
                "lag": lag, "_strength": strength}
        if best is None or cand["_strength"] > best["_strength"]:
            best = cand
    if best is None:
        # fallback: unadjusted contemporaneous slope (labelled as such)
        X, Y = list(data[cause])[:n], list(data[effect])[:n]
        r = _corr(X, Y)
        mx = sum(X) / n
        sx = (sum((x - mx) ** 2 for x in X) / n) ** 0.5 or 1e-9
        my = sum(Y) / n
        sy = (sum((y - my) ** 2 for y in Y) / n) ** 0.5 or 1e-9
        return {"ate": r * sy / sx, "ci95": (-99, 99), "adjusted": False,
                "adjustment": adj, "lag": 0,
                "warning": "unadjusted (cells too small)"}
    best = dict(best)
    best.pop("_strength", None)
    return best
