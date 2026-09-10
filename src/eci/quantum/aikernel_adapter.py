"""Phase 2a — quantum adapter: VQE loss literally IS variational free energy.

Framing (documented, no hand-waving): VQE is inference over which pure
state the register is in. The observation model declares that we observe
an *aspiration energy* ``e_target`` through the Hamiltonian's own Pauli
decomposition, plus isotropic slack eps (keeps R positive-definite):

    observables  O_k = Hamiltonian Pauli terms,  c_k = their coefficients
    R^{-1}       = (1/R_e)·c·cᵀ + eps·I            (rank-1 energy channel + slack)
    o            = (e_target / ||c||²)·c           (so cᵀo = e_target exactly)

Then inaccuracy = ½(o−m)ᵀR⁻¹(o−m)
                = ½(E_target − ⟨H⟩)²/R_e  +  (eps/2)·||o − m||²,
i.e. energy descent toward the aspiration level plus a small pull toward
the declared per-term targets. Complexity D(ρ || I/D) regularizes toward
the maximally-mixed prior (the honest uninformative prior = max entropy).

Set e_target below the ground energy and minimizing F descends ⟨H⟩; the
complexity term only biases the endpoint slightly toward mixed states
(measured in tests, reported, bounded). Nothing in existing public APIs
changed: ``vqe()`` is untouched; ``vqe_aikernel()`` is the opt-in F-loop
and ``VQEContributor`` is the StateContributor adapter.
"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

import torch

from eci.aikernel.functors import default_paulis
from eci.aikernel.generative_model import GenerativeState
from eci.quantum import density as qdensity
from eci.quantum.aikernel_likelihood import energy_likelihood
from eci.quantum.algorithms import _hardware_efficient_ansatz
from eci.quantum.hamiltonian import PauliSum
from eci.quantum.statevector import StatevectorSimulator

__all__ = ["VQEContributor", "vqe_aikernel", "tfi_hamiltonian"]


def tfi_hamiltonian(n_qubits: int = 2, J: float = 1.0, h: float = 1.0) -> PauliSum:
    """Transverse-field Ising with open chain: -J·ΣZZ - h·ΣX."""
    from eci.quantum.hamiltonian import PauliTerm
    terms = [PauliTerm(-J, {i: "Z", i + 1: "Z"}) for i in range(n_qubits - 1)]
    terms += [PauliTerm(-h, {i: "X"}) for i in range(n_qubits)]
    return PauliSum(terms)


class VQEContributor:
    """StateContributor wrapping the hardware-efficient VQE loop."""

    def __init__(self, hamiltonian: PauliSum, n_qubits: int, n_layers: int = 2,
                 e_target: float = -4.0, R_e: float = 1.0, eps: float = 1e-3,
                 lr: float = 0.05, seed: int = 42) -> None:
        if hamiltonian.max_qubit() >= n_qubits:
            raise ValueError("hamiltonian acts on qubits outside the register")
        self.hamiltonian = hamiltonian
        self.n_qubits = n_qubits
        self.n_layers = n_layers
        self.sim = StatevectorSimulator(n_qubits)
        g = torch.Generator().manual_seed(seed)
        self.params = torch.nn.Parameter(
            0.1 * torch.randn(2, n_layers, n_qubits, generator=g))
        self.opt = torch.optim.Adam([self.params], lr=lr)
        self.obs_labels, self.obs_target, self.R = energy_likelihood(
            hamiltonian, n_qubits, e_target, R_e, eps)
        self.e_target = e_target
        self._state: torch.Tensor | None = None
        self._rho: torch.Tensor | None = None
        self.f_history: List[float] = []
        self.e_history: List[float] = []

    # -- loop -----------------------------------------------------------
    def _forward(self) -> torch.Tensor:
        state = _hardware_efficient_ansatz(self.sim, self.params, self.n_layers)
        rho = qdensity.from_statevector(state)[0]  # (D, D), keeps autograd graph
        self._state, self._rho = state, rho
        return rho

    def loss_parts(self) -> Dict[str, torch.Tensor]:
        from eci.aikernel.free_energy import quantum_free_energy
        rho = self._rho if self._rho is not None else self._forward()
        return quantum_free_energy(rho, self.obs_labels, self.obs_target, self.R)

    def step(self) -> Dict[str, float]:
        # NOTE: cached _rho from the no_grad tracking pass carries no graph,
        # so every step starts from a fresh attached forward (one extra
        # forward per step; documented cost of keeping loss_parts pure).
        self._rho, self._state = None, None
        self.opt.zero_grad()
        parts = self.loss_parts()
        parts["total"].backward()
        self.opt.step()
        with torch.no_grad():
            rho = self._forward()
            e = float(self.hamiltonian.expectation(self._state, self.sim)[0].real.item())
        self._rho, self._state = None, None  # invalidate no-grad tensors
        f = float(parts["total"].detach().item())
        self.f_history.append(f)
        self.e_history.append(e)
        return {"F": f, "energy": e}

    def run(self, steps: int) -> Dict[str, Any]:
        for _ in range(steps):
            self.step()
        return {"F_history": list(self.f_history), "e_history": list(self.e_history),
                "F_final": self.f_history[-1], "energy_final": self.e_history[-1]}

    # -- StateContributor contract ---------------------------------------
    def posterior(self) -> GenerativeState:
        rho = self._rho if self._rho is not None else self._forward()
        return GenerativeState.from_density(
            rho.detach(), self.n_qubits, default_paulis(self.n_qubits))

    def update(self, observation: torch.Tensor) -> GenerativeState:
        """Assimilate: observation[0] becomes the new aspiration energy, one step."""
        self.e_target = float(observation.reshape(-1)[0].item())
        self.obs_labels, self.obs_target, self.R = energy_likelihood(
            self.hamiltonian, self.n_qubits, self.e_target, 1.0, 1e-3)
        self.step()
        return self.posterior()

    def free_energy_contribution(self) -> torch.Tensor:
        return self.loss_parts()["total"]


def vqe_aikernel(hamiltonian: PauliSum, n_qubits: int, n_layers: int = 2,
                 steps: int = 200, lr: float = 0.05, seed: int = 42,
                 e_target: float = -4.0, R_e: float = 1.0,
                 eps: float = 1e-3) -> Dict[str, object]:
    """Opt-in VQE loop whose loss is literally kernel F (mirrors vqe())."""
    opt = VQEContributor(hamiltonian, n_qubits, n_layers, e_target, R_e, eps, lr, seed)
    out = opt.run(steps)
    out["contributor"] = opt
    out["params"] = opt.params.detach()
    return out
