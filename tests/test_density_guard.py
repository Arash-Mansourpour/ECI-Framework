"""Guard: density O(4^n) cap at n=12 (Phase 5)."""

import pytest

from eci.quantum.density import from_statevector, partial_trace
from eci.quantum.statevector import StatevectorSimulator


def test_density_guard_raises_before_oom():
    sim = StatevectorSimulator(13)
    psi = sim.random_state()
    # D=8192 → rho 8192²×8B≈512MB plus eigvalsh would OOM — must fail fast
    with pytest.raises(MemoryError, match=r"O\(4\^n\)"):
        from_statevector(psi)
    with pytest.raises(MemoryError, match=r"O\(4\^n\)"):
        partial_trace(psi, n_qubits=13, keep=[0])


def test_density_n12_allowed():
    sim = StatevectorSimulator(12)
    psi = sim.random_state()
    rho = from_statevector(psi)
    assert rho.shape == (1, 4096, 4096)
    # partial trace keep 2 qubits → 4×4
    kept = partial_trace(rho, n_qubits=12, keep=[0, 1])
    assert kept.shape == (1, 4, 4)
