"""Topological QEC shots + MPS canonical truncate."""
from eci.quantum.statevector import StatevectorSimulator
from eci.quantum.tensor_network import bond_benchmark, mps_from_statevector, mps_truncate
from eci.quantum.topological import SurfaceCode


def test_surface_stabilizer_count_d3():
    s = SurfaceCode(3)
    assert len(s.x_stabilizers()) == 4
    assert len(s.z_stabilizers()) == 4


def test_surface_trials_monotone_and_ci():
    s = SurfaceCode(3)
    lo = s.run_trials(p_phys=0.001, shots=100, seed=0)
    hi = s.run_trials(p_phys=0.05, shots=100, seed=0)
    assert lo["p_logical_mc"] <= hi["p_logical_mc"]
    assert lo["wilson"]["lo"] <= lo["p_logical_mc"] <= lo["wilson"]["hi"]


def test_mps_truncate_reports_error():
    sim = StatevectorSimulator(4)
    st = sim.uniform_superposition()
    mps = mps_from_statevector(st, 4, chi_max=16)
    trunc, err = mps_truncate(mps, chi=2)
    assert err >= 0.0
    bench = bond_benchmark(st, 4, chis=(2, 4))
    assert bench[1]["fidelity"] >= bench[0]["fidelity"] - 1e-6
