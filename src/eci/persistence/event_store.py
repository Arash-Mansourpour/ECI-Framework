"""Append-only event store with pluggable backends (memory/sqlite).

Event-sourcing primitive: every state change is an event; state is a
left-fold over events. SQLite backend is stdlib (sqlite3), safe for
edge/server profiles. Used by ledger mirroring, provenance, twin replay.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

__all__ = ["StoredEvent", "MemoryBackend", "SqliteBackend", "EventStore"]


@dataclass
class StoredEvent:
    seq: int
    stream: str
    type: str
    data: dict[str, Any]
    ts: float = field(default_factory=time.time)
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MemoryBackend:
    def __init__(self) -> None:
        self._events: list[StoredEvent] = []

    def append(self, ev: StoredEvent) -> None:
        self._events.append(ev)

    def read(self, stream: str = "", after: int = -1, limit: int = 1000) -> list[StoredEvent]:
        out = [e for e in self._events if (not stream or e.stream == stream) and e.seq > after]
        return out[:limit]

    def __len__(self) -> int:
        return len(self._events)


class SqliteBackend:
    def __init__(self, path: Path | str = ":memory:") -> None:
        self.path = str(path)
        self._db = sqlite3.connect(self.path, check_same_thread=False)
        self._db.execute("CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT, stream TEXT, type TEXT, data TEXT, ts REAL, event_id TEXT)")
        self._db.commit()

    def append(self, ev: StoredEvent) -> None:
        self._db.execute("INSERT INTO events(stream,type,data,ts,event_id) VALUES(?,?,?,?,?)",
                         (ev.stream, ev.type, json.dumps(ev.data, default=str), ev.ts, ev.event_id))
        self._db.commit()

    def read(self, stream: str = "", after: int = -1, limit: int = 1000) -> list[StoredEvent]:
        q = "SELECT seq,stream,type,data,ts,event_id FROM events WHERE seq>? "
        args: list[Any] = [after]
        if stream:
            q += "AND stream=? "
            args.append(stream)
        q += "ORDER BY seq LIMIT ?"
        args.append(limit)
        rows = self._db.execute(q, args).fetchall()
        return [StoredEvent(seq=r[0], stream=r[1], type=r[2], data=json.loads(r[3]), ts=r[4], event_id=r[5]) for r in rows]

    def __len__(self) -> int:
        return int(self._db.execute("SELECT COUNT(*) FROM events").fetchone()[0])


class EventStore:
    """Facade over a backend with stream-position tracking."""

    name = "event-store"

    def __init__(self, backend: Any | None = None) -> None:
        self.backend = backend or MemoryBackend()
        self._seq = len(self.backend)  # type: ignore[arg-type]

    def append(self, stream: str, type: str, data: dict[str, Any] | None = None) -> StoredEvent:
        # sqlite backend assigns seq itself; keep local counter for memory parity
        existing = len(self.backend)
        ev = StoredEvent(seq=existing, stream=stream, type=type, data=data or {})
        self.backend.append(ev)
        return ev

    def read(self, stream: str = "", after: int = -1, limit: int = 1000) -> list[StoredEvent]:
        return self.backend.read(stream, after, limit)

    def fold(self, stream: str, reducer, initial: Any) -> Any:
        state = initial
        for ev in self.read(stream, limit=100_000):
            state = reducer(state, ev)
        return state

    def start(self) -> None: ...
    def stop(self) -> None: ...
    def health(self) -> dict[str, Any]:
        return {"ok": True, "events": len(self.backend)}
