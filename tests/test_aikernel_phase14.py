"""Phase 14 — PyPhi validation table + hygiene gate hardening.

sia (IIT 3.0, EMD) vs phi_structure (IIT 4.0, composition), 2-node gates:
  disconn  0.0     vs 0.0     (theorem both versions share)
  mutCOPY  1.0     vs 3.0     (both rank it top)
  AND11    0.1875  vs 0.1226
  AND00    0.0694  vs 0.2658
  XOR      0.0     vs 0.5     (sharp divergence: synergy paradigm differs)
Agreement claimed ONLY on: zero theorem + argmax/argmin ordering. The
magnitudes are incommensurate measures — asserted as such, not equated.
"""
import pytest


def _pyphi_sia(rules, state):
    import collections
    import collections.abc
    for n in ("Iterable", "Mapping", "Sequence", "MutableMapping"):
        if not hasattr(collections, n):
            setattr(collections, n, getattr(collections.abc, n))
    import numpy as np
    import pyphi
    pyphi.config.PARALLEL_COMPLEX_EVALUATION = False
    pyphi.config.PARALLEL_CONCEPT_EVALUATION = False
    pyphi.config.PARALLEL_CUT_EVALUATION = False
    tpm = np.zeros((2, 2, 2))
    for s0 in (0, 1):
        for s1 in (0, 1):
            tpm[s0, s1, 0] = rules[0](s0, s1)
            tpm[s0, s1, 1] = rules[1](s0, s1)
    net = pyphi.Network(tpm)
    return float(pyphi.compute.sia(pyphi.Subsystem(net, state=state, nodes=(0, 1))).phi)


needs_pyphi = pytest.mark.skipif(
    __import__("importlib").util.find_spec("pyphi") is None, reason="pyphi not installed")


CASES = {
    "disconn": ((lambda a, b: a, lambda a, b: b), (1, 1)),
    "mutCOPY": ((lambda a, b: b, lambda a, b: a), (1, 1)),
    "AND11": ((lambda a, b: a & b, lambda a, b: a & b), (1, 1)),
    "AND00": ((lambda a, b: a & b, lambda a, b: a & b), (0, 0)),
    "XOR": ((lambda a, b: a ^ b, lambda a, b: a ^ b), (1, 1)),
}


@needs_pyphi
def test_sia_table_shared_theorems_and_ordering():
    from eci.consciousness import iit4
    from eci.consciousness.iit4 import DiscreteSubstrate, _gate_tpm
    sia, mine = {}, {}
    for name, (rules, st) in CASES.items():
        sia[name] = _pyphi_sia(rules, st)
        # default-arg binding (rules=rules): values bake at construction
        # inside _gate_tpm, but explicit binding removes all doubt (B023).
        sub = DiscreteSubstrate(2, _gate_tpm(2, {0: lambda b, r=rules: r[0](b[0], b[1]),
                                                 1: lambda b, r=rules: r[1](b[0], b[1])}), st)
        mine[name] = round(iit4.phi_structure(sub)["phi"], 4)
    assert sia["disconn"] == 0.0 and mine["disconn"] == 0.0  # shared theorem
    assert max(sia, key=sia.get) == "mutCOPY" == max(mine, key=mine.get)
    assert min(sia, key=sia.get) == "disconn" == min(mine, key=mine.get)
    # spot magnitudes (calibrated, deterministic — guards silent drift)
    assert abs(sia["mutCOPY"] - 1.0) < 1e-9
    assert abs(mine["XOR"] - 0.5) < 1e-9
    assert abs(sia["AND11"] - 0.1875) < 1e-4 and abs(mine["AND11"] - 0.1226) < 1e-4


def test_hygiene_gate_is_self_maintaining():
    """The Phase 10 gate used hardcoded file lists and rotted within 4
    phases. It now discovers via glob: assert every on-disk
    test_aikernel_*.py file is actually scanned by the gate helpers."""
    import pathlib
    import sys
    root = pathlib.Path(__file__).resolve().parents[1]
    on_disk = sorted(p.name for p in (root / "tests").glob("test_aikernel_*.py"))
    sys.path.insert(0, str(root / "tests"))
    import test_aikernel_phase10 as gate
    try:
        covered_tests = sorted(pathlib.Path(p).name for p in gate._aik_test_files())
    finally:
        sys.path.remove(str(root / "tests"))
    assert covered_tests == on_disk, (covered_tests, on_disk)
    assert len(covered_tests) >= 14, covered_tests
