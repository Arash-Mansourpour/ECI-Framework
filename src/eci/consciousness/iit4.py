"""IIT 4.0 cause-effect structure (Albantakis et al. 2023, PLOS Comp Biol
19(10):e1011465, arXiv:2212.14787) — alongside, NOT replacing, ``iit.py``.

What is implemented (with paper locations):
  - Discrete substrate (Sec. "The IIT ontology", Supp. S1): binary units +
    TPM, current state. Interventions are do()-style fixes on this TPM.
  - Cause repertoire (Box 2, "Cause repertoire"): Bayes inversion with a
    uniform prior over past purview states; non-purview past averaged
    uniformly ("causal marginalization").
  - Effect repertoire (Box 2, "Effect repertoire"): mechanism fixed,
    non-mechanism present units averaged uniformly, purview joint =
    product of per-unit marginals (exact given the TPM class).
  - Intrinsic information (Box 3): selectivity x informativeness,
    POINTWISE at the maximal state z*:
        ii = pi(z*|m) * log2(pi(z*|m) / u(z*)),  u = uniform.
  - Distinction phi (Sec. "Integration", exclusion/maximal-existence):
    cause/effect purviews chosen INDEPENDENTLY to maximize integrated
    cause/effect info; phi_d = min of the two maxima. MIP = bipartition
    of the mechanism maximizing preserved ii (partitioned repertoire =
    same computation with only that part fixed).
  - Relations + system Phi ("Composition", "Phi-structure"): pair
    relations over shared purview overlap (see ``relation_phi`` for the
    exact operationalization); Phi = sum(distinctions) + sum(relations).

Operationalization choices the paper leaves open (stated, not hidden):
  R1. Partitioned repertoires fix one mechanism part and noise the rest
      (rather than splitting the purview) — the standard directional-cut
      reading.
  R2. Pair-relation MIP severs the overlap: each relatum keeps its
      private purview part, overlap assigned to one side; best of the two
      assignments. Normalized by |d| = 2.
  R3. z* ties broken by lowest state index (deterministic).
  R4. Single-unit mechanisms admit no cut: phi = ii (fully integrated).

What is NOT here: continuous/Gaussian input (use ``iit.py``), >8-unit
exhaustion (combinatorial wall, documented), PyPhi cross-check (no PyPhi
installed — ``crosscheck_pyphi()`` runs it automatically IF importable).
See ``consciousness/LIMITATIONS.md`` for the honesty ledger.

No StateContributor adapter (deliberate, per spec Phase 3 §6): forcing
continuous GenerativeState through this discrete path would undermine §1.
See ``consciousness/LIMITATIONS.md`` for what these numbers are and are not.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from typing import Any

__all__ = ["DiscreteSubstrate", "and_system", "or_system", "xor_system",
           "copy_system", "disconnected_system", "cause_repertoire",
           "effect_repertoire", "intrinsic_information", "distinction",
           "relation_phi", "phi_structure", "crosscheck_pyphi"]


# ----------------------------------------------------------------------
# 1. Substrate
# ----------------------------------------------------------------------
@dataclass
class DiscreteSubstrate:
    """n binary units; tpm[j][past] = P(unit j = 1 | past).

    past is an int 0..2^n-1, bit i (LSB-first) = unit i. state likewise.
    """

    n: int
    tpm: dict[int, list[float]]
    state: tuple[int, ...]

    def __post_init__(self) -> None:
        assert len(self.state) == self.n
        assert set(self.tpm) == set(range(self.n))
        for j, col in self.tpm.items():
            assert len(col) == 2 ** self.n, (j, len(col))
            assert all(0.0 <= p <= 1.0 for p in col), j

    def prob1(self, node: int, past: int) -> float:
        return self.tpm[node][past]


def _statespace(k: int) -> list[tuple[int, ...]]:
    return list(itertools.product((0, 1), repeat=k))


def _past_int(full: dict[int, int], n: int) -> int:
    return sum(v << i for i, v in ((i, full[i]) for i in range(n)))


def _gate_tpm(n: int, rules: dict[int, Any]) -> dict[int, list[float]]:
    """rules: node -> f(past_tuple) -> P(1). Deterministic gates use 0/1."""
    tpm: dict[int, list[float]] = {}
    for j in range(n):
        col = []
        for past in range(2 ** n):
            bits = tuple((past >> i) & 1 for i in range(n))
            col.append(float(rules[j](bits)))
        tpm[j] = col
    return tpm


def copy_system(n: int = 1) -> DiscreteSubstrate:
    """Each unit copies itself (n=1: the single-unit reference)."""
    return DiscreteSubstrate(n, _gate_tpm(n, {j: (lambda b, j=j: b[j]) for j in range(n)}),
                             tuple([1] * n))


def disconnected_system() -> DiscreteSubstrate:
    return DiscreteSubstrate(2, _gate_tpm(2, {0: lambda b: b[0], 1: lambda b: b[1]}), (1, 1))


def and_system() -> DiscreteSubstrate:
    return DiscreteSubstrate(2, _gate_tpm(2, {0: lambda b: b[0] & b[1], 1: lambda b: b[0] & b[1]}), (1, 1))


def or_system() -> DiscreteSubstrate:
    return DiscreteSubstrate(2, _gate_tpm(2, {0: lambda b: b[0] | b[1], 1: lambda b: b[0] | b[1]}), (0, 0))


def xor_system() -> DiscreteSubstrate:
    return DiscreteSubstrate(2, _gate_tpm(2, {0: lambda b: b[0] ^ b[1], 1: lambda b: b[0] ^ b[1]}), (1, 1))


def mutual_copy_system() -> DiscreteSubstrate:
    return DiscreteSubstrate(2, _gate_tpm(2, {0: lambda b: b[1], 1: lambda b: b[0]}), (1, 1))


# ----------------------------------------------------------------------
# 2. Repertoires (intervention, not correlation)
# ----------------------------------------------------------------------
def cause_repertoire(sub: DiscreteSubstrate, mech: tuple[int, ...],
                     m_state: tuple[int, ...],
                     purview: tuple[int, ...]) -> dict[tuple[int, ...], float]:
    """pi_c(z_c | m): fix mechanism, average non-purview past uniformly,
    Bayes-invert with a uniform prior over past purview states."""
    rest = [i for i in range(sub.n) if i not in purview]
    scores: dict[tuple[int, ...], float] = {}
    for z in _statespace(len(purview)):
        like = 1.0
        for j, mj in zip(mech, m_state):
            tot, cnt = 0.0, 0
            for r in _statespace(len(rest)):
                full = dict(zip(purview, z))
                full.update(zip(rest, r))
                p = sub.prob1(j, _past_int(full, sub.n))
                tot += p if mj == 1 else 1.0 - p
                cnt += 1
            like *= tot / cnt
        scores[z] = like
    tot = sum(scores.values()) or 1.0
    return {z: v / tot for z, v in scores.items()}


def effect_repertoire(sub: DiscreteSubstrate, mech: tuple[int, ...],
                      m_state: tuple[int, ...],
                      purview: tuple[int, ...]) -> dict[tuple[int, ...], float]:
    """pi_e(z_e | m): do(mech = m), uniform-average the rest, per-unit
    marginals multiplied (exact for this TPM class)."""
    rest = [i for i in range(sub.n) if i not in mech]
    fix = dict(zip(mech, m_state))
    marginals = []
    for i in purview:
        tot, cnt = 0.0, 0
        for r in _statespace(len(rest)):
            full = dict(fix)
            full.update(zip(rest, r))
            tot += sub.prob1(i, _past_int(full, sub.n))
            cnt += 1
        marginals.append(tot / cnt)
    out: dict[tuple[int, ...], float] = {}
    for z in _statespace(len(purview)):
        p = 1.0
        for zi, mi in zip(z, marginals):
            p *= mi if zi == 1 else 1.0 - mi
        out[z] = p
    return out


def _subsets(units: tuple[int, ...]) -> list[tuple[int, ...]]:
    out = []
    for k in range(1, len(units) + 1):
        out.extend(tuple(sorted(c)) for c in itertools.combinations(units, k))
    return out


def _bipartitions(mech: tuple[int, ...]) -> list[tuple[tuple[int, ...], tuple[int, ...]]]:
    """Proper bipartitions, canonical (smallest unit always in part A)."""
    if len(mech) < 2:
        return []
    seen, uniq = set(), []
    for k in range(1, len(mech)):
        for combo in itertools.combinations(mech, k):
            A = tuple(sorted(combo))
            B = tuple(sorted(set(mech) - set(combo)))
            if (B, A) in seen:
                continue  # complements counted once (deterministic)
            seen.add((A, B))
            uniq.append((A, B))
    return uniq


def intrinsic_information(rep: dict[tuple[int, ...], float]) -> tuple[float, tuple[int, ...]]:
    """Box 3: ii = selectivity x informativeness at the maximal state."""
    tot = sum(rep.values()) or 1.0
    rep = {z: v / tot for z, v in rep.items()}
    z_star = min(rep, key=lambda z: (-rep[z], z))  # R3: argmax, ties -> lowest index
    u = 1.0 / len(rep)
    p = max(rep[z_star], 1e-300)
    return p * math.log2(p / u), z_star


def _mechanism_state(sub: DiscreteSubstrate, mech: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(sub.state[j] for j in mech)


def _phi_side(sub: DiscreteSubstrate, mech: tuple[int, ...],
              purviews: list[tuple[int, ...]], side: str,
              cache: dict[Any, Any]) -> tuple[float, tuple[int, ...]]:
    """Max over purviews of (ii - best-partitioned-ii); the exclusion step.

    MIP = dual partition: mechanism split (A,B) x purview split
    (ZA,ZB), each part constraining only its own slice. Single-sided
    candidates are NOT valid partitions here (see module docstring R1):
    letting one part see the whole purview lets redundant parts pose as
    integrated wholes and deflates every coupled system toward zero.
    """
    rep_fn = cause_repertoire if side == "cause" else effect_repertoire

    def _rep(M: tuple[int, ...], Z: tuple[int, ...]) -> dict[tuple[int, ...], float]:
        if not M or not Z:
            return {(): 1.0}
        key = (side, M, tuple(sub.state[j] for j in M), Z)
        if key not in cache:
            cache[key] = rep_fn(sub, M, tuple(sub.state[j] for j in M), Z)
        return cache[key]

    def _joint(rA: dict, ZA: tuple[int, ...], rB: dict,
               ZB: tuple[int, ...], Z: tuple[int, ...]) -> dict[tuple[int, ...], float]:
        ia = [Z.index(x) for x in ZA]
        ib = [Z.index(x) for x in ZB]
        out: dict[tuple[int, ...], float] = {}
        for z in _statespace(len(Z)):
            out[z] = rA.get(tuple(z[i] for i in ia), 0.0) * rB.get(tuple(z[i] for i in ib), 0.0)
        tot = sum(out.values()) or 1.0
        return {z: v / tot for z, v in out.items()}

    best_phi, best_pv = 0.0, purviews[0]
    for Z in purviews:
        ii, _ = intrinsic_information(_rep(mech, Z))
        best_part = 0.0
        # Proper dual splits ONLY (both slices nonempty): a partition must
        # cut something on both sides. Single-sided candidates (one part
        # constraining the whole purview) are not IIT partitions — they
        # let redundant parts pose as integrated wholes and deflate every
        # coupled system toward zero. This is the directional-partition
        # reading of IIT 4.0 (mechanism AND purview divide together).
        for A, B in _bipartitions(mech):
            for r in range(1, len(Z)):
                for ZA_t in itertools.combinations(Z, r):
                    ZA = tuple(sorted(ZA_t))
                    ZB = tuple(sorted(set(Z) - set(ZA)))
                    ii_p, _ = intrinsic_information(
                        _joint(_rep(A, ZA), ZA, _rep(B, ZB), ZB, Z))
                    if ii_p > best_part:
                        best_part = ii_p
        phi = max(0.0, ii - best_part)
        if phi > best_phi:
            best_phi, best_pv = phi, Z
    return best_phi, best_pv


def distinction(sub: DiscreteSubstrate, mech: tuple[int, ...],
                cache: dict[Any, Any] | None = None) -> dict[str, Any]:
    """phi_d = min(max-cause, max-effect); purviews chosen independently."""
    cache = cache if cache is not None else {}
    units = tuple(range(sub.n))
    purviews = _subsets(units)
    phi_c, zc = _phi_side(sub, mech, purviews, "cause", cache)
    phi_e, ze = _phi_side(sub, mech, purviews, "effect", cache)
    return {"mechanism": list(mech), "phi": min(phi_c, phi_e),
            "phi_cause": phi_c, "phi_effect": phi_e,
            "cause_purview": list(zc), "effect_purview": list(ze)}


# ----------------------------------------------------------------------
# 3. Relations (R2 operationalization) + Phi-structure
# ----------------------------------------------------------------------
def _extend(rep: dict[tuple[int, ...], float], from_pv: tuple[int, ...],
            to_pv: tuple[int, ...]) -> dict[tuple[int, ...], float]:
    """Marginal extension: spread uniformly outside the home purview."""
    idx = {u: k for k, u in enumerate(from_pv)}
    extra = len(to_pv) - len(from_pv)
    out: dict[tuple[int, ...], float] = {}
    for u in _statespace(len(to_pv)):
        home = tuple(u[to_pv.index(x)] if x in idx else 0 for x in from_pv)
        out[u] = rep.get(home, 0.0) / (2 ** extra)
    tot = sum(out.values()) or 1.0
    return {z: v / tot for z, v in out.items()}


def relation_phi(r1c: dict[tuple[int, ...], float], z1c: tuple[int, ...],
                 r2c: dict[tuple[int, ...], float], z2c: tuple[int, ...],
                 r1e: dict[tuple[int, ...], float], z1e: tuple[int, ...],
                 r2e: dict[tuple[int, ...], float], z2e: tuple[int, ...]) -> float:
    """Pair-relation irreducibility, R2: joint constraint minus the best
    overlap-severed assignment, normalized by |d| = 2, min over sides."""
    return min(_side_pair(r1c, z1c, r2c, z2c),
               _side_pair(r1e, z1e, r2e, z2e))


def _extend_marginal(rep: dict[tuple[int, ...], float], home_pv: tuple[int, ...],
                     keep: tuple[int, ...], U: tuple[int, ...]) -> dict[tuple[int, ...], float]:
    """Keep only `keep` units' constraint; uniform elsewhere on U."""
    if not keep:
        n = len(U)
        return {u: 1.0 / (2 ** n) for u in _statespace(n)}
    # marginalize rep down to `keep`, then extend uniformly to U
    pos = [home_pv.index(x) for x in keep]
    marg: dict[tuple[int, ...], float] = {}
    for z, v in rep.items():
        key = tuple(z[i] for i in pos)
        marg[key] = marg.get(key, 0.0) + v
    return _extend(marg, keep, U)


def _side_pair(r1: dict[tuple[int, ...], float], z1: tuple[int, ...],
               r2: dict[tuple[int, ...], float], z2: tuple[int, ...]) -> float:
    U = tuple(sorted(set(z1) | set(z2)))
    O = tuple(sorted(set(z1) & set(z2)))
    if not O:
        return 0.0  # no shared units: no relation, exactly
    e1, e2 = _extend(r1, z1, U), _extend(r2, z2, U)
    joint = {u: e1[u] * e2[u] for u in e1}
    tot = sum(joint.values()) or 1.0
    joint = {u: v / tot for u, v in joint.items()}
    ii, _ = intrinsic_information(joint)
    priv1 = tuple(x for x in z1 if x not in O)
    priv2 = tuple(x for x in z2 if x not in O)
    best = 0.0
    for keep1, keep2 in (((z1, priv2)), ((priv1, z2))):
        a = _extend_marginal(r1, z1, keep1, U)
        b = _extend_marginal(r2, z2, keep2, U)
        part = {u: a[u] * b[u] for u in a}
        t2 = sum(part.values()) or 1.0
        part = {u: v / t2 for u, v in part.items()}
        ii_p, _ = intrinsic_information(part)
        best = max(best, ii_p)
    return max(0.0, ii - best) / 2.0


def phi_structure(sub: DiscreteSubstrate) -> dict[str, Any]:
    """Full Phi-structure + system-level Phi.

    Composition sum S = sum(distinctions) + sum(relations) is reported but
    is NOT system Phi on its own (singletons in a disconnected system
    would make it nonzero — the photodiode-pair paradox). System Phi is
    the irreducibility of the WHOLE structure under the system MIP
    (IIT 3.0 big-Phi semantics, directional reading): sever each
    bipartition's cross-connections (units stop reading the other part),
    recompute the composition sum, take the minimum loss:

        Phi = S - max_{system bipartition} S_severed   (>= 0)

    Disconnected systems score EXACTLY 0 (severing changes nothing) while
    keeping their singleton distinctions visible in the report.
    """
    if sub.n > 8:
        raise ValueError(
            f"phi_structure capped at n=8 (got n={sub.n}): combinatorial wall "
            f"(mechanisms 2^n, system MIP 2^(n-1)); see "
            f"src/eci/consciousness/LIMITATIONS.md and iit4.py header"
        )
    phi, distinctions, relations = _composition_sum(sub)
    sys_phi, sys_mip = _system_mip(sub, phi)
    return {"phi": sys_phi, "composition": phi, "system_mip": sys_mip,
            "distinctions": distinctions, "relations": relations,
            "n_distinctions": len(distinctions), "n_relations": len(relations)}


def _severed(sub: DiscreteSubstrate, part_a: tuple[int, ...]) -> DiscreteSubstrate:
    """Copy of sub where units ignore inputs from the other partition:
    severed inputs are averaged uniformly (causal marginalization)."""
    set_a = set(part_a)
    tpm: dict[int, list[float]] = {}
    for j in range(sub.n):
        col = []
        for past in range(2 ** sub.n):
            bits = [(past >> i) & 1 for i in range(sub.n)]
            same_side = [i for i in range(sub.n)
                         if (i in set_a) == (j in set_a)]
            tot, cnt = 0.0, 0
            for alt in _statespace(sub.n - len(same_side)):
                full = list(bits)
                k = 0
                for i in range(sub.n):
                    if i not in same_side:
                        full[i] = alt[k]
                        k += 1
                tot += sub.prob1(j, _past_int({i: full[i] for i in range(sub.n)}, sub.n))
                cnt += 1
            col.append(tot / cnt)
        tpm[j] = col
    return DiscreteSubstrate(sub.n, tpm, sub.state)


def _composition_sum(sub: DiscreteSubstrate) -> tuple[float, list, list]:
    """Composition sum without system MIP (shared core with phi_structure)."""
    units = tuple(range(sub.n))
    cache: dict[Any, Any] = {}
    distinctions = []
    reps: dict[Any, Any] = {}
    for M in _subsets(units):
        d = distinction(sub, M, cache)
        if d["phi"] > 1e-12:
            distinctions.append(d)
            m = _mechanism_state(sub, M)
            zc, ze = tuple(d["cause_purview"]), tuple(d["effect_purview"])
            reps[("cause", M, m, zc)] = cause_repertoire(sub, M, m, zc)
            reps[("effect", M, m, ze)] = effect_repertoire(sub, M, m, ze)
    relations = []
    for i in range(len(distinctions)):
        for j in range(i + 1, len(distinctions)):
            a, b = distinctions[i], distinctions[j]
            ma = _mechanism_state(sub, tuple(a["mechanism"]))
            mb = _mechanism_state(sub, tuple(b["mechanism"]))
            zca, zea = tuple(a["cause_purview"]), tuple(a["effect_purview"])
            zcb, zeb = tuple(b["cause_purview"]), tuple(b["effect_purview"])
            pr = relation_phi(reps[("cause", tuple(a["mechanism"]), ma, zca)], zca,
                              reps[("cause", tuple(b["mechanism"]), mb, zcb)], zcb,
                              reps[("effect", tuple(a["mechanism"]), ma, zea)], zea,
                              reps[("effect", tuple(b["mechanism"]), mb, zeb)], zeb)
            if pr > 1e-12:
                relations.append({"pair": [a["mechanism"], b["mechanism"]], "phi": pr})
    total = sum(d["phi"] for d in distinctions) + sum(r["phi"] for r in relations)
    return total, distinctions, relations


def _system_mip(sub: DiscreteSubstrate, composition: float) -> tuple[float, Any]:
    """Minimum-loss system bipartition (both parts nonempty, canonical)."""
    units = tuple(range(sub.n))
    if len(units) < 2:
        return composition, None  # nothing to cut: fully integrated by vacuity
    best_kept, best_cut = -1.0, None
    seen = set()
    for k in range(1, len(units)):
        for combo in itertools.combinations(units, k):
            A = tuple(sorted(combo))
            B = tuple(sorted(set(units) - set(combo)))
            if (B, A) in seen:
                continue
            seen.add((A, B))
            kept, _, _ = _composition_sum(_severed(sub, A))
            if kept > best_kept:
                best_kept, best_cut = kept, [list(A), list(B)]
    return max(0.0, composition - best_kept), best_cut


def crosscheck_pyphi(sub: DiscreteSubstrate, run_sia: bool = True) -> dict[str, Any]:
    """Cross-check against PyPhi 1.2.0 (IIT 3.0) — validated Phase 10.

    Compares cause/effect repertoires (pre-measure machinery, where the
    two versions MUST agree — and do, to 1e-9) and reports both big-Phi
    numbers side by side (where they must NOT agree: EMD-based IIT 3.0
    vs composition-sum IIT 4.0 are incommensurate measures).

    Validated bridge (bit ordering): our LSB-first past indexing ≡
    PyPhi's state tuples element-wise (unit i ↔ position i), purview
    arrays in big-endian tuple order. Pinned by asymmetric probes
    (mutual-copy cross constraints), not just symmetric cases.

    Environment notes (honest): PyPhi 1.2.0 predates Python 3.10, so a
    function-scoped ``collections.abc`` backfill shim runs first (test-env
    compat only; touches nothing when PyPhi is absent). Multiprocessing
    is disabled (spawned workers would re-import without the shim).
    Refuses n > 3 (sia cost) and missing PyPhi (skip-with-reason).
    """
    import importlib.util
    if importlib.util.find_spec("pyphi") is None:
        return {"ok": True, "skipped": True, "reason": "pyphi not installed"}
    if sub.n > 3:
        return {"ok": True, "skipped": True, "reason": "refused: sia cost above n=3"}
    import collections
    import collections.abc
    for _n in ("Iterable", "Mapping", "Sequence", "MutableMapping"):
        if not hasattr(collections, _n):
            setattr(collections, _n, getattr(collections.abc, _n))
    import numpy as _np
    import pyphi as _pyphi
    _flags = ("PARALLEL_COMPLEX_EVALUATION", "PARALLEL_CONCEPT_EVALUATION",
              "PARALLEL_CUT_EVALUATION")
    _saved = {k: getattr(_pyphi.config, k) for k in _flags}
    try:
        for k in _flags:
            setattr(_pyphi.config, k, False)
        tpm = _np.zeros((2,) * sub.n + (sub.n,))
        for past in range(2 ** sub.n):
            bits = tuple((past >> i) & 1 for i in range(sub.n))
            for j in range(sub.n):
                tpm[bits + (j,)] = sub.prob1(j, past)
        net = _pyphi.Network(tpm)
        pym = _pyphi.Subsystem(net, state=tuple(sub.state), nodes=tuple(range(sub.n)))
        full = tuple(range(sub.n))
        probes = [((0,), (0,)), ((0,), full), (full, full)]
        diffs = []
        for mech, purv in probes:
            for direction in ("cause", "effect"):
                fn = pym.cause_repertoire if direction == "cause" else pym.effect_repertoire
                mine = (cause_repertoire if direction == "cause" else effect_repertoire)(
                    sub, mech, tuple(sub.state[j] for j in mech), purv)
                ref = _np.asarray(fn(mech, purv)).ravel()
                order = sorted(purv)
                got = _np.array([mine[tuple(b)] for b in
                                 itertools.product((0, 1), repeat=len(order))])
                # NOTE: purview tuples here are already sorted, so big-endian
                # tuple order == _statespace enumeration order used by _extend.
                diffs.append({"mech": mech, "purview": purv, "side": direction,
                              "max_abs_diff": float(_np.abs(got - ref).max())})
        worst = max(d["max_abs_diff"] for d in diffs)
        out: dict[str, Any] = {"ok": True, "skipped": False, "probes": diffs,
                               "worst_abs_diff": worst}
        if run_sia:
            out["pyphi_phi_30"] = float(_pyphi.compute.sia(pym).phi)
            out["iit4_phi_40"] = float(phi_structure(sub)["phi"])
            out["caveat"] = ("different measures (EMD IIT 3.0 vs composition "
                             "IIT 4.0): reported side by side, never equated")
        return out
    finally:
        for k, v in _saved.items():
            setattr(_pyphi.config, k, v)
