"""Key-memory sizing: what distance protects attest keys to a target pL.

Solves the threshold law 0.1*(p/p_th)^ceil(d/2) = target for d, then
reports physical-qubit cost for surface vs BB/qLDPC families. Used to
size the LPU that guards Protocol-0 signing keys.
"""

from __future__ import annotations

import math
from typing import Dict

__all__ = ["distance_for_target", "memory_cost"]


def distance_for_target(p: float, target: float = 1e-12, p_th: float = 0.0075) -> Dict:
    """Smallest odd distance with analytic pL <= target (infeasible above threshold)."""
    if p >= p_th:
        return {"feasible": False, "distance": None, "p_logical": 0.5}
    d = 3
    while d <= 31:
        pl = 0.1 * (p / p_th) ** math.ceil(d / 2)
        if pl <= target:
            return {"feasible": True, "distance": d, "p_logical": pl}
        d += 2
    return {"feasible": False, "distance": None, "p_logical": 0.1 * (p / p_th) ** 16}


def memory_cost(p: float, target: float = 1e-12, k_keys: int = 64) -> Dict:
    """Physical qubits for k logical key-qubits: surface (k*d^2) vs BB (k*d^2/12 rate edge)."""
    r = distance_for_target(p, target)
    if not r["feasible"]:
        return {"feasible": False}
    d = r["distance"]
    return {"feasible": True, "distance": d, "p_logical": r["p_logical"],
            "surface_qubits": k_keys * d * d, "bb_qubits": math.ceil(k_keys * d * d / 12)}
