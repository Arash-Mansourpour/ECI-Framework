"""EEG / neural-time-series loader for the awareness lab.

Accepts ``.npy`` (``[time, channels]`` or ``[channels, time]``), ``.csv``
and ``.npz`` (first array). Normalizes to ``[time, channels]`` float64,
applies optional z-scoring + bandpower features so real recordings can
replace the synthetic sine in ``eci consciousness`` and iPDF calibration.

No hard dependency on MNE: if ``mne`` is installed, ``read_mne_raw()``
exposes raw.get_data() in the same layout.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import torch

__all__ = ["load_timeseries", "bandpower", "read_mne_raw"]


def _to_time_first(arr: np.ndarray) -> np.ndarray:
    arr = np.asarray(arr, dtype=np.float64)
    if arr.ndim == 1:
        return arr.reshape(-1, 1)
    if arr.ndim != 2:
        raise ValueError(f"expected 1-D or 2-D array, got {arr.shape}")
    # Heuristic: time axis is the longer one.
    if arr.shape[0] < arr.shape[1] and arr.shape[1] > 4 * arr.shape[0]:
        return arr.T
    return arr


def load_timeseries(path: str | Path, zscore: bool = True, max_seconds: int | None = None, sfreq: float = 256.0) -> torch.Tensor:
    """Load ``[time, channels]`` torch tensor from .npy/.npz/.csv."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"timeseries file not found: {p}")
    if p.suffix == ".npy":
        arr = np.load(p)
    elif p.suffix == ".npz":
        z = np.load(p)
        arr = z[z.files[0]]
    elif p.suffix == ".csv":
        arr = np.loadtxt(p, delimiter=",")
    else:
        raise ValueError(f"unsupported suffix {p.suffix} (use .npy/.npz/.csv)")
    arr = _to_time_first(arr)
    if max_seconds is not None:
        arr = arr[: int(max_seconds * sfreq)]
    if zscore:
        mu, sd = arr.mean(axis=0, keepdims=True), arr.std(axis=0, keepdims=True) + 1e-12
        arr = (arr - mu) / sd
    arr = np.nan_to_num(arr, nan=0.0, posinf=3.0, neginf=-3.0)
    return torch.from_numpy(arr)


def bandpower(x: torch.Tensor, sfreq: float = 256.0) -> Dict[str, float]:
    """Welch-free FFT bandpower (delta/theta/alpha/beta/gamma) mean over channels."""
    xd = x.double()
    fft = torch.fft.rfft(xd, dim=0)
    freqs = torch.fft.rfftfreq(xd.shape[0], d=1.0 / sfreq)
    power = (fft.abs() ** 2).mean(dim=1)
    bands = {"delta": (0.5, 4), "theta": (4, 8), "alpha": (8, 13), "beta": (13, 30), "gamma": (30, 100)}
    out: Dict[str, float] = {}
    total = float(power.sum().item()) + 1e-12
    for name, (lo, hi) in bands.items():
        m = (freqs >= lo) & (freqs < hi)
        out[name] = float(power[m].sum().item() / total) if m.any() else 0.0
    return out


def read_mne_raw(path: str | Path) -> Tuple[torch.Tensor, float]:
    """Load via MNE if installed; returns (tensor [time, ch], sfreq)."""
    try:
        import mne as _mne
    except Exception as e:
        raise ImportError("mne is not installed (pip install mne)") from e
    raw = _mne.io.read_raw(str(path), preload=True, verbose="ERROR")
    data = raw.get_data().T  # [ch, time] -> [time, ch]
    return torch.from_numpy(np.nan_to_num(data).astype(np.float64)), float(raw.info["sfreq"])
