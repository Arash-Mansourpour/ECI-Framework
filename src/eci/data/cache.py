"""LRU+TTL cache: L1 hot path for ledger reads, QEC tables, policy lookups."""

from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

__all__ = ["Cache"]


class Cache:
    def __init__(self, capacity: int = 1024, ttl_s: float = 60.0) -> None:
        self.capacity = capacity
        self.ttl = ttl_s
        self._data: OrderedDict[str, Tuple[Any, float]] = OrderedDict()
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def get(self, key: str) -> Optional[Any]:
        rec = self._data.get(key)
        if rec is None:
            self.misses += 1
            return None
        val, exp = rec
        if time.time() > exp:
            self._data.pop(key, None)
            self.misses += 1
            return None
        self._data.move_to_end(key)
        self.hits += 1
        return val

    def put(self, key: str, value: Any, ttl_s: float | None = None) -> None:
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = (value, time.time() + (ttl_s if ttl_s is not None else self.ttl))
        while len(self._data) > self.capacity:
            self._data.popitem(last=False)
            self.evictions += 1

    def stats(self) -> Dict[str, Any]:
        total = self.hits + self.misses
        return {"size": len(self._data), "hits": self.hits, "misses": self.misses,
                "evictions": self.evictions, "hit_rate": (self.hits / total) if total else 0.0}
