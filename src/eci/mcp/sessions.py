"""Sessions: namespaced, budgeted, attested MCP conversations.

A session binds subject + namespace + attestation + remaining budget, with
a per-session token bucket for rate control and heartbeat expiry. Agents
resume via ``session_id``; anonymous callers get an ephemeral session.
Expiry sweeps keep the mesh leak-free on long-lived servers.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

__all__ = ["Session", "SessionManager"]


@dataclass
class Session:
    id: str
    subject: str = "anon"
    namespace: str = "default"
    attestation: dict[str, float] = field(default_factory=dict)
    capabilities: list[str] = field(default_factory=list)
    budget: float = 100.0
    created: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    calls: int = 0
    tokens: float = 20.0  # session token-bucket balance
    rate_per_s: float = 10.0
    cap: float = 20.0

    def touch(self) -> None:
        now = time.time()
        self.tokens = min(self.cap, self.tokens + (now - self.last_seen) * self.rate_per_s)
        self.last_seen = now

    def allow(self, cost: float = 1.0) -> bool:
        self.touch()
        if self.tokens < cost:
            return False
        self.tokens -= cost
        return True

    def to_dict(self) -> dict[str, Any]:
        return {"session_id": self.id, "subject": self.subject, "namespace": self.namespace,
                "budget": self.budget, "calls": self.calls}


class SessionManager:
    def __init__(self, ttl_s: float = 1800.0) -> None:
        self.ttl = ttl_s
        self._sessions: dict[str, Session] = {}

    def create(self, subject: str = "anon", namespace: str = "default",
               attestation: dict[str, float] | None = None,
               capabilities: list[str] | None = None,
               budget: float = 100.0) -> Session:
        s = Session(id=uuid.uuid4().hex[:12], subject=subject, namespace=namespace,
                    attestation=attestation or {}, capabilities=capabilities or [], budget=budget)
        self._sessions[s.id] = s
        return s

    def get(self, session_id: str = "") -> Session | None:
        s = self._sessions.get(session_id)
        if s is None:
            return None
        if time.time() - s.last_seen > self.ttl:
            self._sessions.pop(session_id, None)
            return None
        return s

    def get_or_ephemeral(self, session_id: str = "", subject: str = "anon") -> Session:
        s = self.get(session_id) if session_id else None
        return s or self.create(subject=subject)

    def sweep(self) -> int:
        now = time.time()
        dead = [k for k, s in self._sessions.items() if now - s.last_seen > self.ttl]
        for k in dead:
            self._sessions.pop(k, None)
        return len(dead)

    def stats(self) -> dict[str, Any]:
        return {"sessions": len(self._sessions)}
