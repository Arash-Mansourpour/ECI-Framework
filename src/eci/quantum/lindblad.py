"""Open-system dynamics: Lindblad master equation and feedback stabilization.

d rho / dt = -i[H, rho] + sum_k ( L_k rho L_k^dag - 1/2 {L_k^dag L_k, rho} )

Integrated with fixed-step RK4. The feedback stabilizer implements the
"mock quantum stabilization" concept from ECI paper section 2.3.2: a
classical closed-loop controller that monitors a coherence observable and
steers a Hamiltonian drive to counteract decoherence.
"""

from __future__ import annotations

from typing import Callable, List, Optional, Sequence, Tuple

import torch

from eci.constants import EPS
from eci.quantum import density as qd

__all__ = [
    "lindblad_derivative",
    "lindblad_evolve",
    "coherence_measure",
    "MockQuantumStabilizer",
]


def lindblad_derivative(
    rho: torch.Tensor,
    hamiltonian: torch.Tensor,
    collapse_ops: Sequence[torch.Tensor],
) -> torch.Tensor:
    """Right-hand side of the Lindblad master equation."""
    commutator = -1j * (hamiltonian @ rho - rho @ hamiltonian)
    dissipator = torch.zeros_like(rho)
    for L in collapse_ops:
        L = L.to(rho.dtype)
        LdL = L.conj().T @ L
        dissipator = dissipator + L @ rho @ L.conj().T - 0.5 * (LdL @ rho + rho @ LdL)
    return commutator + dissipator


def lindblad_evolve(
    rho0: torch.Tensor,
    hamiltonian: torch.Tensor,
    collapse_ops: Sequence[torch.Tensor],
    n_steps: int,
    dt: float = 0.05,
    hamiltonian_schedule: Optional[Callable[[int, torch.Tensor], torch.Tensor]] = None,
) -> List[torch.Tensor]:
    """RK4-integrate the Lindblad equation; returns the trajectory.

    Args:
        rho0: initial density matrix ``(batch, D, D)``.
        hamiltonian: time-independent part H ``(D, D)``.
        collapse_ops: Lindblad operators ``L_k``.
        n_steps: number of integration steps.
        dt: step size.
        hamiltonian_schedule: optional ``H(t_index, rho) -> H`` hook used by
            feedback controllers.
    """
    if rho0.dim() == 2:
        rho0 = rho0.unsqueeze(0)
    if rho0.dim() != 3 or rho0.shape[-1] != rho0.shape[-2]:
        raise ValueError(
            f"rho0 must be a statevector (D,) or density matrix (batch, D, D), "
            f"got {tuple(rho0.shape)}"
        )
    if hamiltonian.shape[-1] != rho0.shape[-1]:
        raise ValueError(
            f"hamiltonian dimension {tuple(hamiltonian.shape)} does not match "
            f"state dimension {rho0.shape[-1]}"
        )
    hamiltonian = hamiltonian.to(rho0.dtype)

    def rhs(idx: int, rho: torch.Tensor) -> torch.Tensor:
        h = hamiltonian_schedule(idx, rho) if hamiltonian_schedule is not None else hamiltonian
        return lindblad_derivative(rho, h.to(rho.dtype), collapse_ops)

    def project(rho: torch.Tensor) -> torch.Tensor:
        # Hermitize + renormalize to fight numerical drift
        rho = 0.5 * (rho + rho.conj().transpose(-1, -2))
        tr = torch.einsum("bii->b", rho).real.clamp_min(EPS)
        return rho / tr.view(-1, 1, 1)

    trajectory = [project(rho0)]
    rho = rho0
    for step in range(n_steps):
        k1 = rhs(step, rho)
        k2 = rhs(step, rho + 0.5 * dt * k1)
        k3 = rhs(step, rho + 0.5 * dt * k2)
        k4 = rhs(step, rho + dt * k3)
        rho = project(rho + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4))
        trajectory.append(rho)
    return trajectory


def coherence_measure(rho: torch.Tensor) -> torch.Tensor:
    """Normalized off-diagonal (l1-norm) coherence, shape ``(batch,)``.

    C(rho) = 2 * sum_{i != j} |rho_ij| / (d^2 - d), in [0, 1] for states
    with bounded off-diagonal mass.
    """
    d = rho.shape[-1]
    if d < 2:
        return torch.zeros(rho.shape[0], device=rho.device)
    eye = torch.eye(d, dtype=torch.bool, device=rho.device)
    mask = (~eye).to(rho.real.dtype)
    total = (torch.abs(rho) * mask).sum(dim=(-1, -2))
    return 2.0 * total / (d * (d - 1))


class MockQuantumStabilizer:
    """Closed-loop decoherence suppression (paper section 2.3.2).

    The controller measures the normalized coherence C(rho) each step and
    modulates a phase-drive Hamiltonian H_fb = g * (C* - C) * D where D is a
    Hermitian drive operator. This is a classical feedback heuristic that
    mimics quantum error suppression; it is honest about being
    simulation-level research tooling.
    """

    def __init__(
        self,
        target_coherence: float = 0.9,
        feedback_gain: float = 2.0,
        max_drive: float = 5.0,
    ) -> None:
        if target_coherence < 0 or target_coherence > 1:
            raise ValueError("target_coherence must be in [0, 1]")
        self.target_coherence = target_coherence
        self.feedback_gain = feedback_gain
        self.max_drive = max_drive
        self.history: List[float] = []

    def _drive_operator(self, rho: torch.Tensor) -> torch.Tensor:
        """Hermitian drive built from the off-diagonal structure of rho."""
        d = rho.shape[-1]
        eye = torch.eye(d, dtype=rho.dtype, device=rho.device)
        off_diag = rho * (1.0 - eye)
        drive = off_diag.real + off_diag.real.conj().transpose(-1, -2)
        return drive

    def schedule(self, collapse_ops: Sequence[torch.Tensor]) -> Callable[[int, torch.Tensor], torch.Tensor]:
        """Return a hamiltonian_schedule callback for :func:`lindblad_evolve`."""

        def schedule(step: int, rho: torch.Tensor) -> torch.Tensor:
            c = float(coherence_measure(rho)[0].item())
            self.history.append(c)
            error = self.target_coherence - c
            gain = self.feedback_gain * max(-self.max_drive, min(self.max_drive, error))
            return gain * self._drive_operator(rho)

        return schedule
