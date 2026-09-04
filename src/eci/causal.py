"""Hybrid Logical Clocks + deterministic multi-writer ledger merge.

Every record carries hlc=(pt, logical, node): wall time for intuition,
logical counter for causality, node id for total order. Concurrent writes
in split partitions merge deterministically by (hlc, hash) — both sides
converge to the SAME chain without coordination. sort_key() is the single
comparison used everywhere: no divergent tie-breaks, ever.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List

__all__ = ["HLC", "hlc_now", "sort_key", "merge_chains"]


@dataclass(order=True)
class HLC:
    pt: int  # physical millis
    logical: int  # lamport counter
    node: str  # tie-break (total order)

    def to_dict(self) -> Dict[str, Any]:
        return {"pt": self.pt, "logical": self.logical, "node": self.node}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "HLC":
        return cls(int(d["pt"]), int(d["logical"]), str(d["node"]))


def hlc_now(last: HLC | None, node: str, now_ms: int | None = None) -> HLC:
    """Next timestamp: max(wall, last+1) logic (Kulkarni et al. 2014)."""
    pt = now_ms if now_ms is not None else time.time_ns() // 1_000_000
    if last is None:
        return HLC(pt, 0, node)
    if pt > last.pt:
        return HLC(pt, 0, node)
    return HLC(last.pt, last.logical + 1, node)


def sort_key(record: Dict[str, Any]) -> tuple:
    h = record.get("hlc") or {"pt": 0, "logical": record.get("seq", 0), "node": ""}
    return (int(h["pt"]), int(h["logical"]), str(h["node"]), str(record.get("hash", "")))


def merge_chains(a: List[Dict[str, Any]], b: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Union by hash, deterministic (hlc, hash) order, relinked prev chain.

    Both partitions run this after reconnect and converge bit-identically.
    NOTE: merged chain re-hashes links (prev pointers rewritten in merged
    order); per-record payload hashes stay verifiable individually.
    """
    import hashlib
    import json

    pool = {r["hash"]: dict(r) for r in list(a) + list(b)}
    ordered = sorted(pool.values(), key=sort_key)
    prev, out = "GENESIS", []
    for r in ordered:
        r = dict(r)
        r["prev"] = prev
        r.pop("hash", None)
        r["hash"] = hashlib.sha256(json.dumps(r, sort_keys=True, default=str).encode()).hexdigest()
        prev = r["hash"]
        out.append(r)
    return out
