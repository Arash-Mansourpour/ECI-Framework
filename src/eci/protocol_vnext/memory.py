"""ECI-MEM — Living Memory + Dream/Consolidation.

Layers: Working · Episodic · Semantic · Procedural · Reflective
+ Salience Decay/Reinforcement + Dream Engine (replay→cluster→deduplicate→skill)
"""

from __future__ import annotations

import math
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any

__all__ = ["LivingMemory", "DreamEngine", "MemoryItem"]


@dataclass
class MemoryItem:
    content: Any
    kind: str  # working/episodic/semantic/procedural/reflective
    salience: float = 0.5
    created: float = field(default_factory=time.time)
    last_access: float = field(default_factory=time.time)
    accesses: int = 0
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    tombstoned: bool = False
    importance: float = 0.0  # EWC/Fisher-like importance (LFM Phase 23)

    def touch(self) -> None:
        self.last_access = time.time()
        self.accesses += 1
        # reinforcement: +0.1 capped at 1.0
        self.salience = min(1.0, self.salience + 0.1)
        self.importance = self.salience * (1.0 + 0.2 * self.accesses)

    def strength(self) -> float:
        """Memory strength S: salience amplified by rehearsal (Ebbinghaus)."""
        return max(0.1, self.salience * (1.0 + 0.2 * self.accesses) + 0.1 * self.importance)

    def retention(self, decay_rate: float = 0.001, now: float | None = None) -> float:
        """Ebbinghaus retention R = exp(-age / (S / decay_rate)) in (0, 1]."""
        age = (now if now is not None else time.time()) - self.last_access
        tau = self.strength() / max(1e-9, decay_rate)
        return math.exp(-max(0.0, age) / max(1.0, tau))

    def current_salience(self, decay_rate: float = 0.001) -> float:
        age = time.time() - self.last_access
        return self.salience * math.exp(-decay_rate * age) * (1 + 0.05 * self.accesses)


class LivingMemory:
    def __init__(self, decay_rate: float = 0.001) -> None:
        self.decay_rate = decay_rate
        self.layers: dict[str, deque[MemoryItem]] = {
            k: deque(maxlen=256) for k in ["working", "episodic", "semantic", "procedural", "reflective"]
        }
        # LFM Phase 23: tombstone archive — forgotten items are never deleted,
        # only moved here with provenance (mirrors semantic.py tombstones).
        self.archive: deque[MemoryItem] = deque(maxlen=1024)

    def store(self, content: Any, kind: str = "episodic", salience: float = 0.5) -> MemoryItem:
        item = MemoryItem(content=content, kind=kind, salience=salience)
        self.layers[kind].append(item)
        return item

    def recall(self, query: str = "", kind: str = "episodic", top_k: int = 5) -> list[MemoryItem]:
        pool = list(self.layers.get(kind, []))
        # salience-ranked + simple substring match bonus
        def score(it: MemoryItem) -> float:
            s = it.current_salience(self.decay_rate)
            if query and query.lower() in str(it.content).lower():
                s += 0.3
            return s
        ranked = sorted(pool, key=score, reverse=True)[:top_k]
        for it in ranked:
            it.touch()
        return ranked

    def forget(self, threshold: float = 0.05) -> int:
        # LFM Phase 23: Ebbinghaus retention gates forgetting; dropped items
        # go to archive as tombstones (auditable), never hard-deleted.
        removed = 0
        for kind, dq in self.layers.items():
            keep: deque[MemoryItem] = deque(maxlen=dq.maxlen)
            for it in dq:
                sal = it.current_salience(self.decay_rate)
                ret = it.retention(self.decay_rate)
                if sal > threshold and ret > threshold:
                    keep.append(it)
                else:
                    it.tombstoned = True
                    self.archive.append(it)
                    removed += 1
            self.layers[kind] = keep
        return removed

    def prune_ebbinghaus(self, retention_floor: float = 0.2) -> dict[str, Any]:
        """Explicit Ebbinghaus sweep: archive anything with R < floor."""
        archived = 0
        for kind, dq in self.layers.items():
            keep: deque[MemoryItem] = deque(maxlen=dq.maxlen)
            for it in dq:
                if it.retention(self.decay_rate) >= retention_floor:
                    keep.append(it)
                else:
                    it.tombstoned = True
                    self.archive.append(it)
                    archived += 1
            self.layers[kind] = keep
        return {"archived": archived, "archive_len": len(self.archive)}

    def stats(self) -> dict[str, Any]:
        d = {k: len(v) for k, v in self.layers.items()}
        d["archived"] = len(self.archive)
        return d


class DreamEngine:
    """Idle-time consolidation: replay → cluster → deduplicate → extract skills."""

    def consolidate(self, memory: LivingMemory) -> dict[str, Any]:
        episodic = list(memory.layers["episodic"])
        if not episodic:
            return {"consolidated": 0, "skills": []}
        # cluster by simple content hash prefix
        clusters: dict[str, list[MemoryItem]] = {}
        for it in episodic:
            key = str(it.content)[:16]
            clusters.setdefault(key, []).append(it)
        skills = []
        for key, items in clusters.items():
            if len(items) >= 2:
                # deduplicate: keep highest salience
                best = max(items, key=lambda x: x.salience)
                # LFM Phase 23: Fisher-like importance prices the skill
                # (rehearsal count x salience); stored back on the winner.
                importance = sum(it.salience * (1.0 + 0.2 * it.accesses) for it in items)
                best.importance = importance
                skill = {"pattern": key, "count": len(items), "exemplar": best.content,
                         "importance": importance}
                skills.append(skill)
                # promote to semantic
                memory.store(skill, kind="semantic", salience=0.7)
        return {"consolidated": len(episodic), "skills": skills, "clusters": len(clusters)}
