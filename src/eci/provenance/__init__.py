"""Decision provenance: causal trace graph with replay + explanation.

Every gated decision (consensus vote, DAO tally, authz verdict, precog
hold, court ruling) appends a node: {inputs, policy, outputs, actor}.
Edges link causation_id -> event_id so any outcome is replayable and
explainable for auditors, courts and risk markets.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

__all__ = ["TraceNode", "ProvenanceGraph"]


@dataclass
class TraceNode:
    id: str
    kind: str            # e.g. "authz.decision", "dao.vote", "court.verdict"
    actor: str
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    policy: Dict[str, Any] = field(default_factory=dict)
    parent: str = ""
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ProvenanceGraph:
    name = "provenance"

    def __init__(self, capacity: int = 4096) -> None:
        self._nodes: Dict[str, TraceNode] = {}
        self._order: List[str] = []
        self._capacity = capacity

    def record(self, kind: str, actor: str, inputs: Dict[str, Any],
               outputs: Dict[str, Any], policy: Dict[str, Any] | None = None,
               parent: str = "") -> TraceNode:
        node = TraceNode(id=uuid.uuid4().hex[:12], kind=kind, actor=actor,
                         inputs=inputs, outputs=outputs, policy=policy or {}, parent=parent)
        self._nodes[node.id] = node
        self._order.append(node.id)
        if len(self._order) > self._capacity:
            old = self._order.pop(0)
            self._nodes.pop(old, None)
        return node

    def lineage(self, node_id: str) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        cur = self._nodes.get(node_id)
        while cur is not None:
            out.append(cur.to_dict())
            cur = self._nodes.get(cur.parent) if cur.parent else None
        return list(reversed(out))

    def explain(self, node_id: str) -> str:
        chain = self.lineage(node_id)
        if not chain:
            return f"no trace {node_id}"
        lines = [f"{n['kind']} by {n['actor']} -> {n['outputs']}" for n in chain]
        return " <= ".join(lines)

    def query(self, kind: str = "", actor: str = "", limit: int = 100) -> List[Dict[str, Any]]:
        out = [n.to_dict() for n in self._nodes.values()
               if (not kind or n.kind == kind) and (not actor or n.actor == actor)]
        return out[-limit:]

    def start(self) -> None: ...
    def stop(self) -> None: ...
    def health(self) -> Dict[str, Any]:
        return {"ok": True, "nodes": len(self._nodes)}
