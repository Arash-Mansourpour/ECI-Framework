"""Mock quantum theory for classical subsystems (paper section 2.3.2).

Implements the mock Planck constant hbar_mock = S_char / (2*pi*N_dof) and
the coherence-scale check of Theorem 2.7, providing quantum-like scaling
for purely classical ECI components.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List

import torch

from eci.constants import REDUCED_PLANCK_CONSTANT

__all__ = ["mock_planck_constant", "mock_coherence_scale", "MockOscillatorEnsemble"]


def mock_planck_constant(action_scale: float, n_dof: int) -> float:
    """hbar_mock = S_char / (2 * pi * N_dof)."""
    if action_scale <= 0:
        raise ValueError("action_scale must be positive")
    if n_dof < 1:
        raise ValueError("n_dof must be >= 1")
    return action_scale / (2.0 * math.pi * n_dof)


def mock_coherence_scale(energy: float, frequency: float, hbar_mock: float) -> float:
    """Coherence ratio E / (hbar_mock * omega); quantum-like regime when ~1."""
    if frequency <= 0:
        raise ValueError("frequency must be positive")
    return energy / (hbar_mock * frequency)


@dataclass
class MockOscillatorEnsemble:
    """Ensemble of damped classical oscillators with mock-quantum scaling.

    Each oscillator evolves as x'' = -omega^2 x - gamma x' + drive, with a
    discretization step scaled by hbar_mock so that the phase-space action
    per step approaches the mock quantum scale (Theorem 2.7).
    """

    n_oscillators: int
    omega: float = 1.0
    gamma: float = 0.02
    seed: int = 42

    def __post_init__(self) -> None:
        if self.n_oscillators < 1:
            raise ValueError("n_oscillators must be >= 1")
        g = torch.Generator().manual_seed(self.seed)
        self.position = torch.randn(self.n_oscillators, generator=g) * 0.1
        self.velocity = torch.zeros(self.n_oscillators)
        self.action_scale = 1.0  # characteristic classical action S_char
        self.hbar_mock = mock_planck_constant(self.action_scale, self.n_oscillators)
        self._g = g
        self.energy_history: List[float] = []

    def step(self, drive: torch.Tensor | None = None, dt: float = 0.01) -> torch.Tensor:
        """Advance one semi-implicit Euler step; returns total energy."""
        if drive is None:
            drive = torch.zeros_like(self.position)
        acceleration = -(self.omega ** 2) * self.position - self.gamma * self.velocity + drive
        self.velocity = self.velocity + acceleration * dt
        self.position = self.position + self.velocity * dt
        energy = float(
            (0.5 * self.velocity ** 2 + 0.5 * (self.omega * self.position) ** 2).sum().item()
        )
        self.energy_history.append(energy)
        return self.position.clone()

    def coherence_indicator(self) -> float:
        """Ratio of per-oscillator action to the mock Planck constant."""
        action = 0.5 * float(
            (self.position.abs() * self.velocity.abs() * self.omega).sum().item()
        ) / self.n_oscillators
        return action / (self.hbar_mock + 1e-30)

    def real_planck_ratio(self) -> float:
        """Diagnostics: hbar_mock relative to the physical reduced Planck constant."""
        return self.hbar_mock / REDUCED_PLANCK_CONSTANT
