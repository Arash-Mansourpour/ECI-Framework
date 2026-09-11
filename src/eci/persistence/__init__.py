"""Persistence facade."""

from eci.persistence.event_store import EventStore, MemoryBackend, SqliteBackend, StoredEvent
from eci.persistence.repository import MemoryTable, Repository, UnitOfWork

__all__ = ["EventStore", "MemoryBackend", "SqliteBackend", "StoredEvent",
           "MemoryTable", "Repository", "UnitOfWork", "Persistence"]

from typing import Any


class Persistence:
    name = "persistence"

    def __init__(self, sqlite_path: Any | None = None) -> None:
        backend = SqliteBackend(sqlite_path) if sqlite_path else MemoryBackend()
        self.events = EventStore(backend)
        self.docs = Repository(kind="docs")

    def start(self) -> None: ...
    def stop(self) -> None: ...
    def health(self) -> dict[str, Any]:
        return {"ok": True, "events": len(self.events.backend), "docs": len(self.docs.table)}
