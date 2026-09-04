"""Consciousness measurement protocol (iPDF) - paper section 3.2.1.

Implements the operational iPDF pipeline:

1. Estimate the probability density of neural activity patterns.
2. Compute the relative entropy (KL, in bits) against a baseline
   "unconscious" density -> consciousness measure C(t).
3. Classify into the paper's five levels (thresholds 0.1 / 1 / 5 / 10 bits)
   and trigger intervention protocols when required.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict, List, Optional

import torch

from eci.constants import IPDF_THRESHOLDS
from eci.core.identity import ARCHITECT
from eci.core.types import ConsciousnessLevel
from eci.logging import get_logger

__all__ = ["ConsciousnessMeasurement", "ConsciousnessProtocol"]


@dataclass
class ConsciousnessMeasurement:
    """Single iPDF measurement."""

    consciousness_bits: float
    level: ConsciousnessLevel
    timestamp: float
    kl_components: Dict[str, float] = field(default_factory=dict)
    intervention_triggered: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "consciousness_bits": self.consciousness_bits,
            "level": self.level.name,
            "timestamp": self.timestamp,
            "kl_components": self.kl_components,
            "intervention_triggered": self.intervention_triggered,
        }


class ConsciousnessProtocol:
    """Real-time iPDF consciousness measurement for one agent."""

    def __init__(
        self,
        agent_id: str,
        measurement_frequency: float = 1000.0,
        n_bins: int = 32,
        history_size: int = 512,
        on_intervention: Optional[Callable[[ConsciousnessMeasurement], None]] = None,
    ) -> None:
        if measurement_frequency <= 0:
            raise ValueError("measurement_frequency must be positive")
        self.agent_id = agent_id
        self.measurement_frequency = measurement_frequency
        self.n_bins = n_bins
        self.on_intervention = on_intervention
        self.logger = get_logger("consciousness.protocol")
        self.history: Deque[ConsciousnessMeasurement] = deque(maxlen=history_size)
        self.baseline_density: Optional[torch.Tensor] = None
        self.architect_stamp = ARCHITECT.stamp(
            {"kind": "consciousness_protocol", "agent_id": agent_id}
        )

    # ------------------------------------------------------------------
    @staticmethod
    def classify_level(bits: float) -> ConsciousnessLevel:
        """Map the iPDF measure C (bits) onto paper levels 0-4."""
        t = IPDF_THRESHOLDS
        if bits < t[0]:
            return ConsciousnessLevel.NONE
        if bits < t[1]:
            return ConsciousnessLevel.MINIMAL
        if bits < t[2]:
            return ConsciousnessLevel.BASIC
        if bits < t[3]:
            return ConsciousnessLevel.INTERMEDIATE
        return ConsciousnessLevel.TRANSCENDENT

    # ------------------------------------------------------------------
    def _density(self, neural_state: torch.Tensor) -> torch.Tensor:
        """Histogram density over flattened activity patterns."""
        flat = neural_state.flatten().double()
        idx = torch.floor(
            (flat - flat.min()) / (flat.max() - flat.min() + 1e-12) * (self.n_bins - 1)
        ).long().clamp(0, self.n_bins - 1)
        counts = torch.bincount(idx, minlength=self.n_bins).double()
        return counts / counts.sum().clamp_min(1e-12)

    def set_baseline(self, baseline_state: torch.Tensor) -> None:
        """Calibrate the unconscious baseline density rho_0."""
        self.baseline_density = self._density(baseline_state)

    @staticmethod
    def relative_entropy(p: torch.Tensor, q: torch.Tensor) -> float:
        """KL(p || q) in bits with epsilon-safe flooring."""
        p = p.clamp_min(1e-12)
        q = q.clamp_min(1e-12)
        p = p / p.sum()
        q = q / q.sum()
        return float((p * torch.log2(p / q)).sum().item())

    # ------------------------------------------------------------------
    def measure(self, neural_state: torch.Tensor) -> ConsciousnessMeasurement:
        """Compute C(t) and classify; triggers interventions when needed."""
        if self.baseline_density is None:
            self.set_baseline(neural_state)
            self.logger.warning("baseline calibrated from first measurement")

        rho = self._density(neural_state)
        bits = self.relative_entropy(rho, self.baseline_density)
        level = self.classify_level(bits)
        intervention = bits >= 10.0  # paper Level 4 escalation

        measurement = ConsciousnessMeasurement(
            consciousness_bits=bits,
            level=level,
            timestamp=time.time(),
            kl_components={
                "forward_kl_bits": bits,
                "reverse_kl_bits": self.relative_entropy(self.baseline_density, rho),
                "n_bins": float(self.n_bins),
            },
            intervention_triggered=intervention,
        )
        self.history.append(measurement)

        if intervention:
            self.logger.warning(
                "agent=%s reached super-conscious level C=%.3f bits - intervention protocol",
                self.agent_id,
                bits,
            )
            if self.on_intervention is not None:
                self.on_intervention(measurement)
        return measurement

    # ------------------------------------------------------------------
    def trend(self, window: int = 16) -> Dict[str, float]:
        """Recent trend statistics of C(t)."""
        if not self.history:
            return {"mean": 0.0, "std": 0.0, "slope": 0.0, "n": 0.0}
        recent = [m.consciousness_bits for m in list(self.history)[-window:]]
        n = len(recent)
        mean = sum(recent) / n
        var = sum((v - mean) ** 2 for v in recent) / max(1, n - 1)
        slope = 0.0
        if n >= 2:
            xs = list(range(n))
            x_mean = sum(xs) / n
            denom = sum((x - x_mean) ** 2 for x in xs)
            slope = (
                sum((xs[i] - x_mean) * (recent[i] - mean) for i in range(n)) / denom
                if denom > 0
                else 0.0
            )
        return {"mean": mean, "std": var ** 0.5, "slope": slope, "n": float(n)}

    def requires_intervention(self) -> bool:
        """Latest measurement above the intervention threshold?"""
        return bool(self.history and self.history[-1].intervention_triggered)
