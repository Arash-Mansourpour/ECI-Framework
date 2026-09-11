"""Motif genome: evolution at the level of reusable circuits.

Genes are not weights — they are *motif instances* (chain, fan, FFL,
feedback, diamond, hub-spoke) with attachment points. Crossover swaps
whole motif blocks between parents (preserving function, unlike blind
edge-swap); mutation rewires *inside* a motif (bounded damage).
``compile()`` grows a MorphGraph from the genome; ``export_genome()``
registers the champion in genome.py so harmful motifs go extinct through
the same DAO-gated life_cycle as any other gene.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

__all__ = ["MOTIFS", "MotifGene", "MotifGenome"]

# motif name -> internal edges over local ports (0..k-1)
MOTIFS: dict[str, list[tuple[int, int]]] = {
    "chain": [(0, 1), (1, 2)],
    "fan-out": [(0, 1), (0, 2)],
    "fan-in": [(0, 2), (1, 2)],
    "ffl": [(0, 1), (0, 2), (1, 2)],          # feed-forward loop
    "feedback": [(0, 1), (1, 0)],              # 2-cycle
    "diamond": [(0, 1), (0, 2), (1, 3), (2, 3)],
    "hub": [(0, 1), (0, 2), (0, 3)],
}


@dataclass
class MotifGene:
    motif: str
    ports: list[str]                 # global node ids bound to local ports
    w: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {"motif": self.motif, "ports": self.ports, "w": self.w}


@dataclass
class MotifGenome:
    genes: list[MotifGene] = field(default_factory=list)
    generation: int = 0
    fitness: float = 0.0

    def random(self, motifs: int = 3, seed: int = 0, prefix: str = "m") -> MotifGenome:
        rng = random.Random(seed)
        names = sorted(MOTIFS)
        for i in range(motifs):
            m = rng.choice(names)
            k = max(p for e in MOTIFS[m] for p in e) + 1
            self.genes.append(MotifGene(m, [f"{prefix}{i}p{j}" for j in range(k)],
                                        w=round(rng.uniform(0.5, 1.5), 3)))
        return self

    def compile(self, graph: Any) -> Any:
        for g in self.genes:
            for p in g.ports:
                graph.add_node(p, kind="motif", attrs={"motif": g.motif})
            for a, b in MOTIFS[g.motif]:
                graph.add_edge(g.ports[a], g.ports[b], w=g.w)
        return graph

    def mutate(self, seed: int = 0) -> MotifGenome:
        """Bounded-damage mutation: rewire one port OR swap one motif kind."""
        rng = random.Random(seed)
        if not self.genes:
            return self
        g = rng.choice(self.genes)
        if rng.random() < 0.5 and len(g.ports) > 1:
            i, j = rng.sample(range(len(g.ports)), 2)
            g.ports[i], g.ports[j] = g.ports[j], g.ports[i]
        else:
            g.motif = rng.choice(sorted(MOTIFS))
            k = max(p for e in MOTIFS[g.motif] for p in e) + 1
            while len(g.ports) < k:
                g.ports.append(f"{g.ports[0]}x{len(g.ports)}")
            g.ports = g.ports[:k]
        self.generation += 1
        return self

    def crossover(self, other: MotifGenome, seed: int = 0) -> MotifGenome:
        """Single-point motif-block crossover (function-preserving)."""
        rng = random.Random(seed)
        if not self.genes or not other.genes:
            return MotifGenome(list(self.genes))
        cut = rng.randint(1, max(1, min(len(self.genes), len(other.genes)) - 1)) \
            if min(len(self.genes), len(other.genes)) > 1 else 1
        kid = MotifGenome(
            [MotifGene(g.motif, list(g.ports), g.w) for g in self.genes[:cut]] +
            [MotifGene(g.motif, list(g.ports), g.w) for g in other.genes[cut:]],
            generation=max(self.generation, other.generation) + 1)
        return kid

    def motif_histogram(self) -> dict[str, int]:
        h: dict[str, int] = {}
        for g in self.genes:
            h[g.motif] = h.get(g.motif, 0) + 1
        return h

    def to_dict(self) -> dict[str, Any]:
        return {"genes": [g.to_dict() for g in self.genes],
                "generation": self.generation, "fitness": self.fitness}
