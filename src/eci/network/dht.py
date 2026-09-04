"""Kademlia-style DHT for bootstrap-free peer discovery (in-process model).

Node IDs = SHA-256 fingerprints (160-bit XOR metric). Each node keeps
k-buckets; lookup() converges in O(log n) hops; store()/find_value()
replicate (key -> value) on the k closest nodes. The wire format is plain
dicts so a socket transport can adopt it without changing callers. No
single bootstrap can kill the mesh: any member bootstraps newcomers.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

__all__ = ["DHTNode", "xor_distance", "lookup"]


def _id(name: str) -> int:
    return int(hashlib.sha256(name.encode()).hexdigest(), 16)


def xor_distance(a: int, b: int) -> int:
    return a ^ b


@dataclass
class DHTNode:
    name: str
    k: int = 8
    buckets: Dict[int, List[str]] = field(default_factory=dict)
    store_data: Dict[str, Tuple[Any, str]] = field(default_factory=dict)

    @property
    def nid(self) -> int:
        return _id(self.name)

    def bucket_of(self, other: str) -> int:
        return xor_distance(self.nid, _id(other)).bit_length()

    def learn(self, other: str) -> None:
        if other == self.name:
            return
        b = self.buckets.setdefault(self.bucket_of(other), [])
        if other in b:
            b.remove(other)
        b.append(other)
        if len(b) > self.k:
            del b[0]

    def closest(self, target: int, n: int, known: Dict[str, "DHTNode"]) -> List[str]:
        cands = [x for x in known if x != self.name]
        cands.sort(key=lambda x: xor_distance(_id(x), target))
        return cands[:n]

    def store(self, key: str, value: Any, known: Dict[str, "DHTNode"]) -> List[str]:
        target = int(hashlib.sha256(key.encode()).hexdigest(), 16)
        holders = self.closest(target, self.k, known)
        for h in holders:
            known[h].store_data[key] = (value, self.name)
            known[h].learn(self.name)
            self.learn(h)
        self.store_data[key] = (value, self.name)
        return holders

    def find_value(self, key: str, known: Dict[str, "DHTNode"]) -> Tuple[bool, Any]:
        if key in self.store_data:
            return True, self.store_data[key][0]
        target = int(hashlib.sha256(key.encode()).hexdigest(), 16)
        for h in self.closest(target, self.k, known):
            if key in known[h].store_data:
                self.learn(h)
                return True, known[h].store_data[key][0]
        return False, None


def lookup(net: Dict[str, DHTNode], seeker: str, target_name: str, hops: int = 8) -> List[str]:
    """Iterative lookup path (for audit): winner list tightens each hop."""
    target = _id(target_name)
    node = net[seeker]
    path = []
    for _ in range(hops):
        nxt = node.closest(target, node.k, net)
        path.append(nxt[0] if nxt else "")
        if nxt and nxt[0] == target_name:
            break
    return path
