"""Quality-Diversity creativity engine (MAP-Elites + novelty search).

One optimum collapses; an archive of diverse elites compounds. Genomes live
in niches indexed by behavior descriptors; each cell keeps its best.
Offspring mutate from random elites (stepping stones), including
goal-switching across niches (POET-style transfer).
"""

from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass
from typing import Any, Callable

__all__ = ["Elite", "MAPElites", "NoveltyArchive", "qd_score"]


@dataclass
class Elite:
    genome: Any
    behavior: tuple[float, ...]
    fitness: float
    generation: int = 0
    lineage: str = ""


def qd_score(cells: dict[tuple[int, ...], Elite]) -> float:
    return sum(e.fitness for e in cells.values())


class NoveltyArchive:
    """k-NN sparseness archive (Lehman & Stanley novelty search)."""

    def __init__(self, k: int = 5, threshold: float = 0.3) -> None:
        self.k = k
        self.threshold = threshold
        self.points: list[tuple[float, ...]] = []

    @staticmethod
    def _dist(a: tuple[float, ...], b: tuple[float, ...]) -> float:
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

    def sparseness(self, b: tuple[float, ...]) -> float:
        if len(self.points) < self.k:
            return float("inf")
        ds = sorted(self._dist(b, p) for p in self.points)
        return sum(ds[: self.k]) / self.k

    def consider(self, b: tuple[float, ...]) -> bool:
        if self.sparseness(b) >= self.threshold:
            self.points.append(b)
            return True
        return False


class MAPElites:
    """Grid archive over a discretized behavior space."""

    def __init__(self, dims: int, bins: int = 8, lo: float = 0.0, hi: float = 1.0,
                 seed: int = 0) -> None:
        if dims < 1 or bins < 2:
            raise ValueError("need dims>=1, bins>=2")
        self.dims = dims
        self.bins = bins
        self.lo = lo
        self.hi = hi
        self.rng = random.Random(seed)
        self.cells: dict[tuple[int, ...], Elite] = {}
        self.novelty = NoveltyArchive()
        self.evaluations = 0
        self.improvements = 0

    def cell_of(self, behavior: tuple[float, ...]) -> tuple[int, ...]:
        idx = []
        for v in behavior[: self.dims]:
            c = min(self.bins - 1, max(0, int((v - self.lo) / (self.hi - self.lo) * self.bins)))
            idx.append(c)
        while len(idx) < self.dims:
            idx.append(0)
        return tuple(idx)

    def elite_id(self, genome: Any) -> str:
        return hashlib.sha256(repr(genome).encode()).hexdigest()[:12]

    def tell(self, genome: Any, behavior: tuple[float, ...],
             fitness: float, generation: int = 0) -> dict[str, Any]:
        """Insert candidate; returns {inserted, improved, novel, cell}."""
        self.evaluations += 1
        cell = self.cell_of(behavior)
        novel = self.novelty.consider(tuple(behavior[: self.dims]))
        cur = self.cells.get(cell)
        elite = Elite(genome=genome, behavior=tuple(behavior), fitness=fitness,
                      generation=generation, lineage=self.elite_id(genome))
        if cur is None or fitness > cur.fitness:
            self.cells[cell] = elite
            if cur is not None:
                self.improvements += 1
            return {"inserted": True, "improved": cur is not None, "novel": novel, "cell": cell}
        return {"inserted": False, "improved": False, "novel": novel, "cell": cell}

    def sample_parent(self) -> Elite:
        return self.rng.choice(list(self.cells.values()))

    def run(self, fitness_fn: Callable[[Any], tuple[float, tuple[float, ...]]],
            mutate_fn: Callable[[Any], Any], inits: list[Any],
            generations: int = 8, offspring: int = 16) -> dict[str, Any]:
        """Evolve inits; fitness_fn(genome) -> (fitness, behavior)."""
        for g in inits:
            fit, beh = fitness_fn(g)
            self.tell(g, beh, fit, generation=0)
        for gen in range(1, generations + 1):
            for _ in range(offspring):
                if not self.cells:
                    break
                child = mutate_fn(self.sample_parent().genome)
                fit, beh = fitness_fn(child)
                self.tell(child, beh, fit, generation=gen)
        return self.report()

    def coverage(self) -> float:
        return len(self.cells) / (self.bins ** self.dims)

    def report(self) -> dict[str, Any]:
        best = max(self.cells.values(), key=lambda e: e.fitness, default=None)
        return {"cells": len(self.cells), "coverage": round(self.coverage(), 4),
                "qd_score": round(qd_score(self.cells), 4),
                "evaluations": self.evaluations, "improvements": self.improvements,
                "novel_points": len(self.novelty.points),
                "best_fitness": round(best.fitness, 4) if best else 0.0}
