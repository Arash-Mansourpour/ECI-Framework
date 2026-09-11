"""Kernel event bus: typed async/sync pub-sub backbone for ECI v6.

Every subsystem publishes domain events here instead of calling peers
directly. Features: wildcard topics (``a.b.*``), correlation/causation
chaining, bounded replay buffer, dead-letter queue, sync+async handlers.
"""

from __future__ import annotations

import asyncio
import fnmatch
import time
import uuid
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

__all__ = ["Event", "Subscription", "EventBus"]


@dataclass(frozen=True)
class Event:
    """Immutable domain event."""

    type: str
    payload: dict[str, Any] = field(default_factory=dict)
    source: str = "unknown"
    correlation_id: str = ""
    causation_id: str = ""
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    ts: float = field(default_factory=time.time)

    def child(self, type: str, payload: dict[str, Any] | None = None, source: str = "") -> Event:
        return Event(
            type=type,
            payload=payload or {},
            source=source or self.source,
            correlation_id=self.correlation_id or self.event_id,
            causation_id=self.event_id,
        )


@dataclass
class Subscription:
    pattern: str
    handler: Callable[[Event], Any]
    name: str = ""
    calls: int = 0
    errors: int = 0


class EventBus:
    """In-process event bus with wildcard routing and DLQ."""

    def __init__(self, replay_capacity: int = 512, dlq_capacity: int = 128) -> None:
        self._subs: list[Subscription] = []
        self._replay: deque[Event] = deque(maxlen=replay_capacity)
        self._dlq: deque[dict[str, Any]] = deque(maxlen=dlq_capacity)
        self._published = 0

    # -- subscription -------------------------------------------------
    def subscribe(self, pattern: str, handler: Callable[[Event], Any], name: str = "") -> Subscription:
        sub = Subscription(pattern=pattern, handler=handler, name=name or getattr(handler, "__name__", pattern))
        self._subs.append(sub)
        return sub

    def unsubscribe(self, sub: Subscription) -> None:
        self._subs = [s for s in self._subs if s is not sub]

    def matching(self, event_type: str) -> list[Subscription]:
        return [s for s in self._subs if fnmatch.fnmatchcase(event_type, s.pattern)]

    # -- publish ------------------------------------------------------
    def publish(self, event: Event) -> int:
        """Synchronous dispatch. Async handlers are scheduled as tasks."""
        self._published += 1
        self._replay.append(event)
        delivered = 0
        for sub in self.matching(event.type):
            try:
                res = sub.handler(event)
                if asyncio.iscoroutine(res):
                    try:
                        loop = asyncio.get_running_loop()
                    except RuntimeError:
                        asyncio.run(res)
                    else:
                        loop.create_task(res)
                sub.calls += 1
                delivered += 1
            except Exception as exc:  # noqa: BLE001
                sub.errors += 1
                self._dlq.append({"event": event, "handler": sub.name, "error": repr(exc), "ts": time.time()})
        return delivered

    async def apublish(self, event: Event) -> int:
        self._published += 1
        self._replay.append(event)
        delivered = 0
        for sub in self.matching(event.type):
            try:
                res = sub.handler(event)
                if asyncio.iscoroutine(res) or isinstance(res, Awaitable):
                    await res
                sub.calls += 1
                delivered += 1
            except Exception as exc:  # noqa: BLE001
                sub.errors += 1
                self._dlq.append({"event": event, "handler": sub.name, "error": repr(exc), "ts": time.time()})
        return delivered

    # -- introspection -------------------------------------------------
    def replay(self, pattern: str = "*", limit: int = 100) -> list[Event]:
        out = [e for e in self._replay if fnmatch.fnmatchcase(e.type, pattern)]
        return out[-limit:]

    @property
    def dead_letters(self) -> list[dict[str, Any]]:
        return list(self._dlq)

    def stats(self) -> dict[str, Any]:
        return {
            "subscriptions": len(self._subs),
            "published": self._published,
            "replay_buffered": len(self._replay),
            "dlq_depth": len(self._dlq),
            "handlers": [{"name": s.name, "pattern": s.pattern, "calls": s.calls, "errors": s.errors} for s in self._subs],
        }
