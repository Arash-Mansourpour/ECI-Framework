"""QRNG-grade randomness: multi-source mixing for nonces and challenges.

Mixes OS entropy (secrets), PID/time jitter, and optional torch noise;
health-checked with a monobit frequency gate. Predictable challenges
kill challenge-response security, so this module — not bare random() —
backs nonces, challenge nonces, and audit samplers.
"""

from __future__ import annotations

import hashlib
import os
import secrets
import time

__all__ = ["mix", "token_hex", "health_check"]


def mix(n_bytes: int = 32, extra: bytes = b"") -> bytes:
    """SHA-256 mix of OS entropy + jitter + optional extra (+torch if present)."""
    parts = [secrets.token_bytes(32), os.urandom(16),
             str(time.time_ns()).encode(), str(os.getpid()).encode(), extra]
    try:
        import torch

        parts.append(torch.randn(8).numpy().tobytes())
    except Exception:  # noqa: BLE001 — torch optional here
        pass
    return hashlib.sha256(b"|".join(parts)).digest()[:n_bytes]


def token_hex(n_bytes: int = 16) -> str:
    return mix(n_bytes).hex()


def health_check(sample: bytes) -> dict:
    """Monobit frequency gate: fraction of 1-bits must lie in [0.4, 0.6] for >=256 bits."""
    n_bits = len(sample) * 8
    ones = sum(bin(b).count("1") for b in sample)
    frac = ones / max(1, n_bits)
    return {"n_bits": n_bits, "ones_frac": frac, "ok": n_bits >= 256 and 0.4 <= frac <= 0.6}
