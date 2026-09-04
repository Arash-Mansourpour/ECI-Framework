"""Hash-chained audit ledger for obedience decisions (JSONL, append-only)."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

__all__ = ["Ledger"]


def _hash(entry: Dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(entry, sort_keys=True, default=str).encode()).hexdigest()


class Ledger:
    """Each record links prev_hash -> hash. Tampering breaks the chain."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else None
        self.records: List[Dict[str, Any]] = []
        if self.path and self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    self.records.append(json.loads(line))

    def append(self, kind: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        rec = {
            "seq": len(self.records),
            "t": time.time(),
            "kind": kind,
            "payload": payload,
            "prev": self.records[-1]["hash"] if self.records else "GENESIS",
        }
        rec["hash"] = _hash({k: v for k, v in rec.items() if k != "hash"})
        self.records.append(rec)
        if self.path:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, default=str) + "\n")
        return rec

    def verify(self) -> Dict[str, Any]:
        prev = "GENESIS"
        for i, rec in enumerate(self.records):
            if rec.get("prev") != prev:
                return {"ok": False, "at": i, "reason": "prev-link broken"}
            h = _hash({k: v for k, v in rec.items() if k != "hash"})
            if h != rec.get("hash"):
                return {"ok": False, "at": i, "reason": "hash mismatch"}
            prev = rec["hash"]
        return {"ok": True, "n": len(self.records)}

    # --- replication: snapshots + delta sync (minutes, not hours) ---
    def snapshot(self) -> Dict[str, Any]:
        """Signed-state shortcut: height + head hash + record count digest."""
        head = self.records[-1]["hash"] if self.records else "GENESIS"
        return {"height": len(self.records), "head": head,
                "verify": self.verify()["ok"]}

    def export_range(self, start: int, end: int | None = None) -> List[Dict[str, Any]]:
        """Delta slice for a lagging peer (inclusive start)."""
        return [dict(r) for r in self.records[start:end]]

    def sync_from(self, remote: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Adopt a longer VALID chain suffix; returns {adopted, height}."""
        if not remote:
            return {"adopted": 0, "height": len(self.records)}
        # Find common head: first remote record must link our chain or genesis.
        ours = {r["hash"]: i for i, r in enumerate(self.records)}
        start = 0
        if remote[0].get("prev") in ours:
            start = ours[remote[0]["prev"]] + 1
        elif remote[0].get("prev") != "GENESIS" and self.records:
            return {"adopted": 0, "height": len(self.records), "reason": "no common ancestor"}
        candidate = self.records[:start] + remote
        probe = Ledger()
        probe.records = [dict(r) for r in candidate]
        v = probe.verify()
        if not v["ok"] or len(candidate) < len(self.records):
            return {"adopted": 0, "height": len(self.records), "reason": v.get("reason", "not longer")}
        adopted = len(candidate) - len(self.records)
        self.records = candidate
        if self.path:
            with self.path.open("w", encoding="utf-8") as f:
                for r in self.records:
                    f.write(json.dumps(r, default=str) + "\n")
        return {"adopted": adopted, "height": len(self.records)}
