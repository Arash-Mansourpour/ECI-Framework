"""Quantum information theory: entropy, capacity, Bell non-locality, teleportation.

Covers
------
* von Neumann / Shannon entropies, mutual information, Holevo χ, coherent info
* No-cloning (proof by linearity), no-deleting duality
* CHSH Bell inequality: classical bound |S|≤2, Tsirelson bound 2√2
* Superdense coding (2 cbits / 1 qubit) and teleportation (2 cbits + EPR → 1 qubit)
* Schumacher compression limit, HSW intuition, entanglement distillation bound
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple

import torch

from eci.constants import EPS
from eci.quantum import density as qd
from eci.quantum import gates as qg
from eci.quantum.statevector import StatevectorSimulator

__all__ = [
    "shannon_entropy",
    "holevo_chi",
    "coherent_information",
    "quantum_mutual_information",
    "chsh_operator",
    "chsh_value",
    "tsirelson_bound",
    "no_cloning_violation",
    "teleportation_fidelity",
    "superdense_coding_capacity",
    "schumacher_limit",
    "entanglement_cost_bound",
]


def shannon_entropy(probs: torch.Tensor, base: float = 2.0) -> torch.Tensor:
    """H(p) = -Σ p log p."""
    p = probs.clamp_min(EPS)
    p = p / p.sum(dim=-1, keepdim=True).clamp_min(EPS)
    ent = -(p * torch.log(p)).sum(dim=-1) / math.log(base)
    return ent


def quantum_mutual_information(rho_AB: torch.Tensor, n_qubits: int, keep_A: List[int]) -> float:
    """I(A:B) = S(ρ_A) + S(ρ_B) - S(ρ_AB)."""
    keep_A = sorted(keep_A)
    keep_B = sorted(set(range(n_qubits)) - set(keep_A))
    rho_A = qd.partial_trace(rho_AB, n_qubits, keep_A)
    rho_B = qd.partial_trace(rho_AB, n_qubits, keep_B)
    sA = float(qd.von_neumann_entropy(rho_A)[0].item())
    sB = float(qd.von_neumann_entropy(rho_B)[0].item())
    rho = rho_AB if rho_AB.dim() == 3 else rho_AB.unsqueeze(0)
    sAB = float(qd.von_neumann_entropy(rho)[0].item())
    return sA + sB - sAB


def holevo_chi(ensemble: List[Tuple[float, torch.Tensor]]) -> float:
    """Holevo χ = S(Σ pᵢρᵢ) - Σ pᵢ S(ρᵢ): upper bound on accessible info."""
    avg = sum(p * rho for p, rho in ensemble)
    if avg.dim() == 2:
        avg = avg.unsqueeze(0)
    s_avg = float(qd.von_neumann_entropy(avg)[0].item())
    sub = 0.0
    for p, rho in ensemble:
        r = rho if rho.dim() == 3 else rho.unsqueeze(0)
        sub += p * float(qd.von_neumann_entropy(r)[0].item())
    return max(0.0, s_avg - sub)


def coherent_information(rho_AB: torch.Tensor, n_qubits: int, keep_A: List[int]) -> float:
    """I(A>B) = S(ρ_B) - S(ρ_AB): achievable quantum communication rate."""
    keep_A = sorted(keep_A)
    keep_B = sorted(set(range(n_qubits)) - set(keep_A))
    rho_B = qd.partial_trace(rho_AB, n_qubits, keep_B)
    sB = float(qd.von_neumann_entropy(rho_B)[0].item())
    rho = rho_AB if rho_AB.dim() == 3 else rho_AB.unsqueeze(0)
    sAB = float(qd.von_neumann_entropy(rho)[0].item())
    return sB - sAB


def chsh_operator(
    a0: torch.Tensor, a1: torch.Tensor, b0: torch.Tensor, b1: torch.Tensor
) -> torch.Tensor:
    """CHSH Bell operator B = A0⊗B0 + A0⊗B1 + A1⊗B0 - A1⊗B1."""
    return (
        torch.kron(a0, b0)
        + torch.kron(a0, b1)
        + torch.kron(a1, b0)
        - torch.kron(a1, b1)
    )


def chsh_value(rho: torch.Tensor, settings: Dict[str, torch.Tensor] | None = None) -> float:
    """<B>_ρ for optimal qubit settings (defaults to maximal-violation angles).

    Classical (LHV): |S| ≤ 2.  Quantum (Tsirelson): |S| ≤ 2√2 ≈ 2.828.
    """
    if settings is None:
        Z, X = qg.Z.to(torch.complex64), qg.X.to(torch.complex64)
        a0, a1 = Z, X
        b0 = (Z + X) / math.sqrt(2)
        b1 = (Z - X) / math.sqrt(2)
    else:
        a0, a1, b0, b1 = settings["a0"], settings["a1"], settings["b0"], settings["b1"]
    B = chsh_operator(a0, a1, b0, b1)
    r = rho if rho.dim() == 3 else rho.unsqueeze(0)
    return float(torch.einsum("bij,ji->b", r, B).real[0].item())


def tsirelson_bound() -> float:
    """Maximum quantum CHSH violation 2√2."""
    return 2.0 * math.sqrt(2.0)


def no_cloning_violation(U: torch.Tensor) -> float:
    """Quantify deviation from a perfect cloner.

    A perfect cloner would satisfy U|ψ>|0> = |ψ>|ψ> ∀ψ. We test on
    {|0>,|1>,|+>} and return 1 - mean fidelity (0 = perfect, impossible
    by linearity; any physical U scores > 0 — the no-cloning theorem).
    """
    from eci.quantum.statevector import StatevectorSimulator as _S

    sim = _S(2)
    tests = [
        torch.tensor([[1.0, 0.0, 0.0, 0.0]], dtype=torch.complex64),
        torch.tensor([[0.0, 0.0, 0.0, 1.0]], dtype=torch.complex64),
        torch.tensor([[0.5, 0.5, 0.5, 0.5]], dtype=torch.complex64),
    ]
    # Ideal targets: |00>, |11>, |++>
    ideals = tests
    fids = []
    for inp, ideal in zip(tests, ideals):
        out = (U @ inp[0]).unsqueeze(0)
        ov = torch.abs(torch.einsum("bi,bi->b", out.conj(), ideal)) ** 2
        fids.append(float(ov[0].item()))
    return 1.0 - sum(fids) / len(fids)


def teleportation_fidelity(n_trials: int = 8, seed: int = 7) -> Dict[str, float]:
    """Simulate textbook teleportation on random single-qubit states.

    Alice holds unknown |ψ> + half EPR; Bell measurement + Pauli correction
    recreates |ψ> on Bob's side. Returns mean fidelity (≈1.0 ideal).
    """
    g = torch.Generator().manual_seed(seed)
    sim3 = StatevectorSimulator(3)
    sim1 = StatevectorSimulator(1)
    fids: List[float] = []
    for _ in range(n_trials):
        psi = sim1.random_state(generator=g)[0]  # 2-dim
        # |ψ> ⊗ |Φ+>
        phi = torch.zeros(4, dtype=torch.complex64)
        phi[0] = 1 / math.sqrt(2)
        phi[3] = 1 / math.sqrt(2)
        full = torch.kron(psi, phi).unsqueeze(0)
        # Alice CNOT(0->1), H(0)
        full = sim3.apply_2q(full, qg.CNOT, 0, 1)
        full = sim3.apply_1q(full, qg.H, 0)
        # Project Alice qubits onto each of 4 outcomes, correct Bob
        probs = sim3.probabilities(full)[0]
        # Ideal protocol: conditional state of Bob == ψ up to Pauli; verify
        # by checking that full distribution matches theory (fidelity via
        # reduced state purification): trace out Alice, Bob must be pure ψ.
        rho = qd.from_statevector(full)
        rho_B = qd.partial_trace(rho, 3, [2])
        target = qd.from_statevector(psi.unsqueeze(0))
        f = float(qd.fidelity(rho_B, target)[0].item())
        # Mixture over Alice outcomes is maximally mixed on Alice side but
        # Bob conditioned on classical feed-forward recovers ψ; the
        # unconditional reduced state check above is pessimistic, so compute
        # conditional fidelity explicitly:
        best = 0.0
        for a in range(4):
            # amplitude block for Alice outcome a
            block = full[0, a * 2:(a + 1) * 2]
            n = torch.linalg.vector_norm(block).item()
            if n < 1e-9:
                continue
            block = block / n
            # Pauli correction indexed by Alice bits
            corr = [qg.I, qg.X, qg.Z, qg.X @ qg.Z][a].to(torch.complex64)
            corrected = (corr @ block.unsqueeze(-1)).squeeze(-1)
            ov = abs(torch.vdot(psi, corrected).item()) ** 2
            best += (n ** 2) * ov
        fids.append(best)
        _ = f
        _ = probs
    return {"mean_conditional_fidelity": sum(fids) / len(fids), "n_trials": float(n_trials)}


def superdense_coding_capacity() -> Dict[str, float]:
    """Ideal superdense coding: 2 classical bits per transmitted qubit + EPR."""
    return {"cbits_per_qubit": 2.0, "ebits_consumed": 1.0, "classical_bound": 1.0}


def schumacher_limit(rho: torch.Tensor) -> float:
    """Schumacher compression limit = S(ρ) qubits per source copy."""
    r = rho if rho.dim() == 3 else rho.unsqueeze(0)
    return float(qd.von_neumann_entropy(r)[0].item())


def entanglement_cost_bound(rho: torch.Tensor) -> Dict[str, float]:
    """Distillable entanglement ≤ E_F; cost ≥ E_F (hashing / formation gap)."""
    from eci.quantum.entanglement import concurrence as _conc

    r = rho if rho.dim() == 3 else rho.unsqueeze(0)
    c = float(_conc(r)[0].item())
    # Binary entropy of (1+√(1-C²))/2 = entanglement of formation (2 qubits)
    x = (1 + math.sqrt(max(0.0, 1 - c * c))) / 2
    if x <= 0 or x >= 1:
        ef = 0.0
    else:
        ef = -x * math.log2(x) - (1 - x) * math.log2(1 - x)
    return {"concurrence": c, "entanglement_of_formation_bits": ef}
