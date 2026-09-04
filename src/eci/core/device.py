"""Device, dtype and reproducibility management."""

from __future__ import annotations

import contextlib
import random
from typing import Iterator, Optional

import numpy as np
import torch

__all__ = ["get_device", "configure_seeds", "seed_context", "device_dtype_info"]


def get_device(prefer: str = "auto") -> torch.device:
    """Resolve the compute device.

    Args:
        prefer: ``"auto"`` (cuda if available, else cpu), ``"cuda"``,
            ``"cpu"`` or a torch device string such as ``"cuda:1"``.
    """
    if prefer == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if prefer in ("cuda", "gpu") :
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(prefer)


def configure_seeds(
    seed: int = 42,
    deterministic: bool = False,
    device: Optional[torch.device] = None,
) -> None:
    """Seed python, numpy and torch (CPU + all CUDA devices) for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if device is not None and device.type == "cuda":
        torch.cuda.manual_seed_all(seed)
    elif torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    if deterministic:
        torch.use_deterministic_algorithms(True, warn_only=True)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


@contextlib.contextmanager
def seed_context(seed: int) -> Iterator[None]:
    """Temporarily seed all RNGs, restoring prior numpy/torch RNG states on exit."""
    np_state = np.random.get_state()
    torch_state = torch.get_rng_state()
    py_state = random.getstate()
    configure_seeds(seed)
    try:
        yield
    finally:
        np.random.set_state(np_state)
        torch.set_rng_state(torch_state)
        random.setstate(py_state)


def device_dtype_info(device: torch.device) -> dict:
    """Return a small diagnostic dict about the resolved device."""
    info = {
        "device": str(device),
        "cuda_available": torch.cuda.is_available(),
        "torch_version": torch.__version__,
        "thread_count": torch.get_num_threads(),
    }
    if device.type == "cuda":
        info["gpu_name"] = torch.cuda.get_device_name(device)
        info["cuda_version"] = torch.version.cuda
    return info
