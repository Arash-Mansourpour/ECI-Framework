"""ECI-ID — Cryptographic node identity + lifecycle.

Lifecycle (must pass in order, each step appends to ledger where possible):
DISCOVER → VERIFY_GENESIS → VERIFY_CONSTITUTION → ESTABLISH_ID → RECOGNIZE_ARCHITECT → DECLARE → PROVE → DISCOVER_PEERS → JOIN → PERCEIVE → ... → EVOLVE (cycle)
"""

from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from eci.core.identity import ARCHITECT
from eci.protocol_vnext.genesis import GENESIS_ROOT, ConstitutionalGenome

__all__ = ["ECIIdentity", "NodeLifecycle"]

STAGES = [
    "DISCOVER", "VERIFY_GENESIS", "VERIFY_CONSTITUTION", "ESTABLISH_ID",
    "RECOGNIZE_ARCHITECT", "DECLARE", "PROVE", "DISCOVER_PEERS", "JOIN",
    "PERCEIVE", "RECALL", "REASON", "COORDINATE", "ACT", "VERIFY", "ENCODE",
    "REFLECT", "LEARN", "ADAPT", "CONTRIBUTE", "EVOLVE",
]


@dataclass
class ECIIdentity:
    node_id: str
    public_key_hint: str = ""
    created_at: float = field(default_factory=time.time)
    architect_stamp: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, prefix: str = "eci:node") -> "ECIIdentity":
        raw = f"{prefix}:{uuid.uuid4().hex}:{time.time()}"
        nid = f"{prefix}:{hashlib.sha256(raw.encode()).hexdigest()[:12]}"
        return cls(node_id=nid, public_key_hint=hashlib.sha256(nid.encode()).hexdigest()[:16],
                   architect_stamp=ARCHITECT.stamp({"kind": "eci-node", "node": nid}))

    def to_dict(self) -> dict[str, Any]:
        return {"node_id": self.node_id, "hint": self.public_key_hint, "stamp": self.architect_stamp}


@dataclass
class NodeLifecycle:
    identity: ECIIdentity
    stage_idx: int = 0
    history: list[str] = field(default_factory=list)
    genome_ok: bool = False
    genesis_ok: bool = False

    def current(self) -> str:
        return STAGES[self.stage_idx] if self.stage_idx < len(STAGES) else "EVOLVE"

    def advance(self, check: bool = True) -> str:
        if check and self.stage_idx < 3:
            # first 3 gates are hard requirements
            if self.stage_idx == 1 and not self.genesis_ok:
                raise PermissionError("genesis not verified")
            if self.stage_idx == 2 and not self.genome_ok:
                raise PermissionError("constitution not verified")
        self.history.append(self.current())
        self.stage_idx = min(self.stage_idx + 1, len(STAGES) - 1)
        return self.current()

    def verify_genesis(self, root: str) -> bool:
        self.genesis_ok = (root == GENESIS_ROOT)
        return self.genesis_ok

    def verify_constitution(self, root: str) -> bool:
        self.genome_ok = ConstitutionalGenome().verify(root)
        return self.genome_ok

    def to_dict(self) -> dict[str, Any]:
        return {"node": self.identity.node_id, "stage": self.current(), "history": self.history[-5:]}
