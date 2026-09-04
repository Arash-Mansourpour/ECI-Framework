"""Robust aggregation for distributed updates.

* :func:`geometric_median` - Weiszfeld's iterative algorithm with
  convergence checking (50% breakdown point, paper section 2.4.2).
* :func:`byzantine_robust_aggregate` - aggregates dict-shaped model updates
  via geometric median, coordinate-wise median, or trimmed mean.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

import torch

__all__ = ["geometric_median", "byzantine_robust_aggregate", "krum", "bulyan"]


def geometric_median(
    points: torch.Tensor,
    weights: Optional[torch.Tensor] = None,
    tol: float = 1e-6,
    max_iter: int = 200,
) -> torch.Tensor:
    """Geometric median via Weiszfeld's algorithm.

    Args:
        points: ``(n, d)`` tensor of points.
        weights: optional ``(n,)`` weights (default: uniform).
        tol: convergence tolerance on the update step.
        max_iter: iteration cap.

    Returns:
        ``(d,)`` geometric median estimate.
    """
    if points.dim() != 2 or points.shape[0] == 0:
        raise ValueError("points must be a non-empty (n, d) tensor")
    if weights is None:
        weights = torch.ones(points.shape[0], dtype=points.dtype, device=points.device)
    weights = weights / weights.sum().clamp_min(1e-12)

    # Standard Weiszfeld initialization: component-wise median (already
    # close to the optimum and robust to outliers, unlike the mean).
    median = points.median(dim=0).values
    for _ in range(max_iter):
        distances = torch.linalg.vector_norm(points - median.unsqueeze(0), dim=1)
        # Guard against division by (near-)zero distances
        distances = distances.clamp_min(1e-12)
        new_median = (points * (weights / distances).unsqueeze(1)).sum(dim=0)
        step = torch.linalg.vector_norm(new_median - median)
        median = new_median
        if step < tol:
            break
    return median


def byzantine_robust_aggregate(
    updates: Sequence[Dict[str, torch.Tensor]],
    method: str = "geometric_median",
    trim_ratio: float = 0.1,
) -> Dict[str, torch.Tensor]:
    """Aggregate stacked parameter updates robustly.

    Args:
        updates: list of ``{param_name: tensor}`` client updates.
        method: ``"geometric_median"`` | ``"median"`` | ``"trimmed_mean"``
            | ``"krum"`` | ``"bulyan"``.
        trim_ratio: fraction trimmed from each side (trimmed mean only).
    """
    if not updates:
        raise ValueError("updates must be non-empty")
    if method not in ("geometric_median", "median", "trimmed_mean", "krum", "bulyan"):
        raise ValueError(f"unknown aggregation method: {method}")

    names = list(updates[0].keys())
    for u in updates:
        if set(u.keys()) != set(names):
            raise ValueError("inconsistent update keys across clients")

    if method in ("krum", "bulyan"):
        return _krum_family(updates, names, method=method)

    aggregated: Dict[str, torch.Tensor] = {}
    for name in names:
        stacked = torch.stack([u[name].flatten() for u in updates], dim=0)
        if method == "geometric_median":
            flat = geometric_median(stacked.to(torch.float64)).to(stacked.dtype)
        elif method == "median":
            flat = stacked.median(dim=0).values
        else:  # trimmed_mean
            n = stacked.shape[0]
            k = int(trim_ratio * n)
            sorted_vals, _ = torch.sort(stacked, dim=0)
            trimmed = sorted_vals[k: n - k] if n - 2 * k >= 1 else sorted_vals
            flat = trimmed.mean(dim=0)
        aggregated[name] = flat.view_as(updates[0][name])
    return aggregated


def _flat_stack(updates: Sequence[Dict[str, torch.Tensor]], names: List[str]) -> torch.Tensor:
    return torch.stack([
        torch.cat([u[n].flatten() for n in names]).to(torch.float64) for u in updates
    ], dim=0)


def krum(updates: Sequence[Dict[str, torch.Tensor]], f: int = 1) -> Dict[str, torch.Tensor]:
    """Krum (Blanchard et al. 2017): pick the update closest to its n-f-2 neighbours."""
    names = list(updates[0].keys())
    return _krum_family(updates, names, method="krum", f=f)


def bulyan(updates: Sequence[Dict[str, torch.Tensor]], f: int = 1) -> Dict[str, torch.Tensor]:
    """Bulyan (Mhamdi et al. 2018): Krum-select n-2f updates, then trimmed mean."""
    names = list(updates[0].keys())
    return _krum_family(updates, names, method="bulyan", f=f)


def _krum_family(updates: Sequence[Dict[str, torch.Tensor]], names: List[str], method: str, f: int = 1) -> Dict[str, torch.Tensor]:
    flat = _flat_stack(updates, names)
    n = flat.shape[0]
    if n < 2 * f + 3:
        raise ValueError(f"need n >= 2f+3 for {method} (n={n}, f={f})")
    dist = torch.cdist(flat, flat, p=2)
    if method == "krum":
        scores = []
        for i in range(n):
            d, _ = torch.sort(dist[i])
            scores.append(float(d[1: n - f - 1].sum().item()))
        best = int(torch.argmin(torch.tensor(scores)).item())
        return {k: updates[best][k].clone() for k in names}
    # Bulyan: Krum-score all, keep best n-2f, coordinate-wise trimmed mean (β=f).
    scores = []
    for i in range(n):
        d, _ = torch.sort(dist[i])
        scores.append(float(d[1: n - f - 1].sum().item()))
    order = torch.argsort(torch.tensor(scores)).tolist()[: n - 2 * f]
    out: Dict[str, torch.Tensor] = {}
    for name in names:
        stacked = torch.stack([updates[i][name].flatten() for i in order], dim=0)
        sv, _ = torch.sort(stacked, dim=0)
        trimmed = sv[f: len(order) - f] if len(order) - 2 * f >= 1 else sv
        out[name] = trimmed.mean(dim=0).view_as(updates[0][name])
    return out
