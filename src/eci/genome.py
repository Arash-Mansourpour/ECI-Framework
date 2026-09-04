"""Protocol genome: the constitution becomes an evolving species.

Policy parameters are GENES. Mutations are proposed, simulated in the
digital twin, trialed on a canary cohort, voted by the DAO, and — only
if obedience AND resilience improve — recorded in the genome registry
and published to federated meshes. Harmful genes go extinct by the same
machinery that adopts good ones. The protocol stops being a document and
starts being an organism.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List

__all__ = ["Gene", "Genome", "mutate", "life_cycle"]


@dataclass
class Gene:
    name: str
    params: Dict[str, float]
    fitness: float = 0.0
    generation: int = 0
    lineage: List[str] = field(default_factory=list)


@dataclass
class Genome:
    genes: Dict[str, Gene] = field(default_factory=dict)  # name -> champion

    def register(self, gene: Gene) -> None:
        cur = self.genes.get(gene.name)
        if cur is None or gene.fitness > cur.fitness:
            self.genes[gene.name] = gene

    def export(self) -> Dict[str, Any]:
        return {n: {"params": g.params, "fitness": round(g.fitness, 4), "gen": g.generation} for n, g in self.genes.items()}


def mutate(gene: Gene, seed: int = 0, scale: float = 0.1) -> Gene:
    rng = random.Random(f"{gene.name}|{seed}")
    child = Gene(gene.name, {k: max(0.0, min(1.0, v + rng.gauss(0, scale))) for k, v in gene.params.items()},
                 generation=gene.generation + 1, lineage=gene.lineage + [f"g{gene.generation}"])
    return child


def life_cycle(
    gene: Gene,
    simulate: Callable[[Dict[str, float]], Dict[str, float]],
    canary: Callable[[Dict[str, float]], Dict[str, float]],
    vote: Callable[[Dict[str, float]], bool],
    genome: Genome,
    seed: int = 0,
    ledger=None,
) -> Dict[str, Any]:
    """mutate -> twin verdict -> canary trial -> DAO vote -> register/publish."""
    child = mutate(gene, seed)
    from eci.twin import what_if

    sim = what_if(f"gene-{gene.name}-g{child.generation}", child.params, [{"x": 1}], simulate)
    if sim["verdict"] != "adopt":
        if ledger:
            ledger.append("genome_reject", {"gene": gene.name, "stage": "twin", "deltas": sim["deltas"]})
        return {"adopted": False, "stage": "twin", "report": sim}
    trial = canary(child.params)
    if trial.get("resilience", 1.0) < 0.9 * trial.get("baseline_resilience", 1.0):
        if ledger:
            ledger.append("genome_reject", {"gene": gene.name, "stage": "canary"})
        return {"adopted": False, "stage": "canary", "trial": trial}
    if not vote(child.params):
        if ledger:
            ledger.append("genome_reject", {"gene": gene.name, "stage": "dao"})
        return {"adopted": False, "stage": "dao"}
    child.fitness = round(trial.get("obedience", 0.0) + trial.get("resilience", 0.0), 4)
    genome.register(child)
    if ledger:
        ledger.append("genome_adopt", {"gene": gene.name, "gen": child.generation, "fitness": child.fitness})
    return {"adopted": True, "gene": child, "fitness": child.fitness}
