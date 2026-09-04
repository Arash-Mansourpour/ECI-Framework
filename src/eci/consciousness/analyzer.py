"""Ultra-advanced consciousness analyzer.

Combines IIT 4.0 (gaussian/quantum/discrete Phi), neural complexity
(LZ76 + sample entropy + spectral entropy), optional quantum-coherence
contribution, self-awareness (meta-cognition proxies), temporal
consistency, information integration and causal density into a single
:class:`ConsciousnessProfile` stamped by the sovereign architect.
"""

from __future__ import annotations

import time
from collections import deque
from typing import Any, Deque, Dict, List, Optional

import numpy as np
import torch

from eci.constants import PHI_THRESHOLDS
from eci.core.device import get_device
from eci.core.identity import ARCHITECT
from eci.core.types import ConsciousnessLevel, ConsciousnessProfile, QuantumState
from eci.logging import get_logger
from eci.consciousness.iit import IntegratedInformationTheory
from eci.consciousness import metrics as cmetrics

__all__ = ["AdvancedConsciousnessAnalyzer"]


class AdvancedConsciousnessAnalyzer:
    """Multi-theory consciousness analyzer with history tracking."""

    def __init__(
        self,
        device: Optional[torch.device] = None,
        phi_method: str = "gaussian",
        history_size: int = 256,
    ) -> None:
        self.device = device if device is not None else get_device()
        self.phi_method = phi_method
        self.logger = get_logger("consciousness.analyzer")
        self.iit = IntegratedInformationTheory(self.device)
        self.measurement_history: Deque[Dict[str, Any]] = deque(maxlen=history_size)

    # ------------------------------------------------------------------
    async def analyze_consciousness(
        self,
        neural_data: torch.Tensor,
        connectivity: Optional[torch.Tensor] = None,
        quantum_state: Optional[QuantumState] = None,
        method: Optional[str] = None,
    ) -> ConsciousnessProfile:
        """Comprehensive consciousness analysis of ``[time, neurons]`` data."""
        neural_data = neural_data.to(self.device).double()
        if neural_data.dim() == 1:
            neural_data = neural_data.unsqueeze(1)
        if connectivity is None:
            if neural_data.shape[1] < 2:
                connectivity = torch.ones(1, 1, device=self.device)
            else:
                connectivity = torch.clamp(torch.corrcoef(neural_state_T(neural_data)), -1.0, 1.0)
        connectivity = connectivity.to(self.device).double()

        # 1. Integrated information
        phi_results = self.iit.calculate_phi(
            neural_data, connectivity, method=method or self.phi_method
        )
        phi_value = phi_results["phi_total"]

        # 2. Neural complexity
        neural_complexity = self._calculate_neural_complexity(neural_data)

        # 3. Quantum coherence contribution
        quantum_coherence = 0.0
        if quantum_state is not None:
            quantum_coherence = self._quantum_contribution(quantum_state)

        # 4. Self-awareness (meta-cognitive proxies)
        self_awareness = self._self_awareness(neural_data, connectivity, phi_value)

        # 5. Temporal consistency
        temporal_consistency = self._temporal_consistency(neural_data)

        # 6. Information integration
        information_integration = self._information_integration(neural_data)

        # 7. Causal density
        causal_density = self._causal_density(connectivity)

        # 8. Signature
        signature = self._signature(neural_data)

        profile = ConsciousnessProfile(
            phi_value=phi_value,
            phi_components=phi_results,
            consciousness_level=self.level_from_phi(phi_value),
            neural_complexity=neural_complexity,
            quantum_coherence=quantum_coherence,
            self_awareness_score=self_awareness,
            temporal_consistency=temporal_consistency,
            information_integration=information_integration,
            causal_density=causal_density,
            signature_pattern=signature,
            architect_stamp=ARCHITECT.stamp(
                {"kind": "consciousness_profile", "phi": phi_value}
            ),
        )

        self.measurement_history.append(
            {"timestamp": time.time(), "profile": profile}
        )
        return profile

    # ------------------------------------------------------------------
    @staticmethod
    def level_from_phi(phi: float) -> ConsciousnessLevel:
        thresholds = PHI_THRESHOLDS
        if phi < thresholds[0]:
            return ConsciousnessLevel.NONE
        if phi < thresholds[1]:
            return ConsciousnessLevel.MINIMAL
        if phi < thresholds[2]:
            return ConsciousnessLevel.BASIC
        if phi < thresholds[3]:
            return ConsciousnessLevel.INTERMEDIATE
        if phi < thresholds[4]:
            return ConsciousnessLevel.ADVANCED
        if phi < thresholds[5]:
            return ConsciousnessLevel.EMERGENT
        return ConsciousnessLevel.TRANSCENDENT

    # ------------------------------------------------------------------
    def _calculate_neural_complexity(self, neural_data: torch.Tensor) -> float:
        data_np = neural_data.detach().cpu().numpy()
        lz = cmetrics.lempel_ziv_complexity(data_np)
        se = cmetrics.sample_entropy(neural_data)
        spe = cmetrics.spectral_entropy(neural_data)
        return float(min(1.0, 0.4 * lz + 0.3 * se + 0.3 * spe))

    def _quantum_contribution(self, quantum_state: QuantumState) -> float:
        coherence = 0.0
        if quantum_state.density_matrix is not None:
            from eci.quantum.lindblad import coherence_measure

            coherence = float(coherence_measure(quantum_state.density_matrix)[0].item())
        combined = (
            0.5 * coherence
            + 0.3 * quantum_state.entanglement_entropy
            + 0.2 * quantum_state.purity
        )
        return float(min(combined, 1.0))

    def _self_awareness(
        self,
        neural_data: torch.Tensor,
        connectivity: torch.Tensor,
        phi_value: float,
    ) -> float:
        autocorr = float(torch.nan_to_num(
            torch.as_tensor(cmetrics.autocorrelation(neural_data)), nan=0.0
        ).item())
        hub = float(torch.nan_to_num(
            torch.as_tensor(self._hub_activity(connectivity)), nan=0.0
        ).item())
        self_ref = float(torch.nan_to_num(
            torch.as_tensor(self._self_reference(neural_data)), nan=0.0
        ).item())
        # Normalize unbounded Phi to [0,1) so it can't saturate the mix:
        # phi_norm = 1 - exp(-phi).  Preserves ordering, bounds influence.
        import math as _m

        phi_norm = 1.0 - _m.exp(-max(0.0, phi_value))
        combined = 0.3 * phi_norm + 0.25 * autocorr + 0.25 * hub + 0.2 * self_ref
        return float(min(max(combined, 0.0), 1.0))

    def _hub_activity(self, connectivity: torch.Tensor) -> float:
        degrees = connectivity.abs().sum(dim=1)
        max_degree = degrees.max()
        if max_degree < 1e-10:
            return 0.0
        normalized = degrees / max_degree
        k = max(1, int(0.2 * len(degrees)))
        top = torch.topk(normalized, k).indices
        hub_conn = connectivity[top][:, top]
        return float(min(hub_conn.abs().mean().item(), 1.0))

    def _self_reference(self, neural_data: torch.Tensor) -> float:
        n_time = neural_data.shape[0]
        if n_time < 100:
            return 0.0
        window = 50
        n_windows = n_time // window
        if n_windows < 2:
            return 0.0
        sims = []
        for i in range(n_windows - 1):
            a = neural_data[i * window:(i + 1) * window].flatten()
            b = neural_data[(i + 1) * window:(i + 2) * window].flatten()
            if a.var(unbiased=False) < 1e-12 or b.var(unbiased=False) < 1e-12:
                continue
            sim = torch.nn.functional.cosine_similarity(
                (a - a.mean()).unsqueeze(0).double(),
                (b - b.mean()).unsqueeze(0).double(),
            )
            v = float(sim.nan_to_num(0.0).item())
            sims.append(v)
        if not sims:
            return 0.0
        return float(max(0.0, float(np.mean(sims))))

    def _temporal_consistency(self, neural_data: torch.Tensor) -> float:
        n_time = neural_data.shape[0]
        if n_time < 20:
            return 0.0
        window = max(10, n_time // 10)
        correlations = []
        for i in range(0, n_time - 2 * window, window):
            a = neural_data[i:i + window].flatten()
            b = neural_data[i + window:i + 2 * window].flatten()
            if a.var(unbiased=False) < 1e-12 or b.var(unbiased=False) < 1e-12:
                continue
            c = torch.nn.functional.cosine_similarity(
                (a - a.mean()).unsqueeze(0).double(),
                (b - b.mean()).unsqueeze(0).double(),
            )
            correlations.append(float(c.nan_to_num(0.0).item()))
        if not correlations:
            return 0.0
        return float(max(0.0, float(np.mean(correlations))))

    def _information_integration(self, neural_data: torch.Tensor) -> float:
        n_neurons = neural_data.shape[1]
        if n_neurons < 2 or neural_data.shape[0] < 10:
            return 0.0
        n_pairs = min(100, n_neurons * (n_neurons - 1) // 2)
        generator = torch.Generator().manual_seed(1234)
        values = []
        for _ in range(n_pairs):
            i, j = torch.randperm(n_neurons, generator=generator)[:2].tolist()
            values.append(
                cmetrics.mutual_information(
                    neural_data[:, i], neural_data[:, j], bins=8
                )
            )
        return float(min(float(np.mean(values)), 1.0))

    def _causal_density(self, connectivity: torch.Tensor) -> float:
        n = connectivity.shape[0]
        max_conn = n * (n - 1)
        if max_conn == 0:
            return 0.0
        strong = (connectivity.abs() > 0.1).double()
        actual = strong.sum().item() - strong.diagonal().sum().item()
        return float(actual / max_conn)

    def _signature(self, neural_data: torch.Tensor) -> torch.Tensor:
        fft = torch.fft.rfft(neural_data, dim=0)
        power = torch.abs(fft) ** 2
        avg = power.mean(dim=1)
        return avg / avg.norm().clamp_min(1e-10)


def neural_state_T(neural_data: torch.Tensor) -> torch.Tensor:
    """Transpose helper kept as a function for readability."""
    return neural_data.T
