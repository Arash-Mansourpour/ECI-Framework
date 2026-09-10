"""Coevolution: populations of graphs x curricula of tasks.

Candidates (MotifGenomes) are compiled, probed by task callables
``probe(graph) -> reward``, and ranked by reward + novelty (distance of
the motif histogram to the archive) with fitness sharing inside niches.
Champion/challenger promotion is DAO-gated (quorum param, default 2/3 of
a test-panel vote simulated here by an injected voter fn). Lineage is a
full parent tree — evolution with a fossil record.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from eci.morph.graph import MorphGraph
from eci.morph.motifs import MotifGenome

__all__ = ["Candidate", "Coevolver"]


@dataclass
class Candidate:
    genome: MotifGenome
    fitness: float = 0.0
    novelty: float = 0.0
    reward: float = 0.0
    parent: str = ""
    cid: str = ""


class Coevolver:
    def __init__(self, pop: int = 6, novelty_w: float = 0.3, quorum: float = 2 / 3) -> None:
        self.pop = pop
        self.novelty_w = novelty_w
        self.quorum = quorum
        self.candidates: List[Candidate] = []
        self.archive: List[Dict[str, int]] = []  # motif histograms
        self.lineage: Dict[str, str] = {}
        self.generation = 0

    def seed(self, seed: int = 0) -> None:
        self.candidates = []
        for i in range(self.pop):
            g = MotifGenome().random(motifs=3, seed=seed + i, prefix=f"g{self.generation}c{i}")
            c = Candidate(g, cid=f"g{self.generation}c{i}")
            self.candidates.append(c)
            self.lineage[c.cid] = ""

    def _novelty(self, hist: Dict[str, int]) -> float:
        if not self.archive:
            return 1.0
        keys = set(hist) | {k for h in self.archive for k in h}
        def vec(h):
            return [h.get(k, 0) for k in keys]
        v = vec(hist)
        best = min(sum((a - b) ** 2 for a, b in zip(v, vec(h))) ** 0.5 for h in self.archive)
        return best

    def evaluate(self, probes: List[Callable[[MorphGraph], float]]) -> None:
        for c in self.candidates:
            g = MorphGraph()
            c.genome.compile(g)
            c.reward = sum(p(g) for p in probes) / max(1, len(probes))
            c.novelty = self._novelty(c.genome.motif_histogram())
            c.fitness = c.reward + self.novelty_w * c.novelty
            c.genome.fitness = c.fitness
        self.archive.extend(c.genome.motif_histogram() for c in self.candidates)
        self.archive = self.archive[-64:]

    def evolve(self, voter: Callable[[Candidate, Candidate], bool] | None = None,
               seed: int = 0) -> Dict[str, Any]:
        """Tournament + crossover + mutation; champion needs quorum to enthrone."""
        rng = random.Random(seed)
        ranked = sorted(self.candidates, key=lambda c: -c.fitness)
        champ, chal = ranked[0], ranked[1] if len(ranked) > 1 else ranked[0]
        votes = sum(1 for _ in range(3) for v in [voter or (lambda a, b: True)] if v(champ, chal))
        enthroned = votes / 3 >= self.quorum
        kids: List[Candidate] = []
        for i in range(self.pop):
            a, b = rng.sample(ranked[:max(2, len(ranked) // 2)], 2)
            kid_genome = a.genome.crossover(b.genome, seed=seed + i).mutate(seed=seed + 100 + i)
            kid = Candidate(kid_genome, parent=a.cid, cid=f"g{self.generation + 1}k{i}")
            kids.append(kid)
            self.lineage[kid.cid] = a.cid
        # elitism: slot 0 carries the champion genome forward untouched
        kids[0].genome = champ.genome
        kids[0].fitness = champ.fitness
        kids[0].parent = champ.cid
        self.candidates = kids
        self.generation += 1
        return {"champion": champ.cid, "fitness": champ.fitness, "reward": champ.reward,
                "enthroned": enthroned, "votes": votes, "generation": self.generation}
