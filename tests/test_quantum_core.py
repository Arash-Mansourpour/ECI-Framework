"""Core quantum correctness: CPTP, concurrence/EoF, CRZ, Heisenberg."""
import math

import torch

from eci.quantum import channels as C
from eci.quantum import density as D
from eci.quantum import entanglement as E
from eci.quantum import gates as G
from eci.quantum import operator as O


def test_phase_damping_is_cptp():
    assert D.is_cptp(C.phase_damping(0.1))
    assert D.is_cptp(C.phase_damping(0.0))
    assert D.is_cptp(C.phase_damping(1.0))


def test_depolarizing_is_cptp():
    assert D.is_cptp(C.depolarizing(0.1))


def _bell():
    b = torch.zeros(1, 4, dtype=torch.complex64)
    b[0, 0] = b[0, 3] = 1 / math.sqrt(2)
    return D.from_statevector(b)


def test_concurrence_and_eof_bell():
    rho = _bell()
    assert abs(float(E.concurrence(rho)[0]) - 1.0) < 1e-4
    assert abs(float(E.entanglement_of_formation(rho)[0]) - 1.0) < 1e-3
    assert abs(float(E.negativity(rho, 2, [1])[0]) - 0.5) < 1e-4


def test_crz_is_controlled_rz():
    m = G.CRZ(0.5)
    d = m.diag()
    assert abs(d[0].item() - 1) < 1e-5 and abs(d[1].item() - 1) < 1e-5
    import cmath

    assert abs(d[2].item() - cmath.exp(-0.25j)) < 1e-5
    assert abs(d[3].item() - cmath.exp(0.25j)) < 1e-5


def test_heisenberg_t0_identity():
    H = torch.tensor([[0.0, 1.0], [1.0, 0.0]], dtype=torch.complex64)
    A = torch.tensor([[1.0, 0.0], [0.0, -1.0]], dtype=torch.complex64)
    assert torch.allclose(O.heisenberg_evolution(H, A, 0.0), A, atol=1e-5)


def test_avg_gate_fidelity_identity_is_one():
    I = torch.eye(2, dtype=torch.complex64)
    assert abs(O.average_gate_fidelity(I, I) - 1.0) < 1e-6
