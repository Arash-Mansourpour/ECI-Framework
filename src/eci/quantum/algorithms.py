"""Quantum algorithms: QFT, Grover, phase estimation, VQE, QAOA.

All algorithms run on the differentiable statevector simulator; the
variational ones (VQE, QAOA) optimize with full autograd through the
simulated circuit (no parameter-shift sampling needed in simulation).
"""

from __future__ import annotations

import math
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import torch

from eci.constants import EPS
from eci.quantum import gates as qg
from eci.quantum.hamiltonian import PauliSum, PauliTerm
from eci.quantum.statevector import GateOp, StatevectorSimulator

__all__ = ["qft", "inverse_qft", "grover_search", "quantum_phase_estimation", "vqe", "qaoa_maxcut"]


def _cphase(theta: float) -> torch.Tensor:
    """Controlled-phase diag(1, 1, 1, e^{i theta}) on (control, target)."""
    m = torch.eye(4, dtype=torch.complex64)
    m[3, 3] = torch.exp(torch.tensor(1j * theta))
    return m


def qft(
    state: torch.Tensor,
    sim: StatevectorSimulator,
    inverse: bool = False,
    qubits: Optional[Sequence[int]] = None,
) -> torch.Tensor:
    """Quantum Fourier transform (big-endian, q0 most significant).

    Args:
        qubits: optional ordered sub-register to transform (local index 0 is
            the most significant). Defaults to all qubits of ``sim``.
    """
    n_total = sim.n_qubits
    if qubits is None:
        qubits = list(range(n_total))
    else:
        qubits = list(qubits)
        if len(set(qubits)) != len(qubits) or any(not (0 <= q < n_total) for q in qubits):
            raise ValueError("invalid qubit subset")
    m = len(qubits)
    angle_sign = -1.0 if inverse else 1.0
    if inverse:
        for q in range(m // 2):
            state = sim.apply_2q(state, qg.SWAP, qubits[q], qubits[m - 1 - q])
        for j in reversed(range(m)):
            for k in reversed(range(j + 1, m)):
                state = sim.apply_2q(
                    state, _cphase(angle_sign * math.pi / 2 ** (k - j)), qubits[k], qubits[j]
                )
            state = sim.apply_1q(state, qg.H, qubits[j])
    else:
        for j in range(m):
            state = sim.apply_1q(state, qg.H, qubits[j])
            for k in range(j + 1, m):
                state = sim.apply_2q(
                    state, _cphase(angle_sign * math.pi / 2 ** (k - j)), qubits[k], qubits[j]
                )
        for q in range(m // 2):
            state = sim.apply_2q(state, qg.SWAP, qubits[q], qubits[m - 1 - q])
    return state


def _diffuser_ops(n: int) -> Tuple[List[GateOp], torch.Tensor]:
    """Grover diffuser D = 2|s><s| - I implemented as H^n diag H^n."""
    pre: List[GateOp] = [("1q", qg.H, q) for q in range(n)]
    diag = torch.full((2 ** n,), -1.0, dtype=torch.complex64)
    diag[0] = 1.0  # 2|0><0| - I = diag(1, -1, ..., -1)
    return pre, diag


def grover_search(
    sim: StatevectorSimulator,
    marked: Sequence[int],
    iterations: Optional[int] = None,
) -> Dict[str, object]:
    """Grover search with phase oracle; returns the final state and stats."""
    n = sim.n_qubits
    dim = sim.dim
    if not marked:
        raise ValueError("marked list must be non-empty")
    if any(not (0 <= m < dim) for m in marked):
        raise ValueError("marked index out of range")

    oracle_sign = torch.ones(dim, dtype=torch.complex64)
    for m in marked:
        oracle_sign[m] = -1.0

    n_marked = len(marked)
    if iterations is None:
        iterations = max(1, int(math.floor((math.pi / 4.0) * math.sqrt(dim / n_marked))))

    state = sim.uniform_superposition()
    pre, diag = _diffuser_ops(n)
    for _ in range(iterations):
        state = state * oracle_sign.view(1, -1)  # oracle: phase flip on marked
        state = sim.apply_ops(state, pre)
        state = state * diag.view(1, -1)
        state = sim.apply_ops(state, pre)
    probs = sim.probabilities(state)[0]
    success = float(probs[marked].sum().item())
    return {
        "state": state,
        "iterations": iterations,
        "success_probability": success,
        "top_indices": torch.topk(probs, min(4, dim)).indices.tolist(),
    }


def quantum_phase_estimation(
    sim: StatevectorSimulator,
    gate_fn: Callable[[int], torch.Tensor],
    n_counting: int,
    eigenstate_index: int = 1,
) -> Dict[str, object]:
    """Canonical QPE.

    Args:
        sim: simulator with n_qubits = n_counting + 1 (counting qubits are
            the most significant ones, the eigen-register is the last qubit).
        gate_fn: ``gate_fn(k)`` returns the 2x2 unitary U^(2^k) acting on
            the eigen-register.
        eigenstate_index: computational basis index of the eigen-register
            (0 or 1).

    Returns the estimated phase ``phi = peak_index / 2**n_counting`` where
    U|psi> = e^{2 pi i phi} |psi>.
    """
    if sim.n_qubits != n_counting + 1:
        raise ValueError(f"simulator must have exactly {n_counting + 1} qubits")
    eigen_target = sim.n_qubits - 1

    # Prepare eigenstate: apply X if needed to move |0> -> |1>.
    state = sim.zero_state()
    if eigenstate_index == 1:
        state = sim.apply_1q(state, qg.X, eigen_target)

    # Hadamards on the counting register.
    for c in range(n_counting):
        state = sim.apply_1q(state, qg.H, c)

    # Controlled-U^(2^k): control = counting qubit (n_counting-1-k) so that
    # after inverse QFT the most significant bit carries the finest phase.
    for k in range(n_counting):
        control = n_counting - 1 - k
        gate = gate_fn(2 ** k)
        state = sim.apply_controlled(state, gate, control, eigen_target)

    state = qft(state, sim, inverse=True, qubits=list(range(n_counting)))
    probs = sim.probabilities(state)[0]
    # Mask out the eigen-register bit.
    counting_probs = probs.view(-1, 2).sum(dim=1)
    peak = int(torch.argmax(counting_probs).item())
    phase = peak / (2 ** n_counting)
    return {
        "phase": phase,
        "peak_index": peak,
        "counting_probabilities": counting_probs.detach(),
        "state": state,
    }


# ---------------------------------------------------------------------------
# Variational algorithms
# ---------------------------------------------------------------------------

def _hardware_efficient_ansatz(
    sim: StatevectorSimulator,
    params: torch.Tensor,
    n_layers: int,
) -> torch.Tensor:
    """RY/RZ rotations + CNOT ring; params shape (2, n_layers, n_qubits)."""
    n = sim.n_qubits
    state = sim.zero_state()
    ry, rz = params[0], params[1]
    for layer in range(n_layers):
        for q in range(n):
            state = sim.apply_1q(state, qg.RY(ry[layer, q]), q)
            state = sim.apply_1q(state, qg.RZ(rz[layer, q]), q)
        for q in range(n):
            state = sim.apply_2q(state, qg.CNOT, q, (q + 1) % n)
    return state


def vqe(
    hamiltonian: PauliSum,
    n_qubits: int,
    n_layers: int = 2,
    steps: int = 200,
    lr: float = 0.05,
    seed: int = 42,
) -> Dict[str, object]:
    """Variational eigensolver for a Pauli-sum Hamiltonian (ground state)."""
    if n_qubits < 1 or hamiltonian.max_qubit() >= n_qubits:
        raise ValueError("hamiltonian acts on qubits outside the register")
    sim = StatevectorSimulator(n_qubits)
    g = torch.Generator().manual_seed(seed)
    params = torch.nn.Parameter(
        0.1 * torch.randn(2, n_layers, n_qubits, generator=g)
    )
    optimizer = torch.optim.Adam([params], lr=lr)
    history: List[float] = []
    for _ in range(steps):
        optimizer.zero_grad()
        state = _hardware_efficient_ansatz(sim, params, n_layers)
        energy = hamiltonian.expectation(state, sim)[0]
        loss = energy.real if torch.is_complex(energy) else energy
        loss.backward()
        optimizer.step()
        history.append(float(energy.item()))
    with torch.no_grad():
        state = _hardware_efficient_ansatz(sim, params, n_layers)
        final = float(hamiltonian.expectation(state, sim)[0].item())
    return {
        "energy": final,
        "history": history,
        "params": params.detach(),
        "state": state.detach(),
    }


def qaoa_maxcut(
    edges: Sequence[Tuple[int, int]],
    n_qubits: int,
    depth: int = 2,
    steps: int = 150,
    lr: float = 0.1,
    seed: int = 42,
) -> Dict[str, object]:
    """QAOA for MaxCut; minimizes the expected cut cost (i.e. maximizes cut)."""
    if not edges:
        raise ValueError("edges must be non-empty")
    hamiltonian = PauliSum.from_maxcut_edges(edges, n_qubits)
    sim = StatevectorSimulator(n_qubits)
    g = torch.Generator().manual_seed(seed)
    gammas = torch.nn.Parameter(0.4 * torch.randn(depth, generator=g))
    betas = torch.nn.Parameter(0.4 * torch.randn(depth, generator=g))
    optimizer = torch.optim.Adam([gammas, betas], lr=lr)

    def build_state() -> torch.Tensor:
        state = sim.uniform_superposition()
        for layer in range(depth):
            # Cost layer: e^{-i gamma C} (up to global phase).
            for term in hamiltonian.terms:
                ops = hamiltonian._pauli_evolution_ops(term, gammas[layer])
                state = sim.apply_ops(state, ops)
            # Mixer layer: e^{-i beta sum X}
            for q in range(n_qubits):
                state = sim.apply_1q(state, qg.RX(2.0 * betas[layer]), q)
        return state

    history: List[float] = []
    for _ in range(steps):
        optimizer.zero_grad()
        state = build_state()
        # MaxCut objective: cut size = sum_{(i,j)} (1 - <Z_i Z_j>)/2
        cut = torch.zeros(1, dtype=torch.float64)
        for (i, j) in edges:
            zz = sim.expectation_pauli(state, {i: "Z", j: "Z"}).double()
            cut = cut + (1.0 - zz[0]) / 2.0
        loss = -cut[0]
        loss.backward()
        optimizer.step()
        history.append(float(cut.item()))

    with torch.no_grad():
        state = build_state()
        probs = sim.probabilities(state)[0]
        best_cut = _best_cut_value(edges, n_qubits, probs)
        expected_cut = float(
            sum((1.0 - sim.expectation_pauli(state, {i: "Z", j: "Z"}).double()[0].item()) / 2.0 for (i, j) in edges)
        )
    return {
        "expected_cut": expected_cut,
        "best_cut": best_cut,
        "history": history,
        "gammas": gammas.detach(),
        "betas": betas.detach(),
        "probabilities": probs.detach(),
        "state": state.detach(),
    }


def _best_cut_value(edges: Sequence[Tuple[int, int]], n_qubits: int, probs: torch.Tensor) -> float:
    """Highest-probability bitstring evaluated as a cut."""
    best_idx = int(torch.argmax(probs).item())
    bits = [(best_idx >> (n_qubits - 1 - q)) & 1 for q in range(n_qubits)]
    return float(sum(1 for (i, j) in edges if bits[i] != bits[j]))
