"""Transparency log: Merkle-tree public record for attestations (CT-style).

No valid attestation is accepted outside this log: witnesses append
attestation hashes, publish signed tree heads, and anyone can demand an
inclusion proof. Pure-python SHA-256 Merkle tree (RFC 6962 leaf hashing).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

__all__ = ["TransparencyLog", "inclusion_proof", "verify_inclusion"]


def _h(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def _leaf_hash(payload: bytes) -> bytes:
    return _h(b"\x00" + payload)


def _node_hash(left: bytes, right: bytes) -> bytes:
    return _h(b"\x01" + left + right)


@dataclass
class TransparencyLog:
    leaves: List[bytes] = field(default_factory=list)

    def append(self, payload: bytes) -> int:
        self.leaves.append(_leaf_hash(payload))
        return len(self.leaves) - 1

    def root(self) -> bytes:
        if not self.leaves:
            return _h(b"empty")
        level = list(self.leaves)
        while len(level) > 1:
            nxt = []
            for i in range(0, len(level), 2):
                r = level[i + 1] if i + 1 < len(level) else level[i]
                nxt.append(_node_hash(level[i], r))
            level = nxt
        return level[0]

    def head(self) -> Dict:
        return {"n": len(self.leaves), "root": self.root().hex()}


def inclusion_proof(log: TransparencyLog, index: int) -> List[Tuple[str, str]]:
    """Sibling hashes bottom-up: [(side, hex)] where side is L/R of sibling."""
    if not 0 <= index < len(log.leaves):
        raise ValueError("leaf index out of range")
    level, idx, proof = list(log.leaves), index, []
    while len(level) > 1:
        sib = idx ^ 1
        sib = sib if sib < len(level) else idx
        proof.append(("R" if sib > idx else "L", level[sib].hex()))
        nxt = []
        for i in range(0, len(level), 2):
            r = level[i + 1] if i + 1 < len(level) else level[i]
            nxt.append(_node_hash(level[i], r))
        level, idx = nxt, idx // 2
    return proof


def verify_inclusion(root_hex: str, leaf_payload: bytes, index: int, proof: List[Tuple[str, str]], total: int) -> bool:
    cur = _leaf_hash(leaf_payload)
    idx = index
    for side, sib_hex in proof:
        sib = bytes.fromhex(sib_hex)
        cur = _node_hash(sib, cur) if side == "L" else _node_hash(cur, sib)
        idx //= 2
    _ = total
    return cur.hex() == root_hex
