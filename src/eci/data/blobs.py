"""Content-addressed blob store (sha256) for snapshots, EEG, artifacts."""

from __future__ import annotations

import hashlib
import time
from typing import Any, Dict, Optional

__all__ = ["BlobStore"]


class BlobStore:
    def __init__(self) -> None:
        self._blobs: Dict[str, Dict[str, Any]] = {}

    def put(self, data: bytes, meta: Dict[str, Any] | None = None) -> str:
        digest = hashlib.sha256(data).hexdigest()
        if digest not in self._blobs:
            self._blobs[digest] = {"data": data, "meta": meta or {}, "ts": time.time(), "size": len(data)}
        return digest

    def get(self, digest: str) -> Optional[bytes]:
        rec = self._blobs.get(digest)
        return rec["data"] if rec else None

    def info(self, digest: str) -> Optional[Dict[str, Any]]:
        rec = self._blobs.get(digest)
        if not rec:
            return None
        return {"digest": digest, "size": rec["size"], "meta": rec["meta"], "ts": rec["ts"]}

    def __len__(self) -> int:
        return len(self._blobs)
