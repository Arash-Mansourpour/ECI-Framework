"""Agent memory: episodic ring + in-memory vector recall (cosine top-k).

Episodic memory is a bounded deque of {role, content, ts}. Vector memory
stores (text, vector) pairs and recalls by cosine similarity — embeddings
are supplied by the caller (QNN / torch / external) so this stays
stdlib+torch-free and edge-safe. Both emit provenance-friendly records.
"""

from __future__ import annotations

import math
import time
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

__all__ = ["EpisodicMemory", "VectorMemory"]


@dataclass
class _Msg:
    role: str
    content: str
    ts: float = field(default_factory=time.time)


class EpisodicMemory:
    def __init__(self, capacity: int = 256) -> None:
        self._buf: deque[_Msg] = deque(maxlen=capacity)

    def add(self, role: str, content: str) -> None:
        self._buf.append(_Msg(role, content))

    def last(self, n: int = 8) -> list[dict[str, Any]]:
        return [{"role": m.role, "content": m.content, "ts": m.ts} for m in list(self._buf)[-n:]]

    def search(self, keyword: str, limit: int = 8) -> list[dict[str, Any]]:
        kw = keyword.lower()
        out = [ {"role": m.role, "content": m.content, "ts": m.ts}
                for m in self._buf if kw in m.content.lower()]
        return out[-limit:]

    def __len__(self) -> int:
        return len(self._buf)


def _cos(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1e-9
    nb = math.sqrt(sum(y * y for y in b)) or 1e-9
    return dot / (na * nb)


class VectorMemory:
    def __init__(self, capacity: int = 2048) -> None:
        self._items: deque[dict[str, Any]] = deque(maxlen=capacity)

    def store(self, text: str, vector: Sequence[float], meta: dict[str, Any] | None = None) -> None:
        self._items.append({"text": text, "vector": list(vector), "meta": meta or {}, "ts": time.time()})

    def recall(self, query: Sequence[float], top_k: int = 3) -> list[dict[str, Any]]:
        scored = [ (float(_cos(query, it["vector"])), it) for it in self._items]
        scored.sort(key=lambda t: t[0], reverse=True)
        return [{"score": s, "text": it["text"], "meta": it["meta"]} for s, it in scored[:top_k]]

    def __len__(self) -> int:
        return len(self._items)
