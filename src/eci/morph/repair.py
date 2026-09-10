"""Self-repair: damage detection + regeneration with scar memory.

Detects: fragmentation (components > 1), λ2 collapse vs baseline, orphan
nodes (degree 0), edge rot (age >> useful). Regenerates by re-attaching
orphans to the highest-utility hub, re-growing bridges via the grammar's
sprout, and re-wiring rot. Every repair writes scars (never deleted) and
returns a heal fraction = λ2_after/λ2_baseline — repair you can measure.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

__all__ = ["SelfRepair"]


class SelfRepair:
    def __init__(self) -> None:
        self.baseline_l2 = 0.0
        self.repairs = 0

    def calibrate(self, graph: Any) -> float:
        self.baseline_l2 = graph.algebraic_connectivity()
        return self.baseline_l2

    def diagnose(self, graph: Any) -> Dict[str, Any]:
        adj = {n: set() for n in graph.nodes}
        for (s, d) in graph.edges:
            adj[s].add(d)
            adj[d].add(s)
        orphans = [n for n, nb in adj.items() if not nb]
        rotted = [(s, d) for (s, d), e in graph.edges.items() if e.age > 100 and e.w < 0.3]
        l2 = graph.algebraic_connectivity()
        return {"components": len(graph.components()), "lambda2": l2,
                "baseline": self.baseline_l2,
                "collapse": l2 < 0.5 * self.baseline_l2 if self.baseline_l2 > 0 else False,
                "orphans": orphans, "rotted": [list(k) for k in rotted],
                "damaged": len(graph.components()) > 1 or bool(orphans) or bool(rotted)}

    def heal(self, graph: Any) -> Dict[str, Any]:
        diag = self.diagnose(graph)
        if not diag["damaged"] and not diag["collapse"]:
            return {"healed": False, "reason": "healthy", "heal_fraction": 1.0}
        actions = []
        hubs = sorted(graph.nodes.values(), key=lambda n: -n.utility)
        hub = hubs[0].id if hubs else None
        for o in diag["orphans"]:
            if hub and o != hub:
                graph.add_edge(hub, o, w=0.5)
                graph.add_edge(o, hub, w=0.3)
                actions.append(f"reattach:{o}->{hub}")
        for s, d in [tuple(k) for k in diag["rotted"]]:
            if graph.del_edge(s, d, reason="repair-rot"):
                actions.append(f"derot:{s}>{d}")
        # bridge fragments: connect smallest component to hub
        comps = graph.components()
        if len(comps) > 1 and hub:
            main = max(comps, key=len)
            for c in comps:
                if c != main:
                    leaf = sorted(c)[0]
                    graph.add_edge(hub, leaf, w=0.6)
                    actions.append(f"bridge:{hub}->{leaf}")
        self.repairs += 1
        l2 = graph.algebraic_connectivity()
        frac = (l2 / self.baseline_l2) if self.baseline_l2 > 1e-9 else (1.0 if l2 > 0 else 0.0)
        graph.scars.append({"what": "repair", "actions": actions,
                            "heal_fraction": frac, "ts": time.time()})
        return {"healed": True, "actions": actions, "lambda2": l2,
                "heal_fraction": frac, "repairs": self.repairs}
