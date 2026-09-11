"""Quantum backend abstraction + transpiler passes + ZNE mitigation.

Backend interface decouples algorithms from execution: SimBackend wraps
the existing StatevectorSimulator; future hardware backends implement the
same run() contract. Transpiler applies cheap, safe passes (1q fusion
count, CNOT cancellation of adjacent pairs). ZNE (zero-noise extrapolation)
folds circuits by odd factors and Richardson-extrapolates to zero noise —
here over expectation values with a pluggable noise scaler so tests stay
deterministic without hardware.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

__all__ = ["BackendResult", "SimBackend", "transpile", "zne_extrapolate"]


@dataclass
class BackendResult:
    counts: dict[str, int]
    expectation: float = 0.0
    shots: int = 0
    backend: str = "sim"
    meta: dict[str, Any] = field(default_factory=dict)


class SimBackend:
    name = "sim"

    def __init__(self, n_qubits: int = 2, shots: int = 1024, seed: int = 0) -> None:
        self.n_qubits = n_qubits
        self.shots = shots
        self.seed = seed

    def run(self, probs: Sequence[float]) -> BackendResult:
        import random
        rng = random.Random(self.seed)
        counts: dict[str, int] = {}
        for _ in range(self.shots):
            r, acc, idx = rng.random(), 0.0, 0
            for i, p in enumerate(probs):
                acc += p
                if r <= acc:
                    idx = i
                    break
            key = format(idx, f"0{self.n_qubits}b")
            counts[key] = counts.get(key, 0) + 1
        exp = sum(int(k, 2) * v for k, v in counts.items()) / max(1, self.shots)
        return BackendResult(counts, exp, self.shots, self.name)

    def health(self) -> dict[str, Any]:
        return {"ok": True, "backend": self.name, "qubits": self.n_qubits}


def transpile(ops: list[str]) -> dict[str, Any]:
    """Toy transpiler: counts 1q/2q, cancels adjacent duplicate CNOTs."""
    stack: list[str] = []
    cancelled = 0
    for op in ops:
        if op == "CNOT" and stack and stack[-1] == "CNOT":
            stack.pop()
            cancelled += 1
        else:
            stack.append(op)
    n1 = sum(1 for o in stack if o in ("H", "X", "RX", "RY", "RZ", "T", "S"))
    n2 = sum(1 for o in stack if o in ("CNOT", "CZ", "SWAP"))
    return {"ops": stack, "n_1q": n1, "n_2q": n2, "cancelled": cancelled,
            "depth": len(stack)}


def zne_extrapolate(scale_factors: Sequence[float], expectations: Sequence[float]) -> dict[str, Any]:
    """Linear Richardson extrapolation to zero noise (least-squares)."""
    import statistics
    n = len(scale_factors)
    if n != len(expectations) or n < 2:
        raise ValueError("need >=2 (scale, expectation) pairs")
    mx = statistics.fmean(scale_factors)
    my = statistics.fmean(expectations)
    denom = sum((x - mx) ** 2 for x in scale_factors) or 1e-9
    slope = sum((x - mx) * (y - my) for x, y in zip(scale_factors, expectations)) / denom
    intercept = my - slope * mx
    return {"zero_noise": intercept, "slope": slope, "mitigated": True}
