"""Robust aggregation for distributed updates.

* :func:`geometric_median` - Weiszfeld's iterative algorithm with
  convergence checking (50% breakdown point, paper section 2.4.2).
* :func:`byzantine_robust_aggregate` - aggregates dict-shaped model updates
  via geometric median, coordinate-wise median, or trimmed mean.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

import torch

__all__ = ["geometric_median", "byzantine_robust_aggregate"]


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
        method: ``"geometric_median"`` | ``"median"`` | ``"trimmed_mean"``.
        trim_ratio: fraction trimmed from each side (trimmed mean only).
    """
    if not updates:
        raise ValueError("updates must be non-empty")
    if method not in ("geometric_median", "median", "trimmed_mean"):
        raise ValueError(f"unknown aggregation method: {method}")

    names = list(updates[0].keys())
    for u in updates:
        if set(u.keys()) != set(names):
            raise ValueError("inconsistent update keys across clients")

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
