"""Neural Darwinism: selection pressure on structure, not just weights.

Fitness per element = utility − λ·metabolic_cost + μ·robustness, where
robustness is the element's marginal contribution to λ2 (leave-one-out,
exact on small graphs, sampled on large). Credit flows by reward-weighted
eligibility traces; modules get sampled Shapley-lite values. Tournament
pruning removes losers; the energy pool (fed by rewards, taxed by edges)
funds growth — structure obeys thermodynamics.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

__all__ = ["SelectionConfig", "DarwinSelector"]


@dataclass
class SelectionConfig:
    lmbda_cost: float = 0.05   # metabolic tax per edge-weight
    mu_robust: float = 0.5     # reward for connectivity contribution
    prune_k: int = 2           # losers removed per triage
    tournament: int = 3
    shapley_samples: int = 16


class DarwinSelector:
    def __init__(self, cfg: SelectionConfig | None = None) -> None:
        self.cfg = cfg or SelectionConfig()
        self.energy_pool = 10.0
        self.elig: dict[str, float] = {}  # node -> eligibility trace
        self.rounds = 0

    # -- credit ---------------------------------------------------------
    def credit(self, graph: Any, reward: float, active: list[str] | None = None,
               decay: float = 0.9) -> None:
        for n in list(self.elig):
            self.elig[n] *= decay
        for n in (active or list(graph.nodes)):
            self.elig[n] = self.elig.get(n, 0.0) + reward
            if n in graph.nodes:
                graph.nodes[n].utility += 0.1 * reward
        self.energy_pool = max(0.0, self.energy_pool + reward)

    def robustness(self, graph: Any, edge: tuple[str, str], samples: int = 0) -> float:
        """Marginal λ2 contribution of an edge (exact leave-one-out)."""
        base = graph.algebraic_connectivity()
        e = graph.edges.get(edge)
        if e is None:
            return 0.0
        graph.edges.pop(edge)
        drop = base - graph.algebraic_connectivity()
        graph.edges[edge] = e
        return drop

    def fitness_edge(self, graph: Any, edge: tuple[str, str]) -> float:
        c = self.cfg
        e = graph.edges[edge]
        u = 0.5 * (graph.nodes[e.src].utility + graph.nodes[e.dst].utility)
        return u - c.lmbda_cost * e.w + c.mu_robust * self.robustness(graph, edge)

    def shapley_module(self, graph: Any, members: list[str], value_fn: Any,
                       seed: int = 0) -> dict[str, float]:
        """Sampled Shapley-lite over a module's nodes (exact formula, sampled perms)."""
        rng = random.Random(seed)
        phi = {m: 0.0 for m in members}
        S = max(4, self.cfg.shapley_samples)
        for _ in range(S):
            perm = rng.sample(members, len(members))
            prev = value_fn([])
            for i, m in enumerate(perm):
                cur = value_fn(perm[:i + 1])
                phi[m] += (cur - prev) / S
                prev = cur
        return phi

    # -- triage -----------------------------------------------------------
    def triage(self, graph: Any, seed: int = 0) -> dict[str, Any]:
        """Tournament prune bottom-k edges; returns receipt."""
        rng = random.Random(seed)
        c = self.cfg
        scored = [(self.fitness_edge(graph, k), k) for k in list(graph.edges)]
        pruned = []
        for _ in range(min(c.prune_k, len(scored))):
            if len(scored) < c.tournament:
                break
            contenders = rng.sample(scored, c.tournament)
            loser = min(contenders, key=lambda t: t[0])
            if graph.del_edge(*loser[1], reason="darwin-triage"):
                pruned.append({"edge": list(loser[1]), "fitness": loser[0]})
            scored = [(f, k) for f, k in scored if k != loser[1]]
        # metabolic tax collection
        tax = c.lmbda_cost * sum(e.w for e in graph.edges.values())
        self.energy_pool = max(0.0, self.energy_pool - tax)
        # node utilities decay; starved nodes flagged
        starved = []
        for n in graph.nodes.values():
            n.utility *= 0.95
            if n.utility < -2.0:
                starved.append(n.id)
        self.rounds += 1
        return {"pruned": pruned, "tax": tax, "pool": self.energy_pool,
                "starved": starved, "rounds": self.rounds}
