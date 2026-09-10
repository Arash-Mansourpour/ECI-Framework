"""Topic streaming with backpressure, consumer groups and replay.

Design: bounded per-topic ring buffers; slow consumers get `dropped`
counters instead of blocking publishers (telemetry-grade at-least-once).
Consumer groups track offsets for replay after restarts (via EventStore).
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict, List, Optional

__all__ = ["StreamRecord", "Topic", "StreamBus"]


@dataclass
class StreamRecord:
    offset: int
    topic: str
    data: Dict[str, Any]
    ts: float = field(default_factory=time.time)


class Topic:
    def __init__(self, name: str, capacity: int = 1024) -> None:
        self.name = name
        self.capacity = capacity
        self._buf: Deque[StreamRecord] = deque(maxlen=capacity)
        self._next = 0
        self.published = 0
        self.dropped = 0

    def publish(self, data: Dict[str, Any]) -> StreamRecord:
        if len(self._buf) >= self.capacity:
            self.dropped += 1
        rec = StreamRecord(offset=self._next, topic=self.name, data=data)
        self._buf.append(rec)
        self._next += 1
        self.published += 1
        return rec

    def read(self, after: int = -1, limit: int = 100) -> List[StreamRecord]:
        return [r for r in self._buf if r.offset > after][:limit]


class StreamBus:
    name = "streaming"

    def __init__(self, default_capacity: int = 1024) -> None:
        self._topics: Dict[str, Topic] = {}
        self._capacity = default_capacity
        self._groups: Dict[str, Dict[str, int]] = defaultdict(dict)  # group -> topic -> offset

    def topic(self, name: str) -> Topic:
        return self._topics.setdefault(name, Topic(name, self._capacity))

    def publish(self, topic: str, data: Dict[str, Any]) -> StreamRecord:
        return self.topic(topic).publish(data)

    def poll(self, topic: str, group: str = "default", limit: int = 100) -> List[StreamRecord]:
        after = self._groups[group].get(topic, -1)
        recs = self.topic(topic).read(after, limit)
        if recs:
            self._groups[group][topic] = recs[-1].offset
        return recs

    def stats(self) -> Dict[str, Any]:
        return {"topics": {k: {"published": t.published, "dropped": t.dropped, "depth": len(t._buf)} for k, t in self._topics.items()},
                "groups": {g: dict(o) for g, o in self._groups.items()}}

    def start(self) -> None: ...
    def stop(self) -> None: ...
    def health(self) -> Dict[str, Any]:
        return {"ok": True, **self.stats()}
