"""Atomic, cross-process operation result store for ECI task mesh."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any


class OperationStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.path), timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS operations ("
                "operation_id TEXT PRIMARY KEY, status TEXT NOT NULL, "
                "result TEXT, created_at REAL NOT NULL, updated_at REAL NOT NULL, "
                "fencing_token INTEGER)"
            )
            # Backward-compatible migration for older DBs.
            cols = {row[1] for row in conn.execute("PRAGMA table_info(operations)").fetchall()}
            if "fencing_token" not in cols:
                conn.execute("ALTER TABLE operations ADD COLUMN fencing_token INTEGER")
            conn.commit()

    def record_if_absent(self, operation_id: str, result: Any,
                         fencing_token: int | None = None) -> bool:
        """Atomically record a result. Returns True if this call created it.

        If a fencing_token is provided, a record with a higher token already
        present wins and this call returns False.
        """
        now = time.time()
        payload = json.dumps(result, default=str)
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            cur = conn.execute(
                "SELECT fencing_token FROM operations WHERE operation_id = ?",
                (operation_id,),
            )
            row = cur.fetchone()
            if row is not None:
                existing_token = row[0]
                if fencing_token is not None and existing_token is not None and fencing_token <= existing_token:
                    conn.commit()
                    return False
                # Allow update only if new token is higher.
                if fencing_token is not None and existing_token is not None and fencing_token > existing_token:
                    conn.execute(
                        "UPDATE operations SET status=?, result=?, updated_at=?, fencing_token=? "
                        "WHERE operation_id=?",
                        ("completed", payload, now, fencing_token, operation_id),
                    )
                    conn.commit()
                    return True
                conn.commit()
                return False
            conn.execute(
                "INSERT INTO operations(operation_id,status,result,created_at,updated_at,fencing_token) "
                "VALUES (?,?,?,?,?,?)",
                (operation_id, "completed", payload, now, now, fencing_token),
            )
            conn.commit()
            return True

    def get(self, operation_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT status,result,created_at,updated_at FROM operations WHERE operation_id = ?",
                (operation_id,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return {
            "operation_id": operation_id,
            "status": row[0],
            "result": json.loads(row[1]) if row[1] is not None else None,
            "created_at": row[2],
            "updated_at": row[3],
        }

    def count_effects(self, operation_id: str) -> int:
        # For file-based effect counters, callers track separately.
        return 1 if self.get(operation_id) is not None else 0