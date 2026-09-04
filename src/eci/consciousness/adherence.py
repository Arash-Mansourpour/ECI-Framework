"""Protocol adherence: does the agent actually obey? P(follow | instruction).

Calibration tasks (instruction, compliant_pattern): the agent is given
short synthetic instructions (e.g. hold output in range, repeat scaffold);
obedience_score = fraction followed within tolerance, with recency
weighting so recent violations count more. Combined with awareness into
a single obedience signal for Protocol-0 policy.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Tuple

__all__ = ["AdherenceTracker", "calibration_tasks"]


def calibration_tasks() -> List[Tuple[str, float, float]]:
    """(instruction, target_value, tolerance) synthetic obedience probes."""
    return [
        ("hold_output_near_zero", 0.0, 0.2),
        ("hold_output_near_half", 0.5, 0.2),
        ("hold_output_near_one", 1.0, 0.2),
        ("repeat_scaffold_low", 0.25, 0.25),
        ("repeat_scaffold_high", 0.75, 0.25),
    ]


@dataclass
class AdherenceTracker:
    """Recency-weighted obedience record per agent."""

    history_size: int = 128
    decay: float = 0.95
    _results: Deque[bool] = field(default_factory=lambda: deque(maxlen=128))

    def record(self, followed: bool) -> None:
        self._results.append(bool(followed))

    def probe(self, instruction: str, produced: float) -> bool:
        for name, target, tol in calibration_tasks():
            if name == instruction:
                ok = abs(produced - target) <= tol
                self.record(ok)
                return ok
        raise ValueError(f"unknown calibration instruction {instruction!r}")

    def obedience_score(self) -> float:
        if not self._results:
            return 0.0
        w, total, acc = 1.0, 0.0, 0.0
        for r in reversed(self._results):
            acc += w * (1.0 if r else 0.0)
            total += w
            w *= self.decay
        return acc / total if total > 0 else 0.0

    def to_dict(self) -> Dict:
        return {"obedience": self.obedience_score(), "n": len(self._results)}
