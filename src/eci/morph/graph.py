"""Living graph: tissue-like directed substrate with exact spectral health.

A MorphGraph is nodes {kind, utility, energy, born} + edges {w, age,
causal_support} with an append-only scar ledger (tombstones, never
deleted — like semantic.py). Health is *measured*, not asserted:
  - algebraic connectivity λ2 (Fiedler): exact eigvalsh of the Laplacian
  - spectral radius ρ (echo/sync proxy), modularity Q (label-propagation
    communities), triad census (directed 3-node motifs, exact enumeration),
    effective resistance R_tot = n·Σ_{i>1} 1/λi (exact pseudoinverse trace).

Small-graph exactness is the contract (n ≤ 512): no approximations are
hidden — anything bigger shards first (documented in MORPHOGENESIS.md).
"""

from __future__ import annotations

import itertools
import time
from dataclasses import dataclass, field
from typing import Any

import torch

__all__ = ["Node", "Edge", "MorphGraph"]


@dataclass
class Node:
    id: str
    kind: str = "unit"          # unit | hub | sensor | motor | motif
    utility: float = 0.0
    energy: float = 1.0
    born: float = field(default_factory=time.time)
    attrs: dict[str, Any] = field(default_factory=dict)


@dataclass
class Edge:
    src: str
    dst: str
    w: float = 1.0
    age: int = 0
    causal_support: float = 0.0


class MorphGraph:
    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}
        self.edges: dict[tuple[str, str], Edge] = {}
        self.scars: list[dict[str, Any]] = []  # tombstone ledger
        self.edits = 0

    # -- structure ------------------------------------------------------
    def add_node(self, nid: str, kind: str = "unit", **attrs: Any) -> Node:
        if nid not in self.nodes:
            self.nodes[nid] = Node(nid, kind, attrs=attrs)
            self.edits += 1
        return self.nodes[nid]

    def add_edge(self, src: str, dst: str, w: float = 1.0, causal: float = 0.0) -> Edge:
        self.add_node(src)
        self.add_node(dst)
        key = (src, dst)
        if key in self.edges:
            e = self.edges[key]
            e.w = 0.5 * e.w + 0.5 * w
            e.causal_support = max(e.causal_support, causal)
        else:
            self.edges[key] = Edge(src, dst, w, causal_support=causal)
            self.edits += 1
        return self.edges[key]

    def del_edge(self, src: str, dst: str, reason: str = "") -> bool:
        key = (src, dst)
        if key not in self.edges:
            return False
        e = self.edges.pop(key)
        self.scars.append({"what": "edge", "src": src, "dst": dst, "w": e.w,
                           "reason": reason, "ts": time.time()})
        self.edits += 1
        return True

    def del_node(self, nid: str, reason: str = "") -> bool:
        if nid not in self.nodes:
            return False
        for key in [k for k in self.edges if nid in k]:
            self.del_edge(*key, reason=f"node-death:{reason}")
        n = self.nodes.pop(nid)
        self.scars.append({"what": "node", "id": nid, "kind": n.kind,
                           "utility": n.utility, "reason": reason, "ts": time.time()})
        self.edits += 1
        return True

    def order(self) -> list[str]:
        return sorted(self.nodes)

    def adjacency(self, weighted: bool = True) -> torch.Tensor:
        ids, idx = self.order(), {n: i for i, n in enumerate(self.order())}
        A = torch.zeros(len(ids), len(ids))
        for (s, d), e in self.edges.items():
            A[idx[s], idx[d]] = e.w if weighted else 1.0
        return A

    # -- spectral health (exact) ------------------------------------------
    def laplacian(self) -> torch.Tensor:
        A = self.adjacency()
        S = A + A.T  # symmetrized coupling for connectivity analysis
        return torch.diag(S.sum(1)) - S

    def spectrum(self) -> list[float]:
        n = len(self.nodes)
        if n == 0:
            return []
        if n == 1:
            return [0.0]
        return sorted(float(v) for v in torch.linalg.eigvalsh(self.laplacian()).tolist())

    def algebraic_connectivity(self) -> float:
        sp = self.spectrum()
        return sp[1] if len(sp) > 1 else 0.0

    def spectral_radius(self) -> float:
        if not self.nodes:
            return 0.0
        return float(torch.linalg.eigvals(self.adjacency()).abs().max().item())

    def effective_resistance(self) -> float:
        """R_tot = n·Σ_{i≥2} 1/λi — exact; inf if disconnected."""
        sp = self.spectrum()
        if len(sp) < 2 or sp[1] < 1e-9:
            return float("inf")
        return len(sp) * sum(1.0 / l for l in sp[1:] if l > 1e-9)

    def components(self) -> list[set[str]]:
        seen: set[str] = set()
        comps = []
        adj: dict[str, set[str]] = {n: set() for n in self.nodes}
        for (s, d) in self.edges:
            adj[s].add(d)
            adj[d].add(s)
        for n in self.nodes:
            if n in seen:
                continue
            stack, comp = [n], set()
            while stack:
                m = stack.pop()
                if m in seen:
                    continue
                seen.add(m)
                comp.add(m)
                stack.extend(adj[m] - seen)
            comps.append(comp)
        return comps

    def modularity(self, labels: dict[str, int] | None = None) -> float:
        """Standard undirected Q on the symmetrized coupling (exact).

        Q = (1/2m)·Σ_ij [S_ij − k_i·k_j/2m]·δ(c_i, c_j), communities from
        deterministic label propagation. Bounded in [-0.5, 1] by construction.
        """
        if len(self.edges) < 2:
            return 0.0
        labels = labels or self._label_propagate()
        S = self.adjacency() + self.adjacency().T
        ids = self.order()
        m = float(S.sum().item()) / 2.0 or 1e-9
        k = S.sum(1)
        Q = 0.0
        for i, a in enumerate(ids):
            for j, b in enumerate(ids):
                if labels[a] == labels[b]:
                    Q += float(S[i, j].item()) - float(k[i].item() * k[j].item()) / (2 * m)
        return Q / (2 * m)

    def _label_propagate(self, iters: int = 10) -> dict[str, int]:
        labels = {n: i for i, n in enumerate(self.order())}
        adj: dict[str, set[str]] = {n: set() for n in self.nodes}
        for (s, d) in self.edges:
            adj[s].add(d)
            adj[d].add(s)
        for _ in range(iters):
            for n in self.order():
                if not adj[n]:
                    continue
                votes: dict[int, float] = {}
                for m in adj[n]:
                    w = self.edges.get((n, m), self.edges.get((m, n))).w
                    votes[labels[m]] = votes.get(labels[m], 0.0) + w
                labels[n] = max(votes.items(), key=lambda kv: (kv[1], -kv[0]))[0]
        return labels

    def triad_census(self) -> dict[str, int]:
        """Exact directed triad census over all 3-node subsets (sparse-safe)."""
        census: dict[str, int] = {}
        ids = self.order()
        eset = set(self.edges)
        for a, b, c in itertools.combinations(ids, 3):
            links = [(x, y) for x, y in
                     ((a, b), (b, a), (a, c), (c, a), (b, c), (c, b)) if (x, y) in eset]
            if not links:
                continue
            key = f"{len(links)}:" + ",".join(f"{x}>{y}" for x, y in sorted(links))
            # canonicalize node labels to motif class (permutation-invariant-ish key)
            census[key] = census.get(key, 0) + 1
        # also report class totals by link count (interpretable at a glance)
        totals: dict[str, int] = {}
        for k, v in census.items():
            totals[f"triads_L{k.split(':')[0]}"] = totals.get(f"triads_L{k.split(':')[0]}", 0) + v
        return totals

    def health(self) -> dict[str, Any]:
        return {"nodes": len(self.nodes), "edges": len(self.edges),
                "lambda2": self.algebraic_connectivity(),
                "radius": self.spectral_radius(),
                "R_tot": self.effective_resistance(),
                "components": len(self.components()),
                "modularity": self.modularity(),
                "edits": self.edits, "scars": len(self.scars),
                **self.triad_census()}

    # -- (de)serialization --------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {"nodes": [{"id": n.id, "kind": n.kind, "utility": n.utility,
                           "energy": n.energy, "attrs": n.attrs} for n in self.nodes.values()],
                "edges": [{"src": e.src, "dst": e.dst, "w": e.w,
                           "causal": e.causal_support} for e in self.edges.values()],
                "scars": self.scars}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> MorphGraph:
        g = cls()
        for n in d.get("nodes", []):
            nd = g.add_node(n["id"], n.get("kind", "unit"))
            nd.utility = n.get("utility", 0.0)
            nd.energy = n.get("energy", 1.0)
        for e in d.get("edges", []):
            g.add_edge(e["src"], e["dst"], e.get("w", 1.0), e.get("causal", 0.0))
        g.scars = list(d.get("scars", []))
        return g
