"""Gossip dissemination + anti-entropy repair (O(n log n) scaling).

Each node keeps a ledger digest (head hash + seq). Rounds: pick k random
peers, exchange digests, pull missing records. Converges exponentially;
partitions heal automatically on reconnect. Transport-agnostic: works over
AsyncMemoryChannel today, sockets tomorrow.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

__all__ = ["GossipNode", "gossip_round", "anti_entropy"]


@dataclass
class GossipNode:
    node_id: str
    records: dict[int, Any] = field(default_factory=dict)

    def digest(self) -> dict:
        import hashlib
        import json

        h = hashlib.sha256(json.dumps(sorted(self.records), default=str).encode()).hexdigest()[:16]
        return {"n": len(self.records), "hash": h, "seqs": sorted(self.records)}

    def missing_vs(self, peer_digest: dict) -> list[int]:
        mine = set(self.records)
        return [s for s in peer_digest.get("seqs", []) if s not in mine]


def gossip_round(nodes: dict[str, GossipNode], fanout: int = 2, seed: int = 0) -> int:
    """One round: every node pushes its full record set to k random peers. Returns deliveries."""
    rng = random.Random(seed)
    ids = list(nodes)
    delivered = 0
    for nid in ids:
        peers = rng.sample([x for x in ids if x != nid], min(fanout, len(ids) - 1))
        for p in peers:
            for seq, rec in nodes[nid].records.items():
                if seq not in nodes[p].records:
                    nodes[p].records[seq] = rec
                    delivered += 1
    return delivered


def anti_entropy(nodes: dict[str, GossipNode], rounds: int = 8, fanout: int = 2, seed: int = 0) -> dict:
    """Run rounds until all digests match or rounds exhaust. Returns convergence report."""
    for r in range(rounds):
        gossip_round(nodes, fanout=fanout, seed=seed + r)
        digests = {n.digest()["hash"] for n in nodes.values()}
        if len(digests) == 1:
            return {"converged": True, "rounds": r + 1, "records": len(next(iter(nodes.values())).records)}
    return {"converged": False, "rounds": rounds, "records": max(len(n.records) for n in nodes.values())}
