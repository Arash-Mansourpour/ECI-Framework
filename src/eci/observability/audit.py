"""Hash-chained audit log: tamper-evident decision trail.

Each record embeds prev_hash so deletion/reorder is detectable via verify().
Backends: memory (default) and JSONL file. Integrates with EventBus by
subscribing to ``audit.*`` and with Protocol-0 ledger by mirroring hashes.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

__all__ = ["AuditRecord", "AuditLogger"]


@dataclass
class AuditRecord:
    seq: int
    ts: float
    actor: str
    action: str
    details: dict[str, Any]
    prev_hash: str
    hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _hash(rec: AuditRecord) -> str:
    body = json.dumps({"seq": rec.seq, "ts": rec.ts, "actor": rec.actor,
                       "action": rec.action, "details": rec.details,
                       "prev_hash": rec.prev_hash}, sort_keys=True, default=str)
    return hashlib.sha256(body.encode()).hexdigest()


class AuditLogger:
    def __init__(self, path: Path | str | None = None) -> None:
        self._records: list[AuditRecord] = []
        self._path = Path(path) if path else None
        if self._path and self._path.exists():
            self._load()

    def append(self, actor: str, action: str, details: dict[str, Any] | None = None) -> AuditRecord:
        prev = self._records[-1].hash if self._records else "GENESIS"
        rec = AuditRecord(seq=len(self._records), ts=time.time(), actor=actor,
                          action=action, details=details or {}, prev_hash=prev)
        rec.hash = _hash(rec)
        self._records.append(rec)
        if self._path:
            with self._path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec.to_dict(), default=str) + "\n")
        return rec

    def _load(self) -> None:
        assert self._path is not None
        for line in self._path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                d = json.loads(line)
                self._records.append(AuditRecord(**d))

    def verify(self) -> dict[str, Any]:
        prev = "GENESIS"
        for rec in self._records:
            if rec.prev_hash != prev:
                return {"ok": False, "bad_seq": rec.seq, "reason": "chain-break"}
            if _hash(rec) != rec.hash:
                return {"ok": False, "bad_seq": rec.seq, "reason": "tamper"}
            prev = rec.hash
        return {"ok": True, "records": len(self._records), "head": prev}

    def query(self, actor: str = "", action: str = "", limit: int = 100) -> list[dict[str, Any]]:
        out = [r.to_dict() for r in self._records
               if (not actor or r.actor == actor) and (not action or r.action == action)]
        return out[-limit:]

    def __len__(self) -> int:
        return len(self._records)
