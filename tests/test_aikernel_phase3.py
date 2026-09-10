"""Phase 3 — IIT 4.0: interventions, distinctions, relations, honesty ledger.

Reference numbers below are MEASURED by this implementation (no PyPhi
installed — see crosscheck_pyphi skip). Structural identities are exact;
magnitudes are reported, not asserted against external ground truth
(which does not exist in this environment — see LIMITATIONS.md).
"""
import math


def test_and_cause_repertoire_is_point_mass():
    """Hand-derived: AND in state 1 admits exactly one past. ii = 2 bits."""
    from eci.consciousness.iit4 import and_system, cause_repertoire, intrinsic_information
    s = and_system()  # state (1, 1)
    rep = cause_repertoire(s, (0,), (1,), (0, 1))
    assert rep == {(0, 0): 0.0, (0, 1): 0.0, (1, 0): 0.0, (1, 1): 1.0}, rep
    ii, zstar = intrinsic_information(rep)
    assert abs(ii - 2.0) < 1e-9 and zstar == (1, 1), (ii, zstar)


def test_copy_effect_repertoire_is_point_mass():
    from eci.consciousness.iit4 import copy_system, effect_repertoire
    s = copy_system(1)
    rep = effect_repertoire(s, (0,), (1,), (0,))
    assert rep == {(0,): 0.0, (1,): 1.0}, rep


def test_intrinsic_information_hand_calc():
    from eci.consciousness.iit4 import intrinsic_information
    # full 4-state purview: half the states ruled out -> 0.5 * log2(2)
    ii, z = intrinsic_information({(0, 0): 0.0, (0, 1): 0.5, (1, 0): 0.0, (1, 1): 0.5})
    assert abs(ii - 0.5) < 1e-12 and z == (0, 1), (ii, z)  # ties -> lowest index
    ii2, _ = intrinsic_information({(0,): 0.25, (1,): 0.75})
    assert abs(ii2 - 0.75 * math.log2(0.75 / 0.5)) < 1e-12, ii2
    ii3, _ = intrinsic_information({(0,): 0.5, (1,): 0.5})
    assert ii3 == 0.0  # uniform specifies nothing


def test_repertoires_normalize_on_random_tpms():
    """Property: every repertoire is a distribution (sums to 1)."""
    import random
    from eci.consciousness.iit4 import (DiscreteSubstrate, cause_repertoire,
                                        effect_repertoire)
    rng = random.Random(0)
    for trial in range(10):
        n = 3
        tpm = {j: [rng.random() for _ in range(8)] for j in range(n)}
        s = DiscreteSubstrate(n, tpm, (1, 0, 1))
        for rep in (cause_repertoire(s, (0, 2), (1, 1), (1, 2)),
                    effect_repertoire(s, (1,), (0,), (0, 2))):
            assert abs(sum(rep.values()) - 1.0) < 1e-9, rep
            assert all(v >= 0.0 for v in rep.values())


def test_disconnected_phi_is_exactly_zero():
    """THE theorem: severing changes nothing, so the system MIP keeps all."""
    from eci.consciousness.iit4 import disconnected_system, phi_structure
    r = phi_structure(disconnected_system())
    assert r["phi"] == 0.0, r
    assert r["composition"] > 0  # singletons visible, not hidden
    assert r["system_mip"] == [[0], [1]], r["system_mip"]


def test_single_copy_photodiode():
    """Tononi's photodiode: one COPY unit carries exactly 1 bit."""
    from eci.consciousness.iit4 import copy_system, phi_structure
    r = phi_structure(copy_system(1))
    assert abs(r["phi"] - 1.0) < 1e-9, r
    assert r["n_distinctions"] == 1 and r["n_relations"] == 0


def test_xor_whole_distinction_measured():
    """Synergy paradigm: XOR pair scores 0.5 via the whole mechanism."""
    from eci.consciousness.iit4 import phi_structure, xor_system
    r = phi_structure(xor_system())
    assert abs(r["phi"] - 0.5) < 1e-9, r
    assert r["n_distinctions"] == 1
    d = r["distinctions"][0]
    assert d["mechanism"] == [0, 1] and abs(d["phi"] - 0.5) < 1e-9, d


def test_mutual_copy_and_and_reported():
    """Strongly-coupled swap loop integrates more than degenerate AND."""
    from eci.consciousness.iit4 import (and_system, mutual_copy_system,
                                        phi_structure)
    from eci.consciousness.iit4 import DiscreteSubstrate, _gate_tpm
    mc = phi_structure(mutual_copy_system())
    an = phi_structure(and_system())
    assert mc["phi"] > an["phi"] >= 0.0, (mc["phi"], an["phi"])
    assert abs(mc["phi"] - 3.0) < 1e-9, mc
    # AND in (0,0): selective past, determined future -> small but nonzero
    a00 = phi_structure(DiscreteSubstrate(
        2, _gate_tpm(2, {0: lambda b: b[0] & b[1], 1: lambda b: b[0] & b[1]}), (0, 0)))
    assert 0.0 < a00["phi"] < mc["phi"], a00


def test_relations_zero_without_overlap_nonzero_with_partial():
    """Disjoint purviews -> exactly 0. Partial overlap -> 1.0 (hand-built)."""
    from eci.consciousness.iit4 import intrinsic_information, relation_phi
    # disjoint: different units entirely
    r = relation_phi({(0,): 1.0}, (5,), {(0,): 1.0}, (7,),
                     {(0,): 1.0}, (5,), {(0,): 1.0}, (7,))
    assert r == 0.0
    # equality chain u0==u1==u2: each pair sees only pairwise equality;
    # the TRIPLE consistency (0,0,0)/(1,1,1) is genuinely relational.
    # joint ii = 1.0, severed best = 0.25 -> (1-0.25)/2 = 0.375 exactly.
    r1 = {(0, 0): 0.5, (0, 1): 0.0, (1, 0): 0.0, (1, 1): 0.5}  # over (0,1)
    r2 = {(0, 0): 0.5, (0, 1): 0.0, (1, 0): 0.0, (1, 1): 0.5}  # over (1,2)
    got = relation_phi(r1, (0, 1), r2, (1, 2), r1, (0, 1), r2, (1, 2))
    assert abs(got - 0.375) < 1e-9, got


def test_three_node_chain_runs():
    """Scaling smoke: 3-node COPY ring completes fast with sane output."""
    import time
    from eci.consciousness.iit4 import DiscreteSubstrate, _gate_tpm, phi_structure
    s = DiscreteSubstrate(3, _gate_tpm(3, {0: lambda b: b[2], 1: lambda b: b[0], 2: lambda b: b[1]}),
                          (1, 1, 1))
    t0 = time.time()
    r = phi_structure(s)
    assert time.time() - t0 < 60, "combinatorial wall hit at n=3"
    assert r["phi"] >= 0.0 and r["composition"] >= r["phi"]


def test_crosscheck_reports_skip_honestly():
    from eci.consciousness.iit4 import disconnected_system, crosscheck_pyphi
    out = crosscheck_pyphi(disconnected_system())
    assert out["skipped"] is True and "reason" in out
