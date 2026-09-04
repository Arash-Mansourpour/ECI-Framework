"""Quantum metrology & sensing: Fisher information, Cramér-Rao, Heisenberg limit.

Theory
------
* Classical Fisher I(θ) = Σ_x p(x|θ) [∂_θ ln p]²; CR bound Var(θ̂) ≥ 1/(νI).
* Quantum Fisher F_Q[ρ_θ] = Tr(ρ L²), L the symmetric logarithmic derivative.
  For pure |ψ_θ>: F_Q = 4(⟨∂ψ|∂ψ⟩ - |⟨ψ|∂ψ⟩|²).
* Standard quantum limit (separable): Δθ ~ 1/√(νN).
  Heisenberg limit (entangled, e.g. NOON/GHZ): Δθ ~ 1/(√ν N).
* ECI application: consciousness-field phase estimation and network clock
  synchronization at Heisenberg scaling via GHZ states.
"""

from __future__ import annotations

import math
from typing import Callable, Dict, Tuple

import torch

from eci.constants import EPS
from eci.quantum import gates as qg
from eci.quantum.statevector import StatevectorSimulator

__all__ = [
    "classical_fisher_information",
    "cramer_rao_bound",
    "quantum_fisher_pure",
    "heisenberg_limit",
    "standard_quantum_limit",
    "ghz_phase_qfi",
    "noon_state_qfi",
    "ramsey_sensitivity",
]


def classical_fisher_information(
    probs_fn: Callable[[float], torch.Tensor], theta: float, dtheta: float = 1e-5
) -> float:
    """Numerical classical Fisher I(θ) via central differences."""
    p0 = probs_fn(theta).clamp_min(EPS)
    pp = probs_fn(theta + dtheta).clamp_min(EPS)
    pm = probs_fn(theta - dtheta).clamp_min(EPS)
    dp = (pp - pm) / (2 * dtheta)
    return float(((dp ** 2 / p0).sum()).item())


def cramer_rao_bound(fisher: float, n_shots: int = 1) -> float:
    """Var(θ̂) ≥ 1/(ν F)."""
    return 1.0 / max(EPS, (n_shots * fisher))


def quantum_fisher_pure(
    psi_fn: Callable[[float], torch.Tensor], theta: float, dtheta: float = 1e-5
) -> float:
    """QFI for pure parametrized states via finite-difference fidelity.

    F_Q = 8(1 - |<ψ(θ)|ψ(θ+dθ)>|)/dθ²  (→ exact as dθ→0).
    """
    a = psi_fn(theta)
    b = psi_fn(theta + dtheta)
    if a.dim() == 2:
        a = a[0]
    if b.dim() == 2:
        b = b[0]
    a = a / torch.linalg.vector_norm(a).clamp_min(EPS)
    b = b / torch.linalg.vector_norm(b).clamp_min(EPS)
    fid = abs(torch.vdot(a, b).item())
    return max(0.0, 8 * (1 - fid) / (dtheta ** 2))


def standard_quantum_limit(n_particles: int, n_shots: int = 1) -> float:
    """Δθ_SQL = 1/√(νN)."""
    return 1.0 / math.sqrt(max(1, n_shots) * max(1, n_particles))


def heisenberg_limit(n_particles: int, n_shots: int = 1) -> float:
    """Δθ_HL = 1/(√ν N)."""
    return 1.0 / (math.sqrt(max(1, n_shots)) * max(1, n_particles))


def ghz_phase_qfi(n_qubits: int) -> Dict[str, float]:
    """GHZ Ramsey sensing: F_Q = N² (Heisenberg scaling)."""
    return {
        "qfi": float(n_qubits ** 2),
        "delta_theta_single_shot": 1.0 / n_qubits,
        "scaling": "Heisenberg 1/N",
    }


def noon_state_qfi(n_photons: int) -> Dict[str, float]:
    """NOON-state interferometry: F_Q = N²."""
    return {
        "qfi": float(n_photons ** 2),
        "delta_theta_single_shot": 1.0 / n_photons,
        "scaling": "Heisenberg 1/N",
    }


def ramsey_sensitivity(n_qubits: int, entangled: bool = True, shots: int = 1024) -> Dict[str, float]:
    """Compare separable vs GHZ Ramsey sensitivity for N qubits."""
    if entangled:
        per_shot = 1.0 / n_qubits
    else:
        per_shot = 1.0 / math.sqrt(n_qubits)
    return {
        "per_shot": per_shot,
        "with_shots": per_shot / math.sqrt(shots),
        "regime": "Heisenberg" if entangled else "SQL",
        "quantum_advantage_db": 10 * math.log10(n_qubits) if entangled else 0.0,
    }
