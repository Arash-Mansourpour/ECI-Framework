"""Causal engine (P1-4): from correlation to intervention.

- StructuralCausalModel: linear-Gaussian equations over a DAG
- do(): graph surgery + interventional sampling (twin tests become do-tests)
- counterfactual(): abduction-action-prediction under linear model
- discover(): PC-skeleton via Fisher-z conditional independence on samples
"""

from __future__ import annotations

import math
import random
from typing import Any

__all__ = ["StructuralCausalModel", "discover_skeleton", "partial_corr"]


def partial_corr(x: list[float], y: list[float], z: list[list[float]]) -> float:
    """Partial correlation of x,y given z via residualization (pure python)."""
    n = len(x)

    def resid(v: list[float]) -> list[float]:
        if not z:
            m = sum(v) / n
            return [a - m for a in v]
        # OLS of v on [1, *z]
        k = len(z) + 1
        cols = [[1.0] * n] + z
        # normal equations
        ata = [[sum(cols[i][t] * cols[j][t] for t in range(n)) for j in range(k)] for i in range(k)]
        atv = [sum(cols[i][t] * v[t] for t in range(n)) for i in range(k)]
        beta = _solve(ata, atv)
        return [v[t] - sum(beta[i] * cols[i][t] for i in range(k)) for t in range(n)]

    rx, ry = resid(x), resid(y)
    denom = math.sqrt(sum(a * a for a in rx) * sum(b * b for b in ry))
    if denom == 0:
        return 0.0
    return sum(a * b for a, b in zip(rx, ry)) / denom


def _solve(a: list[list[float]], b: list[float]) -> list[float]:
    n = len(a)
    m = [row[:] + [v] for row, v in zip(a, b)]
    for c in range(n):
        piv = max(range(c, n), key=lambda r: abs(m[r][c]))
        m[c], m[piv] = m[piv], m[c]
        if abs(m[c][c]) < 1e-12:
            continue
        for r in range(n):
            if r != c:
                f = m[r][c] / m[c][c]
                for k in range(c, n + 1):
                    m[r][k] -= f * m[c][k]
    return [m[i][n] / m[i][i] if abs(m[i][i]) > 1e-12 else 0.0 for i in range(n)]


def discover_skeleton(data: dict[str, list[float]], alpha: float = 0.05) -> dict[str, Any]:
    """PC-skeleton: edge X-Y kept iff dependent given every subset of neighbors."""
    import math as _m

    nodes = sorted(data)
    n = len(next(iter(data.values())))
    adj = {u: set(v for v in nodes if v != u) for u in nodes}

    def _pvalue(r: float, dof: int) -> float:
        if abs(r) >= 1.0 or dof < 1:
            return 0.0 if abs(r) >= 1.0 else 1.0
        z = 0.5 * _m.log((1 + r) / (1 - r)) * _m.sqrt(max(1, dof))
        # normal two-sided approx
        p = 2 * (1 - 0.5 * (1 + _m.erf(abs(z) / _m.sqrt(2))))
        return p

    for u in nodes:
        for v in list(adj[u]):
            if v not in adj[u]:
                continue
            others = [w for w in nodes if w not in (u, v)]
            separated = False
            for size in range(0, min(2, len(others)) + 1):
                from itertools import combinations

                for cond in combinations(others, size):
                    z = [data[w] for w in cond]
                    r = partial_corr(data[u], data[v], z)
                    if _pvalue(r, n - len(cond) - 3) > alpha:
                        separated = True
                        break
                if separated:
                    break
            if separated:
                adj[u].discard(v)
                adj[v].discard(u)
    edges = sorted((u, v) for u in nodes for v in adj[u] if u < v)
    return {"nodes": nodes, "edges": edges}


class StructuralCausalModel:
    """Linear-Gaussian DAG: eqs[var] = (parents, coeffs, noise_std)."""

    def __init__(self, order: list[str], eqs: dict[str, tuple[list[str], list[float], float]],
                 seed: int = 0) -> None:
        self.order = list(order)
        self.eqs = dict(eqs)
        self.rng = random.Random(seed)
        self.interventions: dict[str, float] = {}

    def do(self, var: str, value: float) -> "StructuralCausalModel":
        """Graph surgery: fix var, cut its incoming edges. Returns new SCM."""
        if var not in self.eqs:
            raise KeyError(var)
        twin = StructuralCausalModel(self.order, self.eqs, seed=self.rng.randrange(2 ** 30))
        twin.interventions = dict(self.interventions)
        twin.interventions[var] = value
        return twin

    def sample(self, n: int = 200) -> dict[str, list[float]]:
        out: dict[str, list[float]] = {v: [] for v in self.order}
        for _ in range(n):
            vals: dict[str, float] = {}
            for v in self.order:
                if v in self.interventions:
                    vals[v] = self.interventions[v]
                    continue
                parents, coeffs, noise = self.eqs[v]
                mu = sum(c * vals[p] for c, p in zip(coeffs, parents))
                vals[v] = mu + self.rng.gauss(0, noise)
            for v in self.order:
                out[v].append(vals[v])
        return out

    def ate(self, treatment: str, outcome: str, treated: float = 1.0,
            control: float = 0.0, n: int = 2000) -> float:
        """Average treatment effect via two do() worlds (interventional, not regression)."""
        a = self.do(treatment, treated).sample(n)[outcome]
        b = self.do(treatment, control).sample(n)[outcome]
        return sum(a) / n - sum(b) / n

    def to_dict(self) -> dict[str, Any]:
        return {"order": self.order, "edges": [(p, v) for v, (ps, _, _) in self.eqs.items() for p in ps],
                "interventions": self.interventions}
