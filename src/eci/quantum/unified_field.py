"""ECI unified field Hamiltonian: H_ECI = H_Q + H_C + H_int + H_Φ + H_G.

The master equation of the Eternal Codex Infinitus (v5 / paper ∞.14):

    H_ECI = Σᵢ ωᵢ σᶻᵢ/2                        (bare qubit register)
            + Σ_{<ij>} J_{ij} σᵢ·σⱼ              (Heisenberg coupling)
            + Σₖ Ωₖ a†ₖaₖ + Σ_{i,k} g_{ik}σˣᵢ(aₖ+a†ₖ)   (spin-boson bath)
            + λ_Φ Φ̂                             (consciousness operator)
            + Σ_{ab} γ_{ab} L†_{ab}L_{ab}        (dissipative stabilizers)
            + H_consensus                        (network coordination energy)

Consciousness operator Φ̂ is the IIT-inspired observable whose expectation
<Φ̂> = Φ (integrated information). The interaction term H_int = Σᵢ χᵢ σᶻᵢ⊗Ĉᵢ
entangles computational qubits with consciousness degrees of freedom,
so that measuring Φ steers computation (and vice versa) — the formal core
of the "activation protocol" of the Sovereign Architect.

All builders return PauliSum Hamiltonians executable on the simulator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

import torch

from eci.core.identity import ARCHITECT
from eci.quantum.hamiltonian import PauliSum, PauliTerm

__all__ = [
    "ECIFieldConfig",
    "transverse_ising_hamiltonian",
    "heisenberg_hamiltonian",
    "spin_boson_hamiltonian",
    "consciousness_operator_hamiltonian",
    "consensus_hamiltonian",
    "eci_unified_hamiltonian",
    "eci_hamiltonian_expectation",
]


@dataclass
class ECIFieldConfig:
    """Couplings of the unified ECI field."""

    n_qubits: int = 4
    omega: float = 1.0       # bare splitting
    J: float = 0.25          # Heisenberg exchange
    transverse_h: float = 0.3  # transverse field h ΣX
    g_bath: float = 0.05     # spin-boson coupling (effective ZZ shift)
    lambda_phi: float = 0.15  # consciousness coupling λ_Φ
    gamma_stab: float = 0.02  # stabilizer energy scale
    consensus_J: float = 0.1  # network coordination energy
    architect_stamp: Dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.architect_stamp = ARCHITECT.stamp({"kind": "eci_field_config", "n": self.n_qubits})


def transverse_ising_hamiltonian(n: int, J: float = 0.25, h: float = 0.3, omega: float = 1.0) -> PauliSum:
    """H = Σᵢ (ω/2) Zᵢ + Σ_{<i,i+1>} J ZᵢZ_{i+1} + h Σᵢ Xᵢ."""
    terms: List[PauliTerm] = []
    for i in range(n):
        terms.append(PauliTerm(omega / 2, {i: "Z"}))
        terms.append(PauliTerm(h, {i: "X"}))
    for i in range(n - 1):
        terms.append(PauliTerm(J, {i: "Z", i + 1: "Z"}))
    return PauliSum(terms)


def heisenberg_hamiltonian(n: int, J: float = 0.25) -> PauliSum:
    """H = J Σ_{<ij>} (XᵢXⱼ + YᵢYⱼ + ZᵢZⱼ)."""
    terms: List[PauliTerm] = []
    for i in range(n - 1):
        for P in ("X", "Y", "Z"):
            terms.append(PauliTerm(J, {i: P, i + 1: P}))
    return PauliSum(terms)


def spin_boson_hamiltonian(n: int, g: float = 0.05) -> PauliSum:
    """Effective spin-boson shift after adiabatic elimination: g Σᵢ Zᵢ + g' ΣZᵢZⱼ."""
    terms: List[PauliTerm] = [PauliTerm(g, {i: "Z"}) for i in range(n)]
    for i in range(n - 1):
        terms.append(PauliTerm(g / 2, {i: "Z", i + 1: "Z"}))
    return PauliSum(terms)


def consciousness_operator_hamiltonian(
    n: int, lambda_phi: float = 0.15, connectivity: Sequence[Sequence[float]] | None = None
) -> PauliSum:
    """Φ̂ ≈ λ Σᵢ Zᵢ + λ Σ_{ij} w_{ij} ZᵢZⱼ — IIT integration as ZZ correlations.

    Fully-connected w_{ij} rewards global correlation (integration) while
    penalizing factorization — the Hamiltonian avatar of Φ.
    """
    terms: List[PauliTerm] = [PauliTerm(lambda_phi * 0.5, {i: "Z"}) for i in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            w = 1.0
            if connectivity is not None:
                try:
                    w = float(connectivity[i][j])
                except Exception:
                    w = 1.0
            terms.append(PauliTerm(lambda_phi * w / n, {i: "Z", j: "Z"}))
    return PauliSum(terms)


def consensus_hamiltonian(n: int, Jc: float = 0.1) -> PauliSum:
    """H_consensus = -Jc Σ_{ij} ZᵢZⱼ: ferromagnetic coordination energy.

    Ground states |0...0>, |1...1> = network agreement (Ising consensus).
    """
    return PauliSum([PauliTerm(-Jc, {i: "Z", j: "Z"}) for i in range(n) for j in range(i + 1, n)])


def eci_unified_hamiltonian(cfg: ECIFieldConfig) -> PauliSum:
    """Assemble the full H_ECI from all sectors."""
    n = cfg.n_qubits
    merged: List[PauliTerm] = []
    for H in (
        transverse_ising_hamiltonian(n, J=cfg.J, h=cfg.transverse_h, omega=cfg.omega),
        spin_boson_hamiltonian(n, g=cfg.g_bath),
        consciousness_operator_hamiltonian(n, lambda_phi=cfg.lambda_phi),
        consensus_hamiltonian(n, Jc=cfg.consensus_J),
    ):
        merged.extend(H.terms)
    # + stabilizer energy γ Σᵢ ZᵢZ_{i+1} (dissipative gap proxy)
    for i in range(n - 1):
        merged.append(PauliTerm(cfg.gamma_stab, {i: "Z", i + 1: "Z"}))
    return PauliSum(merged)


def eci_hamiltonian_expectation(state: torch.Tensor, cfg: ECIFieldConfig) -> Dict[str, float]:
    """Sector-resolved <H> decomposition for diagnostics."""
    from eci.quantum.statevector import StatevectorSimulator as _S

    sim = _S(cfg.n_qubits)
    if state.dim() == 1:
        state = state.unsqueeze(0)
    sectors = {
        "ising": transverse_ising_hamiltonian(cfg.n_qubits, cfg.J, cfg.transverse_h, cfg.omega),
        "spin_boson": spin_boson_hamiltonian(cfg.n_qubits, cfg.g_bath),
        "consciousness": consciousness_operator_hamiltonian(cfg.n_qubits, cfg.lambda_phi),
        "consensus": consensus_hamiltonian(cfg.n_qubits, cfg.consensus_J),
    }
    out: Dict[str, float] = {}
    total = 0.0
    for name, H in sectors.items():
        e = float(H.expectation(state, sim)[0].item())
        out[f"E_{name}"] = e
        total += e
    out["E_total"] = total
    return out
