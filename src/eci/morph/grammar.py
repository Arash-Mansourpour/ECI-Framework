"""Self-modifying grammar: the graph rewrites its own rewrite rules.

A Rule is LHS (edge predicate over src/dst/weight/age/causal_support) ->
RHS action (strengthen | prune | sprout | split | rewire) gated by a
condition on graph-level signals (surprise, lambda2, energy). Rules carry
a utility score updated by outcome (did λ2/utility improve after firing?)
— the grammar *learns which edits work*, closing the self-evolution loop.
``mine_rules()`` proposes candidates from co-active pairs so novelty comes
from data, not from a hardcoded list.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

__all__ = ["Rule", "GraphGrammar"]

Predicate = Callable[[str, str, Any], bool]  # (src, dst, edge) -> match


@dataclass
class Rule:
    name: str
    action: str            # strengthen | prune | sprout | split | rewire
    predicate: Predicate = field(repr=False, default=lambda s, d, e: True)
    need_surprise: float = 0.0
    need_lambda2: float = 0.0   # fire only if connectivity below this (repair bias)
    utility: float = 0.0
    fires: int = 0
    param: dict[str, Any] = field(default_factory=dict)


class GraphGrammar:
    def __init__(self) -> None:
        self.rules: list[Rule] = []

    def add(self, rule: Rule) -> None:
        self.rules.append(rule)

    def defaults(self) -> None:
        """Seed grammar: the five primordial edits."""
        self.add(Rule("hebb-strengthen", "strengthen",
                      lambda s, d, e: e.w < 2.0 and e.causal_support > 0.3,
                      need_surprise=0.0, param={"rate": 0.2}))
        self.add(Rule("rot-prune", "prune",
                      lambda s, d, e: e.age > 50 and e.w < 0.2,
                      param={}))
        self.add(Rule("hub-sprout", "sprout",
                      lambda s, d, e: True, need_surprise=0.5,
                      param={"from": "hub"}))
        self.add(Rule("overload-split", "split",
                      lambda s, d, e: False, param={"degree": 8}))
        self.add(Rule("stale-rewire", "rewire",
                      lambda s, d, e: e.age > 100 and e.causal_support < 0.1,
                      param={}))

    def mine_rules(self, pairs: list[tuple[str, str, float]], top_k: int = 3) -> list[Rule]:
        """Propose sprout-rules for the most surprising co-active pairs."""
        out = []
        for s, d, surprise in sorted(pairs, key=lambda t: -t[2])[:top_k]:
            if surprise <= 0.3:
                continue
            out.append(Rule(f"mined-{s}-{d}", "sprout",
                            lambda a, b, e, _s=s, _d=d: a == _s and b == _d,
                            need_surprise=0.3, utility=surprise,
                            param={"src": s, "dst": d, "mined": True}))
        self.rules.extend(out)
        return out

    def fire(self, graph: Any, surprise: float = 0.0,
             energy_budget: float = 10.0) -> dict[str, Any]:
        """One rewrite pass over matching edges; returns auditable receipt."""
        l2 = graph.algebraic_connectivity()
        fired: list[str] = []
        spent = 0.0
        before = (len(graph.nodes), len(graph.edges), l2)
        for rule in sorted(self.rules, key=lambda r: -r.utility):
            if surprise < rule.need_surprise:
                continue
            if rule.need_lambda2 and l2 >= rule.need_lambda2:
                continue
            for (s, d), e in list(graph.edges.items()):
                try:
                    match = rule.predicate(s, d, e)
                except Exception:  # noqa: BLE001
                    match = False
                if not match or spent >= energy_budget:
                    continue
                ok = self._apply(graph, rule, s, d)
                if ok:
                    rule.fires += 1
                    fired.append(f"{rule.name}:{s}>{d}")
                    spent += 1.0
                    e.age = 0
        # outcome credit: did connectivity hold or improve?
        after_l2 = graph.algebraic_connectivity()
        for rule in self.rules:
            if any(f.startswith(rule.name) for f in fired):
                rule.utility += 0.1 * (after_l2 - l2)
        for e in graph.edges.values():
            e.age += 1
        return {"fired": fired, "spent": spent, "lambda2_before": l2,
                "lambda2_after": after_l2,
                "delta_nodes": len(graph.nodes) - before[0],
                "delta_edges": len(graph.edges) - before[1]}

    def _apply(self, graph: Any, rule: Rule, s: str, d: str) -> bool:
        e = graph.edges[(s, d)]
        if rule.action == "strengthen":
            e.w = min(3.0, e.w + rule.param.get("rate", 0.2))
            return True
        if rule.action == "prune":
            return graph.del_edge(s, d, reason=f"grammar:{rule.name}")
        if rule.action == "sprout":
            src = rule.param.get("src", s)
            dst = rule.param.get("dst", f"{d}'")
            graph.add_edge(src, dst, w=0.5)
            return True
        if rule.action == "split":
            deg = sum(1 for (a, b) in graph.edges if a == s or b == s)
            if deg < rule.param.get("degree", 8):
                return False
            clone = f"{s}#2"
            graph.add_node(clone, kind=graph.nodes[s].kind)
            for (a, b), oe in list(graph.edges.items()):
                if a == s and hash(b) % 2 == 0:
                    graph.add_edge(clone, b, w=oe.w)
                    graph.del_edge(a, b, reason="split")
            return True
        if rule.action == "rewire":
            # re-target to the highest-utility node (preferential attach)
            best = max(graph.nodes.values(), key=lambda n: n.utility, default=None)
            if best is None or best.id in (s, d):
                return False
            w = e.w
            graph.del_edge(s, d, reason=f"grammar:{rule.name}")
            graph.add_edge(s, best.id, w=w, causal=e.causal_support)
            return True
        return False
