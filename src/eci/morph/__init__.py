"""Morphogenesis facade: the living-network organ of ECI.

Owns one living MorphGraph + grammar + Darwin selector + motif genome +
self-repair + coevolver. ``evolve_step()`` is the heartbeat:

  probe tasks -> credit -> grammar rewrite -> darwin triage ->
  motif grow (energy-funded) -> repair -> causal rewire -> report

Every structural edit flows to provenance + bus + audit, so evolution is
as accountable as any DAO vote — growth without governance is cancer.
"""

from __future__ import annotations

import random
import time
from typing import Any, Callable, Dict, List, Optional

from eci.morph.coevolve import Coevolver
from eci.morph.grammar import GraphGrammar
from eci.morph.graph import MorphGraph
from eci.morph.motifs import MotifGenome
from eci.morph.repair import SelfRepair
from eci.morph.selection import DarwinSelector, SelectionConfig

__all__ = ["Morphogenesis"]


class Morphogenesis:
    name = "morphogenesis"

    def __init__(self, seed: int = 0, bus=None, provenance=None, audit=None) -> None:
        self.graph = MorphGraph()
        self.grammar = GraphGrammar()
        self.grammar.defaults()
        self.selector = DarwinSelector()
        self.motifs = MotifGenome().random(motifs=3, seed=seed, prefix="m0")
        self.motifs.compile(self.graph)
        self.repair = SelfRepair()
        self.repair.calibrate(self.graph)
        self.coevolver = Coevolver()
        self.coevolver.seed(seed)
        self.bus = bus
        self.provenance = provenance
        self.audit = audit
        self.steps = 0

    def evolve_step(self, probes: List[Callable[[MorphGraph], float]] | None = None,
                    reward: float = 0.0, active: List[str] | None = None,
                    surprise: float = 0.0, seed: int = 0) -> Dict[str, Any]:
        t0 = time.time()
        g = self.graph
        # 1. evaluate living graph on task probes
        rewards = [p(g) for p in (probes or [])]
        r = (sum(rewards) / len(rewards) if rewards else reward)
        # 2. credit + grammar rewrite (self-modification)
        self.selector.credit(g, r, active)
        receipt = self.grammar.fire(g, surprise=surprise,
                                    energy_budget=min(10.0, self.selector.energy_pool))
        # 3. darwin triage (selection pressure)
        tri = self.selector.triage(g, seed=seed)
        # 4. motif growth funded by energy pool
        from eci.morph.motifs import MOTIFS, MotifGene
        grown = []
        rng = random.Random(seed)
        while self.selector.energy_pool > 4.0 and len(grown) < 2:
            m = rng.choice(sorted(MOTIFS))
            k = max(p for e in MOTIFS[m] for p in e) + 1
            gene = MotifGene(m, [f"n{len(g.nodes)}p{j}" for j in range(k)], w=1.0)
            self.motifs.genes.append(gene)
            for p in gene.ports:
                g.add_node(p, kind="motif", attrs={"motif": m})
            for a, b in MOTIFS[m]:
                g.add_edge(gene.ports[a], gene.ports[b], w=1.0)
            self.selector.energy_pool -= 2.0
            grown.append(m)
        # 5. repair + causal rewire hook (strengthen causally-supported edges)
        heal = self.repair.heal(g)
        for (s, d), e in g.edges.items():
            if e.causal_support > 0.5:
                e.w = min(3.0, e.w + 0.05)
        self.steps += 1
        report = {"step": self.steps, "reward": r, "grammar": receipt,
                  "triage": tri, "grown": grown, "heal": heal,
                  "health": g.health(), "duration_s": time.time() - t0}
        try:
            if self.provenance is not None:
                node = self.provenance.record("morph.evolve", "morphogenesis",
                                              {"reward": r, "surprise": surprise},
                                              {"lambda2": g.health()["lambda2"], "grown": grown},
                                              {"edits": g.edits})
                report["provenance_id"] = node.id
            if self.audit is not None:
                self.audit.append("morphogenesis", "morph.evolve", {"step": self.steps})
            if self.bus is not None:
                from eci.kernel.bus import Event
                self.bus.publish(Event(type="morph.evolve.done", source="morphogenesis",
                                       payload={"step": self.steps, "reward": r}))
        except Exception:  # noqa: BLE001
            pass
        return report

    def start(self) -> None: ...
    def stop(self) -> None: ...
    def health(self) -> Dict[str, Any]:
        return {"ok": True, "steps": self.steps, **self.graph.health(),
                "rules": len(self.grammar.rules), "pool": self.selector.energy_pool,
                "repairs": self.repair.repairs}
