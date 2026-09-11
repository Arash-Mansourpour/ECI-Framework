"""Generic repository + unit-of-work over an in-memory document table.

Keeps domain code storage-agnostic: swap MemoryTable for a SQL adapter
without touching callers. UoW batches mutations with commit/rollback.
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any, TypeVar

__all__ = ["MemoryTable", "Repository", "UnitOfWork"]

T = TypeVar("T")


class MemoryTable:
    def __init__(self) -> None:
        self._rows: dict[str, dict[str, Any]] = {}

    def get(self, key: str) -> dict[str, Any] | None:
        v = self._rows.get(key)
        return copy.deepcopy(v) if v is not None else None

    def put(self, key: str, value: dict[str, Any]) -> None:
        self._rows[key] = copy.deepcopy(value)

    def delete(self, key: str) -> None:
        self._rows.pop(key, None)

    def scan(self, predicate: Callable[[dict[str, Any]], bool] | None = None) -> list[dict[str, Any]]:
        vals = [copy.deepcopy(v) for v in self._rows.values()]
        return [v for v in vals if predicate is None or predicate(v)]

    def __len__(self) -> int:
        return len(self._rows)


class Repository:
    """Thin CRUD facade with optimistic-concurrency via version field."""

    def __init__(self, table: MemoryTable | None = None, kind: str = "doc") -> None:
        self.table = table or MemoryTable()
        self.kind = kind

    def save(self, key: str, doc: dict[str, Any]) -> dict[str, Any]:
        cur = self.table.get(key)
        nxt = dict(doc)
        nxt["_id"] = key
        nxt["_v"] = int(cur.get("_v", 0)) + 1 if cur else 1
        self.table.put(key, nxt)
        return nxt

    def get(self, key: str) -> dict[str, Any] | None:
        return self.table.get(key)

    def delete(self, key: str) -> None:
        self.table.delete(key)

    def find(self, predicate: Callable[[dict[str, Any]], bool] | None = None) -> list[dict[str, Any]]:
        return self.table.scan(predicate)


class UnitOfWork:
    """Batch mutations atomically against a Repository."""

    def __init__(self, repo: Repository) -> None:
        self.repo = repo
        self._ops: list[tuple] = []
        self._snapshot: dict[str, Any] = {}

    def __enter__(self) -> UnitOfWork:
        self._snapshot = {k: v for k, v in self.repo.table._rows.items()}
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc_type is not None:
            self.rollback()
            return False
        self.commit()
        return False

    def save(self, key: str, doc: dict[str, Any]) -> None:
        self._ops.append(("save", key, doc))

    def delete(self, key: str) -> None:
        self._ops.append(("delete", key, None))

    def commit(self) -> None:
        for op, key, doc in self._ops:
            if op == "save":
                self.repo.save(key, doc)
            else:
                self.repo.delete(key)
        self._ops.clear()
        self._snapshot = {}

    def rollback(self) -> None:
        self.repo.table._rows = dict(self._snapshot)
        self._ops.clear()
        self._snapshot = {}
