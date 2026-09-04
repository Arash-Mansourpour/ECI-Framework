"""Negative + clonal selection over behavior-feature space.

Feature vector (5-D, all in [0,1] except rate): [awareness, obedience,
trust, vote_rate, challenge_score]. Distance = Euclidean. A detector is
(center, radius): it *binds* x iff dist(center, x) <= radius.

Negative selection: random candidates surviving self-tolerance (no bind
on any self sample) become the naive repertoire. Clonal selection: on a
confirmed anomaly, clone the binders, mutate proportionally to affinity,
keep offspring that bind the anomaly harder while still tolerating self.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import List, Sequence, Tuple

__all__ = ["Detector", "DetectorSet", "affinity", "breed", "evolve"]


def affinity(a: Sequence[float], b: Sequence[float]) -> float:
    """Similarity in [0,1]: 1 / (1 + euclidean distance)."""
    d = math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))
    return 1.0 / (1.0 + d)


@dataclass
class Detector:
    center: Tuple[float, ...]
    radius: float
    generation: int = 0
    kills: int = 0

    def binds(self, x: Sequence[float]) -> bool:
        d = math.sqrt(sum((c - v) ** 2 for c, v in zip(self.center, x)))
        return d <= self.radius


@dataclass
class DetectorSet:
    detectors: List[Detector] = field(default_factory=list)

    def scan(self, x: Sequence[float]) -> List[Detector]:
        return [d for d in self.detectors if d.binds(x)]

    def false_positive_rate(self, self_samples: List[Sequence[float]]) -> float:
        if not self_samples:
            return 0.0
        hits = sum(1 for s in self_samples if self.scan(s))
        return hits / len(self_samples)


def breed(
    self_samples: List[Sequence[float]],
    n_detectors: int = 32,
    radius: float = 0.35,
    seed: int = 0,
    max_candidates: int = 4000,
) -> DetectorSet:
    """Negative selection: keep random detectors that tolerate ALL self."""
    rng = random.Random(seed)
    dim = len(self_samples[0]) if self_samples else 5
    out: List[Detector] = []
    tried = 0
    while len(out) < n_detectors and tried < max_candidates:
        tried += 1
        c = tuple(rng.uniform(0.0, 1.0) for _ in range(dim))
        d = Detector(center=c, radius=radius)
        if not any(d.binds(s) for s in self_samples):
            out.append(d)
    return DetectorSet(out)


def evolve(
    repertoire: DetectorSet,
    anomaly: Sequence[float],
    self_samples: List[Sequence[float]],
    clones_each: int = 6,
    mutation: float = 0.12,
    seed: int = 1,
) -> DetectorSet:
    """Clonal selection: mutate binders toward the anomaly, keep self-tolerant."""
    rng = random.Random(seed)
    binders = repertoire.scan(anomaly) or list(repertoire.detectors)
    offspring: List[Detector] = []
    for b in binders:
        for _ in range(clones_each):
            step = mutation * (1.0 - affinity(b.center, anomaly) + 0.1)
            c = tuple(min(1.0, max(0.0, v + rng.gauss(0, step))) for v in b.center)
            child = Detector(center=c, radius=b.radius * 0.95, generation=b.generation + 1)
            if child.binds(anomaly) and not any(child.binds(s) for s in self_samples):
                offspring.append(child)
    offspring.sort(key=lambda d: affinity(d.center, anomaly), reverse=True)
    for o in offspring[:4]:
        o.kills += 1
    return DetectorSet(list(repertoire.detectors) + offspring)
