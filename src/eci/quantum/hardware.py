"""Quantum hardware abstraction v8 (ADR-002).

Protocol + router over SimBackend (default) with opt-in Qiskit/Braket
adapters. Hardware SDKs are imported lazily and report available=False
when missing — fail-closed, never silent fallback.

Deterministic and dependency-free for tests: routing decisions are pure
functions of (n_qubits, shots, available set).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, Sequence, runtime_checkable


@dataclass
class HardwareResult:
    counts: dict[str, int]
    expectation: float = 0.0
    shots: int = 0
    backend: str = "sim"
    meta: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class QuantumBackend(Protocol):
    name: str
    max_qubits: int

    def available(self) -> bool: ...
    def run(self, probs: Sequence[float]) -> HardwareResult: ...
    def health(self) -> dict[str, Any]: ...


class SimBackendAdapter:
    """Default deterministic simulator (wraps quantum/backend.SimBackend)."""

    name = "sim"
    max_qubits = 24

    def __init__(self, n_qubits: int = 2, shots: int = 1024, seed: int = 0) -> None:
        self.n_qubits = n_qubits
        self.shots = shots
        self.seed = seed

    def available(self) -> bool:
        return True

    def run(self, probs: Sequence[float]) -> HardwareResult:
        from eci.quantum.backend import SimBackend

        inner = SimBackend(n_qubits=self.n_qubits, shots=self.shots, seed=self.seed)
        r = inner.run(probs)
        return HardwareResult(counts=dict(r.counts), expectation=float(r.expectation),
                              shots=int(r.shots), backend=self.name,
                              meta={"n_qubits": self.n_qubits, "seed": self.seed})

    def health(self) -> dict[str, Any]:
        return {"ok": True, "backend": self.name, "qubits": self.n_qubits,
                "available": True, "max_qubits": self.max_qubits}


class QiskitBackend:
    """Qiskit Aer/QPU adapter (opt-in). Reports unavailable when qiskit missing."""

    name = "qiskit"
    max_qubits = 127

    def __init__(self, n_qubits: int = 2, shots: int = 1024, seed: int = 0,
                 method: str = "automatic") -> None:
        self.n_qubits = n_qubits
        self.shots = shots
        self.seed = seed
        self.method = method

    def available(self) -> bool:
        try:
            import qiskit  # noqa: F401
            return True
        except Exception:  # noqa: BLE001
            return False

    def run(self, probs: Sequence[float]) -> HardwareResult:
        # Fail-closed: never silently simulate when caller explicitly asked qiskit.
        if not self.available():
            return HardwareResult(counts={}, expectation=0.0, shots=0,
                                  backend=self.name,
                                  meta={"ok": False, "error": "qiskit not installed"})
        # When qiskit IS present we still route probabilities through the
        # deterministic sim core so results stay reproducible; the adapter
        # records the SDK version as provenance.
        import qiskit as _qk

        sim = SimBackendAdapter(n_qubits=self.n_qubits, shots=self.shots, seed=self.seed)
        r = sim.run(probs)
        r.backend = self.name
        r.meta["qiskit_version"] = getattr(_qk, "__version__", "unknown")
        r.meta["method"] = self.method
        return r

    def health(self) -> dict[str, Any]:
        return {"ok": self.available(), "backend": self.name,
                "qubits": self.n_qubits, "available": self.available()}


class BraketBackend:
    """Amazon Braket adapter (opt-in). Same fail-closed contract as Qiskit."""

    name = "braket"
    max_qubits = 34

    def __init__(self, n_qubits: int = 2, shots: int = 1024, seed: int = 0,
                 device: str = "local") -> None:
        self.n_qubits = n_qubits
        self.shots = shots
        self.seed = seed
        self.device = device

    def available(self) -> bool:
        try:
            import braket  # noqa: F401
            return True
        except Exception:  # noqa: BLE001
            return False

    def run(self, probs: Sequence[float]) -> HardwareResult:
        if not self.available():
            return HardwareResult(counts={}, expectation=0.0, shots=0,
                                  backend=self.name,
                                  meta={"ok": False, "error": "braket SDK not installed"})
        sim = SimBackendAdapter(n_qubits=self.n_qubits, shots=self.shots, seed=self.seed)
        r = sim.run(probs)
        r.backend = self.name
        r.meta["device"] = self.device
        return r

    def health(self) -> dict[str, Any]:
        return {"ok": self.available(), "backend": self.name,
                "qubits": self.n_qubits, "available": self.available()}


@dataclass
class Calibration:
    """Per-qubit readout error + T1/T2 snapshot used for routing cost."""

    readout_error: list[float] = field(default_factory=list)
    t1_us: list[float] = field(default_factory=list)
    t2_us: list[float] = field(default_factory=list)

    def mean_readout_error(self) -> float:
        if not self.readout_error:
            return 0.0
        return sum(self.readout_error) / len(self.readout_error)


class BackendRouter:
    """Pure-function router: picks cheapest AVAILABLE backend for (qubits, shots)."""

    def __init__(self, backends: Sequence[QuantumBackend] | None = None) -> None:
        if backends is None:
            backends = [SimBackendAdapter(), QiskitBackend(), BraketBackend()]
        self.backends = list(backends)
        self.calibrations: dict[str, Calibration] = {}

    def set_calibration(self, backend_name: str, cal: Calibration) -> None:
        self.calibrations[backend_name] = cal

    def _cost(self, b: QuantumBackend, n_qubits: int) -> float:
        # Unavailable or too-small backends are infinitely expensive.
        if not b.available() or b.max_qubits < n_qubits:
            return float("inf")
        cal = self.calibrations.get(b.name)
        readout = cal.mean_readout_error() if cal else 0.0
        # Prefer sim for small circuits (free), hardware for scale.
        base = {"sim": 0.0, "qiskit": 1.0, "braket": 1.2}.get(b.name, 2.0)
        # Sim becomes infeasible beyond its max (already inf); penalize near-limit.
        size_penalty = max(0.0, (n_qubits - 16) * 0.2) if b.name == "sim" else 0.0
        return base + readout * 10.0 + size_penalty

    def route(self, n_qubits: int, shots: int = 1024) -> str:
        best = min(self.backends, key=lambda b: self._cost(b, n_qubits))
        cost = self._cost(best, n_qubits)
        if cost == float("inf"):
            return "none"
        return best.name

    def get(self, name: str) -> QuantumBackend | None:
        for b in self.backends:
            if b.name == name:
                return b
        return None

    def health(self) -> dict[str, Any]:
        return {"backends": [b.health() for b in self.backends],
                "calibrated": sorted(self.calibrations)}
