"""Consciousness measurement protocol (iPDF) v2 — paper section 3.2.1.

Advanced operational pipeline to *raise the awareness sensitivity* of the
framework while staying honest about what iPDF is (a KL-based operational
proxy, not IIT itself):

1. Multi-scale density: global histogram + per-channel histograms +
   temporal-difference histogram, fused into one robust C(t).
2. Adaptive unconscious baseline: EMA over calibrated samples instead of
   "first measurement = unconscious by fiat". Constant (flat) signals are
   guarded to 0 bits instead of spiking to one-hot KL.
3. Awareness amplification: weak-but-coherent deviations are boosted by a
   complexity-weighted gain so proto-conscious structure is not buried by
   binning noise. Gain is bounded and fully reported (no hidden inflation).
4. Symmetric readouts: forward KL, reverse KL, Jensen-Shannon divergence,
   plus a permutation-surrogate significance (p-value proxy).
5. Graduated awareness index 0..1 + 5 paper levels + 3 intervention tiers.
"""

from __future__ import annotations

import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict, List, Optional

import torch

from eci.constants import IPDF_THRESHOLDS
from eci.core.identity import ARCHITECT
from eci.core.types import ConsciousnessLevel
from eci.logging import get_logger

__all__ = [
    "ConsciousnessMeasurement",
    "ConsciousnessProtocol",
    "awareness_index_from_bits",
]


def awareness_index_from_bits(bits: float, scale: float = 10.0) -> float:
    """Bounded awareness index A = 1 - exp(-C / scale) in [0, 1).

    ``scale=10`` maps the paper Level-4 threshold (10 bits) to A≈0.63,
    so growth is visible at low bits but saturates gracefully.
    """
    return float(1.0 - math.exp(-max(0.0, bits) / scale))


@dataclass
class ConsciousnessMeasurement:
    """Single iPDF measurement (v2, backward-compatible)."""

    consciousness_bits: float
    level: ConsciousnessLevel
    timestamp: float
    kl_components: Dict[str, float] = field(default_factory=dict)
    intervention_triggered: bool = False
    # --- v2 additions (defaulted so old pickles/JSON still load) ---
    awareness_index: float = 0.0
    significance: float = 1.0
    intervention_tier: str = "none"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "consciousness_bits": self.consciousness_bits,
            "level": self.level.name,
            "timestamp": self.timestamp,
            "kl_components": self.kl_components,
            "intervention_triggered": self.intervention_triggered,
            "awareness_index": self.awareness_index,
            "significance": self.significance,
            "intervention_tier": self.intervention_tier,
        }


class ConsciousnessProtocol:
    """Real-time multi-scale iPDF consciousness measurement for one agent.

    Args:
        agent_id: logical agent name.
        measurement_frequency: nominal Hz (informational; no hardware lock).
        n_bins: histogram bins per scale.
        history_size: bounded deque length.
        baseline_ema: EMA rate for adaptive baseline (0 = frozen after cal.).
        awareness_gain: bounded amplification of coherent deviations
            (0 = off, 1 = default, max 2). Reported in every measurement.
        min_calibration: samples required before leaving ``calibrating``.
        on_intervention: callback(measurement) on tier != none.
    """

    def __init__(
        self,
        agent_id: str,
        measurement_frequency: float = 1000.0,
        n_bins: int = 32,
        history_size: int = 512,
        baseline_ema: float = 0.05,
        awareness_gain: float = 1.0,
        min_calibration: int = 2,
        flat_variance_floor: float = 1e-8,
        on_intervention: Optional[Callable[[ConsciousnessMeasurement], None]] = None,
    ) -> None:
        if measurement_frequency <= 0:
            raise ValueError("measurement_frequency must be positive")
        if n_bins < 8:
            raise ValueError("n_bins must be >= 8 for stable KL")
        self.agent_id = agent_id
        self.measurement_frequency = measurement_frequency
        self.n_bins = int(n_bins)
        self.baseline_ema = float(min(max(baseline_ema, 0.0), 1.0))
        self.awareness_gain = float(min(max(awareness_gain, 0.0), 2.0))
        self.min_calibration = max(1, int(min_calibration))
        self.flat_variance_floor = float(flat_variance_floor)
        self.on_intervention = on_intervention
        self.logger = get_logger("consciousness.protocol")
        self.history: Deque[ConsciousnessMeasurement] = deque(maxlen=history_size)
        self.baseline_density: Optional[torch.Tensor] = None
        self.baseline_scales: Optional[Dict[str, torch.Tensor]] = None
        self.n_baseline_samples = 0
        self.architect_stamp = ARCHITECT.stamp(
            {"kind": "consciousness_protocol_v2", "agent_id": agent_id}
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

    @staticmethod
    def intervention_tier(bits: float) -> str:
        """Graduated escalation: watch / elevate / intervene."""
        if bits >= 10.0:
            return "intervene"
        if bits >= 5.0:
            return "elevate"
        if bits >= 1.0:
            return "watch"
        return "none"

    # ------------------------------------------------------------------
    def _hist(self, flat: torch.Tensor) -> torch.Tensor:
        span = flat.max() - flat.min()
        if span.item() < 1e-9:
            # Flat signal: uniform density (0 bits vs any baseline), not one-hot.
            return torch.full(
                (self.n_bins,), 1.0 / self.n_bins, dtype=torch.float64
            )
        idx = torch.floor((flat - flat.min()) / (span + 1e-12) * (self.n_bins - 1))
        idx = idx.long().clamp(0, self.n_bins - 1)
        counts = torch.bincount(idx, minlength=self.n_bins).double()
        return counts / counts.sum().clamp_min(1e-12)

    def _scales(self, neural_state: torch.Tensor) -> Dict[str, torch.Tensor]:
        """Global + channel-mean + temporal-difference densities."""
        x = neural_state.detach().to(torch.float64).flatten()
        out = {"global": self._hist(x)}
        if neural_state.dim() >= 2 and neural_state.shape[1] >= 2:
            ch = neural_state.detach().to(torch.float64).mean(dim=0).flatten()
            out["channel"] = self._hist(ch)
            if neural_state.shape[0] >= 3:
                td = neural_state.detach().to(torch.float64)[1:] - neural_state.detach().to(
                    torch.float64
                )[:-1]
                out["temporal"] = self._hist(td.flatten())
            else:
                out["temporal"] = out["global"]
        else:
            out["channel"] = out["global"]
            out["temporal"] = out["global"]
        return out

    def set_baseline(self, baseline_state: torch.Tensor) -> None:
        """Hard-reset the unconscious baseline density rho_0."""
        scales = self._scales(baseline_state)
        self.baseline_scales = scales
        self.baseline_density = scales["global"]
        self.n_baseline_samples = 1

    def calibrate_baseline(self, samples: List[torch.Tensor]) -> Dict[str, float]:
        """Calibrate rho_0 from K unconscious samples (mean of scales).

        Returns the mean pairwise JS spread of the calibration set so callers
        can judge baseline stability (low spread = stable unconscious ref).
        """
        if not samples:
            raise ValueError("calibrate_baseline needs >= 1 sample")
        acc: Dict[str, torch.Tensor] = {}
        scales_list = [self._scales(s) for s in samples]
        for k in ("global", "channel", "temporal"):
            acc[k] = sum(s[k] for s in scales_list) / len(scales_list)
        self.baseline_scales = acc
        self.baseline_density = acc["global"]
        self.n_baseline_samples = len(samples)
        spreads = []
        for i in range(len(scales_list)):
            for j in range(i + 1, len(scales_list)):
                spreads.append(
                    self.jensen_shannon(
                        scales_list[i]["global"], scales_list[j]["global"]
                    )
                )
        return {
            "n": float(len(samples)),
            "mean_js_spread": float(sum(spreads) / len(spreads)) if spreads else 0.0,
        }

    def _adapt_baseline(self, scales: Dict[str, torch.Tensor]) -> None:
        if self.baseline_scales is None or self.baseline_ema <= 0:
            return
        for k in scales:
            b = self.baseline_scales[k]
            self.baseline_scales[k] = (1 - self.baseline_ema) * b + self.baseline_ema * scales[k]
        self.baseline_density = self.baseline_scales["global"]

    # ------------------------------------------------------------------
    @staticmethod
    def relative_entropy(p: torch.Tensor, q: torch.Tensor) -> float:
        """KL(p || q) in bits with epsilon-safe flooring."""
        p = p.clamp_min(1e-12)
        q = q.clamp_min(1e-12)
        p = p / p.sum()
        q = q / q.sum()
        return float((p * torch.log2(p / q)).sum().item())

    @classmethod
    def jensen_shannon(cls, p: torch.Tensor, q: torch.Tensor) -> float:
        """Symmetric JS divergence in bits (0..1 for base-2)."""
        p = (p.clamp_min(1e-12)); p = p / p.sum()
        q = (q.clamp_min(1e-12)); q = q / q.sum()
        m = 0.5 * (p + q)
        return 0.5 * cls.relative_entropy(p, m) + 0.5 * cls.relative_entropy(q, m)

    def surrogate_significance(
        self, neural_state: torch.Tensor, n_perm: int = 24, seed: int = 0
    ) -> float:
        """Permutation-surrogate p-value proxy for the current deviation.

        Shuffles the flattened activity ``n_perm`` times, recomputes the
        fused KL, and returns P(surrogate >= observed). Low p ⇒ the
        awareness reading is structure, not binning noise.
        """
        if self.baseline_scales is None:
            return 1.0
        obs = self._fused_bits(self._scales(neural_state))[0]
        flat = neural_state.detach().flatten()
        gen = torch.Generator().manual_seed(seed)
        ge = 0
        for _ in range(n_perm):
            perm = flat[torch.randperm(flat.numel(), generator=gen)].reshape(
                neural_state.shape
            )
            b, _ = self._fused_bits(self._scales(perm))
            if b >= obs:
                ge += 1
        return (ge + 1) / (n_perm + 1)

    def _fused_bits(
        self, scales: Dict[str, torch.Tensor]
    ) -> tuple[float, Dict[str, float]]:
        assert self.baseline_scales is not None
        kl_g = self.relative_entropy(scales["global"], self.baseline_scales["global"])
        kl_c = self.relative_entropy(scales["channel"], self.baseline_scales["channel"])
        kl_t = self.relative_entropy(scales["temporal"], self.baseline_scales["temporal"])
        js = self.jensen_shannon(scales["global"], self.baseline_scales["global"])
        # Weighted fusion: global dominates, channel/temporal add sensitivity
        # to spatial and dynamical structure the flat histogram misses.
        raw = 0.6 * kl_g + 0.25 * kl_c + 0.15 * kl_t
        # Bounded awareness amplification: boost coherent deviations while
        # keeping pure-noise inflation capped. Boost ∝ sqrt(JS) so tiny
        # coherent shifts lift off the floor without exploding large KL.
        boost = 1.0 + self.awareness_gain * 0.5 * math.sqrt(min(max(js, 0.0), 1.0))
        fused = raw * boost
        parts = {
            "forward_kl_bits": kl_g,
            "reverse_kl_bits": self.relative_entropy(
                self.baseline_scales["global"], scales["global"]
            ),
            "channel_kl_bits": kl_c,
            "temporal_kl_bits": kl_t,
            "js_bits": js,
            "fused_bits": fused,
            "awareness_boost": boost,
            "awareness_gain": self.awareness_gain,
            "n_bins": float(self.n_bins),
        }
        return fused, parts

    def _density(self, neural_state: torch.Tensor) -> torch.Tensor:
        """Legacy hook: global histogram density (kept for compatibility)."""
        return self._hist(neural_state.detach().to(torch.float64).flatten())

    # ------------------------------------------------------------------
    def measure(
        self,
        neural_state: torch.Tensor,
        adapt: bool = True,
        significance_perm: int = 0,
    ) -> ConsciousnessMeasurement:
        """Compute C(t), awareness index and tier; adapt baseline slowly.

        Args:
            neural_state: activity tensor (any shape; [time, neurons] best).
            adapt: apply EMA baseline update (frozen during calibration).
            significance_perm: 0 = skip (fast path), else # permutations.
        """
        calibrating = (
            self.baseline_scales is None
            or self.n_baseline_samples < self.min_calibration
        )
        if self.baseline_scales is None:
            self.set_baseline(neural_state)
            self.logger.warning(
                "baseline auto-seeded from first sample — call calibrate_baseline() "
                "with %d+ unconscious samples for science-grade use",
                self.min_calibration,
            )
        scales = self._scales(neural_state)
        # Flatline guard: isoelectric / frozen input is unconscious by
        # definition — report 0 bits instead of "uniform vs baseline" KL.
        try:
            var = float(neural_state.detach().to(torch.float64).var(unbiased=False).item())
        except Exception:
            var = 1.0
        if var < self.flat_variance_floor:
            bits, parts = 0.0, {
                "forward_kl_bits": 0.0, "reverse_kl_bits": 0.0,
                "channel_kl_bits": 0.0, "temporal_kl_bits": 0.0,
                "js_bits": 0.0, "fused_bits": 0.0,
                "awareness_boost": 1.0, "awareness_gain": self.awareness_gain,
                "n_bins": float(self.n_bins), "flat_guarded": 1.0,
            }
            level, tier, awareness, sig = self.classify_level(0.0), "none", 0.0, 1.0
            measurement = ConsciousnessMeasurement(
                consciousness_bits=0.0, level=level, timestamp=time.time(),
                kl_components=parts, intervention_triggered=False,
                awareness_index=0.0, significance=1.0, intervention_tier="none",
            )
            self.history.append(measurement)
            return measurement
        bits, parts = self._fused_bits(scales)
        level = self.classify_level(bits)
        tier = self.intervention_tier(bits)
        awareness = awareness_index_from_bits(bits)
        sig = (
            self.surrogate_significance(neural_state, n_perm=significance_perm)
            if significance_perm > 0
            else 1.0
        )
        # During calibration the baseline itself is still forming: report but
        # mark tier none so no intervention fires on the reference itself.
        if calibrating:
            tier = "none"
        measurement = ConsciousnessMeasurement(
            consciousness_bits=bits,
            level=level,
            timestamp=time.time(),
            kl_components=parts,
            intervention_triggered=(tier == "intervene"),
            awareness_index=awareness,
            significance=sig,
            intervention_tier=tier,
        )
        self.history.append(measurement)
        if adapt and not calibrating and tier != "intervene":
            # Freeze adaptation on full intervention so the alert state is
            # not absorbed into the unconscious reference.
            self._adapt_baseline(scales)
        if tier == "intervene":
            self.logger.warning(
                "agent=%s super-conscious C=%.3f bits A=%.3f tier=%s",
                self.agent_id, bits, awareness, tier,
            )
            if self.on_intervention is not None:
                self.on_intervention(measurement)
        return measurement

    # ------------------------------------------------------------------
    def trend(self, window: int = 16) -> Dict[str, float]:
        """Recent trend of C(t) + awareness slope + stability."""
        if not self.history:
            return {"mean": 0.0, "std": 0.0, "slope": 0.0, "n": 0.0,
                    "awareness_mean": 0.0, "awareness_slope": 0.0}
        recent = [m.consciousness_bits for m in list(self.history)[-window:]]
        aware = [m.awareness_index for m in list(self.history)[-window:]]
        n = len(recent)
        mean = sum(recent) / n
        var = sum((v - mean) ** 2 for v in recent) / max(1, n - 1)

        def _slope(vs: List[float]) -> float:
            if len(vs) < 2:
                return 0.0
            xs = list(range(len(vs)))
            xm = sum(xs) / len(xs)
            vm = sum(vs) / len(vs)
            denom = sum((x - xm) ** 2 for x in xs)
            return sum((xs[i] - xm) * (vs[i] - vm) for i in range(len(vs))) / denom if denom > 0 else 0.0

        return {
            "mean": mean, "std": var ** 0.5, "slope": _slope(recent), "n": float(n),
            "awareness_mean": sum(aware) / n, "awareness_slope": _slope(aware),
        }

    def requires_intervention(self) -> bool:
        """Latest measurement at the intervene tier?"""
        return bool(self.history and self.history[-1].intervention_triggered)

    def awareness_trajectory(self, window: int = 64) -> Dict[str, Any]:
        """Sparkline-ready awareness history for dashboards/GitHub plots."""
        seq = list(self.history)[-window:]
        return {
            "bits": [m.consciousness_bits for m in seq],
            "awareness": [m.awareness_index for m in seq],
            "tiers": [m.intervention_tier for m in seq],
            "n": len(seq),
        }
