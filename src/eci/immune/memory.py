"""Immunological memory: confirmed killers persist for fast secondary response.

Primary response scans the full naive repertoire (slow, thorough).
Memory cells — detectors with kills > 0, promoted after a confirmed
attack — are scanned FIRST on every new sample (fast path). A memory hit
skips breeding and goes straight to challenge. Memory decays: cells unused
for `retention` encounters are demoted (forgetting prevents autoimmunity).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Sequence

from eci.immune.detectors import Detector

__all__ = ["ImmuneMemory"]


@dataclass
class ImmuneMemory:
    cells: List[Detector] = field(default_factory=list)
    retention: int = 500
    _idle: dict = field(default_factory=dict)

    def promote(self, detectors: List[Detector]) -> int:
        n = 0
        known = {d.center for d in self.cells}
        for d in detectors:
            if d.kills > 0 and d.center not in known:
                self.cells.append(d)
                self._idle[d.center] = 0
                known.add(d.center)
                n += 1
        return n

    def recall(self, x: Sequence[float]) -> List[Detector]:
        """Fast path: memory hits (also refreshes their idle counters)."""
        hits = [d for d in self.cells if d.binds(x)]
        for d in self.cells:
            self._idle[d.center] = 0 if d in hits else self._idle.get(d.center, 0) + 1
        stale = [d for d in self.cells if self._idle.get(d.center, 0) > self.retention]
        for d in stale:
            self.cells.remove(d)
            del self._idle[d.center]
        return hits
