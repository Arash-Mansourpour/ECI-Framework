"""ECI-MSG — Async Message Fabric.

Types: TASK/RESULT/EVENT/PROPOSAL/VOTE/ERROR/HEALTH/CANCEL/CAPABILITY_UPDATE/KNOWLEDGE_PROPOSAL/EVIDENCE/CONTRADICTION/EVOLUTION_PROPOSAL
Envelope: message_id, correlation_id, sender, recipient, type, priority, ttl, signature, trace
Transports: swappable (MemoryChannel default; adapters for MQTT/NATS/Kafka/A2A/libp2p)
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

__all__ = ["ECIMessage", "MessageFabric"]

TYPES = ["TASK", "RESULT", "EVENT", "PROPOSAL", "VOTE", "ERROR", "HEALTH",
         "CANCEL", "CAPABILITY_UPDATE", "KNOWLEDGE_PROPOSAL", "EVIDENCE",
         "CONTRADICTION", "EVOLUTION_PROPOSAL"]


@dataclass
class ECIMessage:
    type: str
    sender: str
    recipient: str = "*"
    payload: dict[str, Any] = field(default_factory=dict)
    correlation_id: str = ""
    priority: int = 5
    ttl: int = 3600
    message_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    ts: float = field(default_factory=time.time)
    trace: list[str] = field(default_factory=list)
    signature: str = ""

    def __post_init__(self) -> None:
        if self.type not in TYPES:
            raise ValueError(f"unknown type {self.type}")
        if not self.correlation_id:
            self.correlation_id = self.message_id

    def sign(self, key: str = "demo-key") -> str:
        canonical = json.dumps({"t": self.type, "s": self.sender, "r": self.recipient,
                                "p": self.payload, "c": self.correlation_id}, sort_keys=True)
        self.signature = hashlib.sha256(f"{key}|{canonical}".encode()).hexdigest()[:16]
        return self.signature

    def to_dict(self) -> dict[str, Any]:
        return {"message_id": self.message_id, "correlation_id": self.correlation_id,
                "sender": self.sender, "recipient": self.recipient, "type": self.type,
                "priority": self.priority, "ttl": self.ttl, "payload": self.payload,
                "trace": self.trace, "signature": self.signature, "ts": self.ts}


class MessageFabric:
    """In-memory pub/sub fabric (transport-agnostic)."""

    def __init__(self) -> None:
        self._queues: dict[str, list[ECIMessage]] = {}
        self._subscribers: dict[str, list[str]] = {}
        self.history: list[ECIMessage] = []

    def publish(self, msg: ECIMessage) -> None:
        msg.trace.append(f"fabric@{time.time():.2f}")
        self.history.append(msg)
        # deliver to recipient queue or broadcast
        qkey = msg.recipient if msg.recipient != "*" else "__broadcast__"
        self._queues.setdefault(qkey, []).append(msg)
        # also copy to subscribers of type
        for sub, types in self._subscribers.items():
            if msg.type in types or "*" in types:
                self._queues.setdefault(f"sub:{sub}", []).append(msg)

    def subscribe(self, subscriber: str, types: list[str]) -> None:
        self._subscribers[subscriber] = types

    def poll(self, recipient: str, limit: int = 10) -> list[ECIMessage]:
        q = self._queues.get(recipient, [])
        out, rest = q[:limit], q[limit:]
        self._queues[recipient] = rest
        return out

    def poll_broadcast(self, limit: int = 10) -> list[ECIMessage]:
        return self.poll("__broadcast__", limit)

    def stats(self) -> dict[str, Any]:
        return {"queued": {k: len(v) for k, v in self._queues.items()},
                "history": len(self.history), "subscribers": len(self._subscribers)}
