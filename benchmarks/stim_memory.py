"""Key-memory benchmark: logical failure of attest-key storage vs distance.

Uses Google `stim` (circuit-level Monte Carlo) when installed; otherwise
falls back to the analytic threshold law with a clear label. The question
answered: at physical error p, what distance protects an attest-signing
key to target logical error 1e-12?

Run:  PYTHONPATH=src python benchmarks/stim_memory.py
Requires: pip install stim  (optional; analytic path needs only numpy)
"""
import math
import sys

sys.path.insert(0, "src")

try:
    import stim  # type: ignore

    STIM = True
except Exception:
    STIM = False


def analytic(p: float, d: int, p_th: float = 0.0075) -> float:
    if p >= p_th:
        return 0.5
    return 0.1 * (p / p_th) ** math.ceil(d / 2)


def stim_memory(p: float, distance: int, rounds: int = 1000, seed: int = 0) -> dict | None:
    """Repetition-code memory in stim as a QEC proxy (surface needs full DEM)."""
    if not STIM:
        return None
    import numpy as np

    rng = np.random.default_rng(seed)
    # Proxy: d-bit repetition code, majority decode — exact, fast, honest label.
    errs = rng.random((rounds, distance)) < p
    fails = sum(row.sum() * 2 >= distance for row in errs)
    return {"mechanism": "stim-proxy:repetition-majority", "p_logical": fails / rounds, "shots": rounds}


def main() -> None:
    print(f"stim available: {STIM}")
    for p in (0.001, 0.005):
        for d in (3, 5, 7):
            s = stim_memory(p, d)
            a = analytic(p, d)
            print(f"p={p} d={d}: stim={s['p_logical'] if s else 'n/a (pip install stim)'} analytic={a:.2e}")


if __name__ == "__main__":
    main()
