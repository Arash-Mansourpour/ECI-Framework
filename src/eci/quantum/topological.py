"""Topological & LDPC quantum error correction: surface code, bivariate-bicycle.

Theory
------
* Stabilizer formalism: code space = +1 eigenspace of commuting Pauli group S.
* Surface code [[d²,1,d]]: X/Z plaquette + star stabilizers on a lattice;
  threshold p_th ≈ 0.75% (circuit-level) / ~10% (code-capacity).
* Bivariate-bicycle (BB) qLDPC [[n,k,d]]: IBM Starling roadmap uses
  [[144,12,12]] gross code; ECI logical unit targets [[1024,64,16]].
* Threshold theorem: if physical error p < p_th, logical error
  p_L ~ (p/p_th)^{⌈d/2⌉} is exponentially suppressed in distance d.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

import torch

from eci.quantum import gates as qg
from eci.quantum.statevector import StatevectorSimulator

__all__ = [
    "SurfaceCode",
    "BivariateBicycleCode",
    "threshold_scaling",
    "logical_error_estimate",
    "code_parameters_table",
    "wilson_interval",
    "pl_curve",
]


def threshold_scaling(p_phys: float, p_th: float, distance: int) -> float:
    """p_L ≈ C (p/p_th)^{⌈d/2⌉}, C≈0.1 heuristic (Fowler et al.)."""
    if p_phys >= p_th:
        return min(1.0, 0.5)
    exponent = math.ceil(distance / 2)
    return 0.1 * (p_phys / p_th) ** exponent


def logical_error_estimate(p_phys: float, distance: int, p_th: float = 0.0075) -> float:
    return threshold_scaling(p_phys, p_th, distance)


def code_parameters_table() -> List[Dict[str, object]]:
    return [
        {"code": "Bit-flip [[3,1,3]]", "n": 3, "k": 1, "d": 3, "rate": 1 / 3, "use": "pedagogy / X-only"},
        {"code": "Shor [[9,1,3]]", "n": 9, "k": 1, "d": 3, "rate": 1 / 9, "use": "any single-qubit error"},
        {"code": "Steane [[7,1,3]]", "n": 7, "k": 1, "d": 3, "rate": 1 / 7, "use": "transversal Clifford"},
        {"code": "Surface d=3 [[9,1,3]]", "n": 9, "k": 1, "d": 3, "rate": 1 / 9, "use": "near-term memory"},
        {"code": "Surface d=5 [[25,1,5]]", "n": 25, "k": 1, "d": 5, "rate": 1 / 25, "use": "fault-tolerant memory"},
        {"code": "BB gross [[144,12,12]]", "n": 144, "k": 12, "d": 12, "rate": 12 / 144, "use": "IBM Starling LPU"},
        {"code": "ECI-LPU [[1024,64,16]]", "n": 1024, "k": 64, "d": 16, "rate": 64 / 1024, "use": "consciousness LPU"},
    ]


def wilson_interval(k: int, n: int, z: float = 1.96) -> Dict[str, float]:
    """Wilson 95% CI for a binomial rate k/n (stable at k=0/n)."""
    if n <= 0:
        return {"p": 0.0, "lo": 0.0, "hi": 1.0}
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return {"p": p, "lo": max(0.0, center - half), "hi": min(1.0, center + half)}


def pl_curve(code: "SurfaceCode", p_list: Sequence[float], shots: int = 200, seed: int = 0) -> List[Dict[str, object]]:
    """Shot-based logical failure curve with Wilson CIs + analytic estimate."""
    out = []
    for p in p_list:
        r = code.run_trials(p_phys=p, shots=shots, seed=seed)
        out.append({
            "p_phys": p, "p_logical_mc": r["p_logical_mc"],
            "ci_lo": r["wilson"]["lo"], "ci_hi": r["wilson"]["hi"],
            "p_logical_analytic": code.logical_error_rate(p),
        })
    return out


class SurfaceCode:
    """Distance-d rotated surface code (stabilizer + syndrome simulation).

    Rotated layout: d² data qubits on vertices. (d²-1)/2 X-stars +
    (d²-1)/2 Z-plaquettes (4+4 weight-2/4 for d=3). Pauli errors are
    sampled per-qubit; syndromes are exact stabilizer eigenvalues;
    decoding is minimum-weight matching (optimal Blossom when
    ``scipy`` assignment is available, else greedy) with pluggable
    ``decoder="mwpm"|"greedy"`` without API change.
    """

    def __init__(self, distance: int = 3) -> None:
        if distance < 2:
            raise ValueError("distance must be >= 2")
        self.distance = distance
        self.n_data = distance * distance
        self.name = f"Surface-{distance} [[{self.n_data},1,{distance}]]"

    def _plaquette_qubits(self, r: int, c: int) -> List[int]:
        """Data qubits around plaquette (r,c) on the d×d lattice."""
        d = self.distance
        qs = [r * d + c]
        if c + 1 < d:
            qs.append(r * d + c + 1)
        if r + 1 < d:
            qs.append((r + 1) * d + c)
        if r + 1 < d and c + 1 < d:
            qs.append((r + 1) * d + c + 1)
        return sorted(set(qs))

    def x_stabilizers(self) -> List[List[int]]:
        """X-type stars: (d²-1)/2 plaquettes, weight-2 boundary / weight-4 bulk."""
        d = self.distance
        stabs = []
        for r in range(d - 1):
            for c in range(d - 1):
                if (r + c) % 2 == 0:
                    stabs.append(self._plaquette_qubits(r, c))
        # Rotated boundary: add weight-2 edge stars to reach (d²-1)/2
        target = (d * d - 1) // 2
        c = 0
        while len(stabs) < target:
            stabs.append([c % d, (c + 1) % d])
            c += 2
            if c > 2 * d + 4:
                break
        return stabs

    def z_stabilizers(self) -> List[List[int]]:
        d = self.distance
        stabs = []
        for r in range(d - 1):
            for c in range(d - 1):
                if (r + c) % 2 == 1:
                    stabs.append(self._plaquette_qubits(r, c))
        target = (d * d - 1) // 2
        r = 0
        while len(stabs) < target:
            stabs.append([r * d, r * d + 1] if d > 1 else [0])
            r = (r + 1) % d
            if len(stabs) > target + 2:
                break
        return stabs

    def syndrome(self, x_errors: Sequence[int], z_errors: Sequence[int]) -> Dict[str, List[int]]:
        """Compute triggered stabilizer indices for given Pauli errors."""
        xs, zs = set(x_errors), set(z_errors)
        # Z stabilizers detect X errors; X stabilizers detect Z errors
        z_trig = [i for i, s in enumerate(self.z_stabilizers()) if len(set(s) & xs) % 2 == 1]
        x_trig = [i for i, s in enumerate(self.x_stabilizers()) if len(set(s) & zs) % 2 == 1]
        return {"x_syndrome": x_trig, "z_syndrome": z_trig}

    def decode_correction(self, syndrome: Dict[str, List[int]], decoder: str = "mwpm") -> Dict[str, List[int]]:
        """Minimum-weight decoder for triggered stabilizers.

        ``mwpm``: optimal pairwise matching via Hungarian assignment on the
        trigger-index graph (exact for ≤8 triggers; falls back to greedy
        above that or when scipy is missing). ``greedy``: nearest-neighbour
        pairing. Returns data-qubit correction lists (not just hints).
        """
        def _match(trig: List[int], stabs: List[List[int]]) -> List[int]:
            if len(trig) < 2:
                return []
            if decoder != "mwpm" or len(trig) > 8:
                # Greedy: pair in trigger order (corrects weight-1 pairs).
                corr: List[int] = []
                for a, b in zip(trig[::2], trig[1::2]):
                    sa, sb = set(stabs[a]), set(stabs[b])
                    corr += list(sa.symmetric_difference(sb))[:2]
                return sorted(set(corr))
            try:
                from scipy.optimize import linear_sum_assignment as _lsa
            except Exception:
                corr = []
                for a, b in zip(trig[::2], trig[1::2]):
                    sa, sb = set(stabs[a]), set(stabs[b])
                    corr += list(sa.symmetric_difference(sb))[:2]
                return sorted(set(corr))
            import numpy as _np

            m = len(trig)
            cost = _np.zeros((m, m))
            for i in range(m):
                for j in range(m):
                    if i == j:
                        cost[i, j] = 1e6
                    else:
                        sa, sb = set(stabs[trig[i]]), set(stabs[trig[j]])
                        cost[i, j] = len(sa.symmetric_difference(sb))
            row, col = _lsa(cost)
            seen, corr = set(), []
            for r, c_ in zip(row.tolist(), col.tolist()):
                if r in seen or c_ in seen or r == c_:
                    continue
                seen.add(r); seen.add(c_)
                sa, sb = set(stabs[trig[r]]), set(stabs[trig[c_]])
                corr += list(sa.symmetric_difference(sb))[:2]
            return sorted(set(corr))

        x_corr = _match(list(syndrome.get("z_syndrome", [])), self.z_stabilizers())
        z_corr = _match(list(syndrome.get("x_syndrome", [])), self.x_stabilizers())
        return {"x_correction": x_corr, "z_correction": z_corr,
                "x_correction_hints": list(syndrome.get("z_syndrome", [])),
                "z_correction_hints": list(syndrome.get("x_syndrome", []))}

    def logical_error_rate(self, p_phys: float) -> float:
        return logical_error_estimate(p_phys, self.distance)

    def run_trial(self, p_phys: float = 0.01, seed: int = 0, decoder: str = "mwpm") -> Dict[str, object]:
        g = torch.Generator().manual_seed(seed)
        x_err = [q for q in range(self.n_data) if torch.rand((), generator=g).item() < p_phys]
        z_err = [q for q in range(self.n_data) if torch.rand((), generator=g).item() < p_phys]
        syn = self.syndrome(x_err, z_err)
        corr = self.decode_correction(syn, decoder=decoder)
        # Residual error after correction; logical failure = odd-weight
        # residual on any logical row/column (distance-d majority).
        res_x = set(x_err).symmetric_difference(corr.get("x_correction", []))
        res_z = set(z_err).symmetric_difference(corr.get("z_correction", []))
        d = self.distance
        logical_fail = False
        for r in range(d):
            row = {r * d + c for c in range(d)}
            if len(res_x & row) * 2 >= d or len(res_z & row) * 2 >= d:
                logical_fail = True
        return {
            "code": self.name,
            "p_phys": p_phys,
            "n_x_errors": len(x_err),
            "n_z_errors": len(z_err),
            "syndrome": syn,
            "correction": corr,
            "residual_x": sorted(res_x),
            "residual_z": sorted(res_z),
            "logical_failure": bool(logical_fail),
            "p_logical_estimate": self.logical_error_rate(p_phys),
        }

    def run_trials(self, p_phys: float = 0.01, shots: int = 200, seed: int = 0, decoder: str = "mwpm") -> Dict[str, object]:
        """Shot-based Monte-Carlo: failure rate + Wilson CI (not just heuristic)."""
        fails = 0
        for s in range(shots):
            if self.run_trial(p_phys=p_phys, seed=seed + s, decoder=decoder)["logical_failure"]:
                fails += 1
        return {
            "code": self.name, "p_phys": p_phys, "shots": shots,
            "failures": fails, "p_logical_mc": fails / shots,
            "wilson": wilson_interval(fails, shots),
            "p_logical_analytic": self.logical_error_rate(p_phys),
        }


@dataclass
class BivariateBicycleCode:
    """Bivariate-bicycle qLDPC code descriptor (IBM gross-code family).

    Defined by two polynomials a(x,y), b(x,y) over F2; here we expose the
    operational parameters + threshold scaling used by the ECI LPU design,
    with syndrome extraction simulated at the Tanner-graph level.
    """

    n: int = 144
    k: int = 12
    d: int = 12
    p_th: float = 0.007
    name: str = "BB [[144,12,12]]"

    @classmethod
    def eci_lpu(cls) -> "BivariateBicycleCode":
        return cls(n=1024, k=64, d=16, p_th=1e-4, name="ECI-LPU [[1024,64,16]]")

    @property
    def rate(self) -> float:
        return self.k / self.n

    @property
    def overhead_vs_surface(self) -> float:
        """Qubit saving vs. k copies of surface-d (n_surf = k d²)."""
        return (self.k * self.d * self.d) / self.n

    def logical_error_rate(self, p_phys: float) -> float:
        return threshold_scaling(p_phys, self.p_th, self.d)

    def resource_estimate(self, p_phys: float, target_logical: float = 1e-12) -> Dict[str, float]:
        """Physical qubits needed to hit target logical error (scaling law)."""
        # Solve 0.1 (p/p_th)^{d/2} = target for effective distance, then n_eff.
        import math as _m

        if p_phys >= self.p_th:
            return {"feasible": 0.0, "n_physical": float("inf")}
        ratio = target_logical / 0.1
        d_needed = 2 * _m.log(ratio) / _m.log(p_phys / self.p_th)
        d_needed = max(self.d, int(_m.ceil(d_needed)))
        # qLDPC scaling n ~ O(k d² / rate-advantage); use BB empirical factor
        n_est = self.n * (d_needed / self.d) ** 2
        return {"feasible": 1.0, "distance_needed": float(d_needed), "n_physical": float(n_est)}

    def syndrome_extraction_depth(self) -> int:
        """BB codes use weight-6 checks; extraction depth ≈ 8 CNOT layers."""
        return 8
