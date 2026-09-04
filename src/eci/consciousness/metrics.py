"""Vectorized information-theoretic metrics.

All heavy loops from the legacy implementation are replaced with tensor
ops: Sample Entropy via delay embedding + Chebyshev ``cdist``, mutual
information via joint histogram bincounting, spectral entropy via FFT.
"""

from __future__ import annotations

from typing import Tuple

import numpy as np
import torch

from eci.constants import EPS

__all__ = [
    "lempel_ziv_complexity",
    "sample_entropy",
    "spectral_entropy",
    "mutual_information",
    "autocorrelation",
]


def lempel_ziv_complexity(data: np.ndarray, max_length: int = 50_000) -> float:
    """Normalized LZ76 complexity of the binarized signal.

    Fast implementation: the longest-prefix-match per phrase is located by
    binary search over phrase length using C-speed ``bytes.find``, which
    is orders of magnitude faster than the classic char-by-char loop while
    producing identical phrase counts.
    """
    if data.size == 0:
        return 0.0
    flat = data.flatten()
    if flat.size > max_length:  # stride subsample for tractability
        stride = int(np.ceil(flat.size / max_length))
        flat = flat[::stride]
    binary = (flat > np.median(flat)).astype(np.uint8)
    n = binary.size
    if n < 2:
        return 0.0

    s = binary.tobytes()
    u = 0
    phrases = 0
    while u < n:
        # Largest L such that s[u:u+L] occurs starting before position u.
        lo, hi = 1, n - u
        best = 0
        while lo <= hi:
            mid = (lo + hi) // 2
            if s.find(s[u:u + mid]) < u:
                best = mid
                lo = mid + 1
            else:
                hi = mid - 1
        # Canonical LZ76 phrase: match + one innovation character.
        phrases += 1
        u += min(best + 1, n - u)
    return float(min(phrases / (n / np.log2(n)), 1.0))


def sample_entropy(
    data: torch.Tensor,
    m: int = 2,
    r: float = 0.2,
    max_points: int = 2000,
) -> float:
    """Sample entropy (vectorized).

    Builds the m- and (m+1)-delay embedding matrices and counts template
    matches with a Chebyshev distance threshold ``r * std``.
    """
    if data.dim() > 1:
        data = data.flatten()
    x = data.to(torch.float64)
    x = (x - x.mean()) / (x.std() + EPS)
    n = x.numel()
    if n <= m + 1:
        return 0.0
    if n > max_points:
        stride = int(np.ceil(n / max_points))
        x = x[::stride]
        n = x.numel()
        if n <= m + 1:
            return 0.0

    tol = r * x.std() + EPS

    def _phi(dim: int) -> float:
        emb = x.unfold(0, dim, 1).unsqueeze(0)  # (1, n-dim+1, dim)
        dist = torch.cdist(emb, emb, p=float("inf"))  # Chebyshev
        matches = (dist < tol).double().sum() - (n - dim + 1)  # exclude self
        return float(matches / (n - dim + 1))

    phi_m = _phi(m)
    phi_m1 = _phi(m + 1)
    if phi_m <= 0 or phi_m1 <= 0:
        return 0.0
    return float(min(-np.log(phi_m1 / phi_m) / 2.0, 1.0))


def spectral_entropy(neural_data: torch.Tensor) -> float:
    """Normalized spectral entropy averaged over channels."""
    fft = torch.fft.rfft(neural_data.double(), dim=0)
    power = torch.abs(fft) ** 2
    power_norm = power / power.sum(dim=0, keepdim=True).clamp_min(EPS)
    entropy = -(power_norm * torch.log2(power_norm.clamp_min(EPS))).sum(dim=0)
    max_entropy = np.log2(power.shape[0]) + EPS
    return float((entropy.mean() / max_entropy).clamp(0.0, 1.0).item())


def mutual_information(x: torch.Tensor, y: torch.Tensor, bins: int = 10) -> float:
    """Mutual information (bits) via a joint histogram (fully vectorized)."""
    x = x.to(torch.float64)
    y = y.to(torch.float64)

    def _binned(z: torch.Tensor) -> torch.Tensor:
        z_min, z_max = z.min(), z.max()
        span = (z_max - z_min).clamp_min(EPS)
        idx = torch.floor((z - z_min) / span * (bins - 1)).long()
        return idx.clamp(0, bins - 1)

    xb, yb = _binned(x), _binned(y)
    joint_idx = xb * bins + yb
    joint = torch.bincount(joint_idx, minlength=bins * bins).double()
    joint = joint / joint.sum().clamp_min(EPS)
    joint = joint.reshape(bins, bins)
    px = joint.sum(dim=1)
    py = joint.sum(dim=0)
    outer = torch.outer(px, py)
    mask = joint > 1e-12
    mi = (joint[mask] * torch.log2(joint[mask] / outer.clamp_min(EPS)[mask])).sum()
    return float(max(0.0, mi.item()))


def autocorrelation(data: torch.Tensor, lag: int = 1) -> float:
    """Lag-k autocorrelation of the flattened signal."""
    flat = data.flatten().to(torch.float64)
    mean = flat.mean()
    var = flat.var(unbiased=False)
    if var < EPS:
        return 0.0
    a = flat[:-lag] - mean
    b = flat[lag:] - mean
    return float(max(0.0, ((a * b).mean() / var).item()))
