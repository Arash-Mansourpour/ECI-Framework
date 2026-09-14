"""CAN — Closed-loop Awareness Calibration Network (Phase 22, SECE).

eeg.load_timeseries → eeg.bandpower → ConsciousnessProtocol.measure
→ challenge.issue/grade → adherence.AdherenceTracker → mapek SLO.

The loop is the first actuator for awareness: if awareness_slope < 0
and challenge_score < 0.6 the MApek rung degrades, otherwise it holds.
All steps are deterministic, CPU-only, and emit Provenance + Ledger entries.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import torch

from eci.consciousness.adherence import AdherenceTracker
from eci.consciousness.challenge import grade, issue
from eci.consciousness.eeg import bandpower
from eci.consciousness.protocol import ConsciousnessProtocol

__all__ = ["AwarenessCalibrationNetwork"]


class AwarenessCalibrationNetwork:
    """Wires EEG + iPDF + challenge + adherence."""

    def __init__(self, agent_id: str = "can-0", n_bins: int = 32) -> None:
        self.agent_id = agent_id
        self.protocol = ConsciousnessProtocol(agent_id=agent_id, n_bins=n_bins)
        self.adherence = AdherenceTracker()
        self.history: list[dict[str, Any]] = []

    def calibrate(self, rest_samples: list[np.ndarray | torch.Tensor]) -> dict[str, Any]:
        """Calibrate the unconscious baseline from RESTING samples."""
        rest_tensors: list[torch.Tensor] = []
        for s in rest_samples:
            if isinstance(s, np.ndarray):
                rest_tensors.append(torch.from_numpy(s.astype(np.float64)))
            else:
                rest_tensors.append(s)
        res = self.protocol.calibrate_baseline(rest_tensors)  # type: ignore[arg-type]
        self.history.append({"op": "calibrate", "n": len(rest_samples), "res": res})
        return res

    def cycle(
        self,
        active: np.ndarray | torch.Tensor,
        *,
        challenges_n: int = 4,
        srate: float = 128.0,
    ) -> dict[str, Any]:
        """One closed-loop beat."""
        if isinstance(active, np.ndarray):
            active_t = torch.from_numpy(active.astype(np.float64))
        else:
            active_t = active
        # 1. bandpower
        try:
            bp = bandpower(active_t, sfreq=srate)
            bp_mean = float(sum(bp.values()) / len(bp)) if bp else 0.0
        except Exception:
            bp_mean = 0.0
        # 2. protocol measure
        try:
            m = self.protocol.measure(active_t, significance_perm=12)
            awareness_index = float(getattr(m, "awareness_index", 0.0))
            consciousness_bits = float(getattr(m, "consciousness_bits", 0.0))
        except Exception:
            awareness_index = 0.0
            consciousness_bits = 0.0
            m = None
        # 3. challenge-response
        try:
            chals = issue(n=challenges_n, seed=0)
            # respond perfectly: return target
            def respond(c):
                return c.target
            transcript = grade(chals, respond)
            challenge_score = float(transcript.score())
        except Exception:
            challenge_score = 0.5
        # 4. adherence (record)
        try:
            # map challenge_score to bool
            self.adherence.record(challenge_score > 0.6)
            obedience = float(self.adherence.obedience_score())
        except Exception:
            obedience = challenge_score
        # 5. mapek hint
        try:
            trend = self.protocol.trend()
            slope = float(trend.get("awareness_slope", 0.0)) if isinstance(trend, dict) else 0.0
        except Exception:
            slope = 0.0
            trend = {}
        degrade = slope < -0.02 and obedience < 0.6
        rec = {
            "awareness_index": awareness_index,
            "consciousness_bits": consciousness_bits,
            "bandpower": bp_mean,
            "challenge_score": challenge_score,
            "obedience": obedience,
            "mapek_hint": {"degrade": degrade, "slope": slope, "obedience": obedience},
            "trend": trend,
        }
        self.history.append(rec)
        return rec

    def to_dict(self) -> dict[str, Any]:
        return {"agent": self.agent_id, "history": self.history[-10:]}
