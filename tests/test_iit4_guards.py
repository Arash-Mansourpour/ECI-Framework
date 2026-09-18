"""Guard: phi_structure hard cap at n=8 (Phase 1.5)."""

import time

import pytest

from eci.consciousness.iit4 import DiscreteSubstrate, phi_structure


def _substrate(n: int) -> DiscreteSubstrate:
    tpm = {j: [0.5] * (2**n) for j in range(n)}
    state = tuple([0] * n)
    return DiscreteSubstrate(n, tpm, state)


def test_phi_structure_caps_at_eight():
    ok = _substrate(3)
    # n=3 is allowed; n=8 would also be allowed but is combinatorially heavy for a unit test
    phi_structure(ok)

    big = _substrate(9)
    t0 = time.perf_counter()
    with pytest.raises(ValueError, match=r"capped at n=8"):
        phi_structure(big)
    dt = time.perf_counter() - t0
    assert dt < 0.5, f"cap must raise immediately, not hang (took {dt:.2f}s)"
    # message must point to LIMITATIONS
    try:
        phi_structure(big)
    except ValueError as exc:
        assert "LIMITATIONS.md" in str(exc)
