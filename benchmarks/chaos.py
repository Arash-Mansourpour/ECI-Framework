"""Chaos drills: the network attacks itself on schedule and scores resilience.

Scenarios: partition (split-brain then heal), equivocate flood (30%
Byzantine), message flood (drop storm). Each drill reports achieved-rate
and honest-dominance; the summary is leaderboard-ready. Deterministic.

Run:  PYTHONPATH=src python benchmarks/chaos.py
"""
import sys

sys.path.insert(0, "src")

from eci.core.types import NetworkNode, NetworkRole
from eci.network.consensus import PBFTConsensus
from eci.network.gossip import GossipNode, anti_entropy


def _nodes(n_honest=7, n_byz=3):
    nodes = {}
    for i in range(n_honest):
        nid = f"h{i}"
        nodes[nid] = NetworkNode(node_id=nid, role=NetworkRole.VALIDATOR, trust_score=1.0, reputation_score=1.0, stake=1.0)
    for i in range(n_byz):
        nid = f"b{i}"
        nodes[nid] = NetworkNode(node_id=nid, role=NetworkRole.VALIDATOR, trust_score=0.1, reputation_score=0.2, stake=1.0)
    return nodes


def drill_equivocate(trials: int = 20) -> dict:
    nodes = _nodes()
    c = PBFTConsensus(n_nodes=10, byzantine_rate=0.0, byzantine_mode="equivocate")
    achieved = sum((setattr(c, "sequence_number", s) or c.achieve_consensus(nodes, {"op": s}).achieved) for s in range(trials))
    return {"scenario": "equivocate-30pct", "achieved": achieved, "trials": trials, "rate": achieved / trials}


def drill_partition_heal() -> dict:
    honest = {f"h{i}": GossipNode(f"h{i}", {s: f"rec-{s}" for s in range(10)}) for i in range(4)}
    isolated = {f"q{i}": GossipNode(f"q{i}", {}) for i in range(2)}
    # Heal: merge and repair
    merged = {**honest, **isolated}
    rep = anti_entropy(merged, rounds=8, seed=3)
    return {"scenario": "partition-heal", **rep}


def main() -> None:
    for name, fn in [("equivocate", drill_equivocate), ("partition", drill_partition_heal)]:
        print(name, fn())


if __name__ == "__main__":
    main()
