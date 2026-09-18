"""Adaptive protocol vigilance: future-proof anomaly sensing.

Design
------
* EWMA mean/variance per metric (alpha=0.2) → adaptive threshold
  `mean + k*sigma` (k=3) that drifts with legitimate regime shifts but
  spikes on anomalies.
* Predictive check: linear extrapolation from last 3 points → if next
  value deviates >3σ from prediction, flag as `predictive_anomaly`.
* No torch, no heavy deps — pure Python/numpy, O(1) per update.
* Bounded history (deque maxlen=256) — no unbounded growth (Phase 5).
* Honesty: this is a statistical proxy, not a consciousness or security
  proof — see LIMITATIONS.md#vigilance (added).

Integrates as opt-in wrapper: `vigilance.update({"phi":0.5, "lz":0.3})`
does not replace existing `analyzer` or `governance` logic.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetricState:
    ewma: float = 0.0
    ewmvar: float = 1.0
    count: int = 0
    history: deque[float] = field(default_factory=lambda: deque(maxlen=256))

    def update(self, value: float, alpha: float = 0.2) -> None:
        self.history.append(value)
        if self.count == 0:
            self.ewma = value
            self.ewmvar = 1.0
        else:
            delta = value - self.ewma
            self.ewma += alpha * delta
            self.ewmvar = (1 - alpha) * (self.ewmvar + alpha * delta * delta)
        self.count += 1

    def threshold(self, k: float = 3.0) -> float:
        return self.ewma + k * math.sqrt(max(self.ewmvar, 1e-12))

    def is_anomalous(self, value: float, k: float = 3.0) -> bool:
        if self.count < 5:
            return False
        return value > self.threshold(k)

    def predict_next(self) -> float | None:
        if len(self.history) < 3:
            return None
        a, b, c = self.history[-3], self.history[-2], self.history[-1]
        # linear extrap: c + (c-b) ~ 2c - b, averaged with trend
        return 2 * c - b + 0.5 * ((c - b) - (b - a))

    def predictive_anomaly(self, value: float, k: float = 3.0) -> bool:
        pred = self.predict_next()
        if pred is None or self.count < 5:
            return False
        sigma = math.sqrt(max(self.ewmvar, 1e-12))
        return abs(value - pred) > k * sigma


class AdaptiveVigilance:
    """Per-metric adaptive vigilance with bounded history."""

    def __init__(self, alpha: float = 0.2, k: float = 3.0, history: int = 256) -> None:
        self.alpha = alpha
        self.k = k
        self.history = history
        self._states: dict[str, MetricState] = {}

    def _get(self, key: str) -> MetricState:
        if key not in self._states:
            self._states[key] = MetricState(history=deque(maxlen=self.history))
        return self._states[key]

    def update(self, metrics: dict[str, float]) -> dict[str, Any]:
        """Update all metrics, return per-metric anomaly report."""
        report: dict[str, Any] = {}
        for key, value in metrics.items():
            if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                report[key] = {"anomaly": False, "predictive": False, "reason": "non-finite"}
                continue
            st = self._get(key)
            anomalous = st.is_anomalous(float(value), self.k)
            pred_anom = st.predictive_anomaly(float(value), self.k)
            report[key] = {
                "value": float(value),
                "ewma": st.ewma,
                "sigma": math.sqrt(max(st.ewmvar, 1e-12)),
                "threshold": st.threshold(self.k),
                "anomaly": anomalous,
                "predictive_anomaly": pred_anom,
                "count": st.count,
            }
            st.update(float(value), self.alpha)
        return report

    def is_global_anomaly(self, report: dict[str, Any], min_flags: int = 2) -> bool:
        flags = sum(1 for v in report.values() if v.get("anomaly") or v.get("predictive_anomaly"))
        return flags >= min_flags

    def to_dict(self) -> dict[str, Any]:
        return {
            k: {"ewma": s.ewma, "sigma": math.sqrt(max(s.ewmvar, 1e-12)), "count": s.count, "history_len": len(s.history)}
            for k, s in self._states.items()
        }
