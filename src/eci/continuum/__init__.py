"""Temporal continuity: snapshots, autobiography, verifiable replay.

AGI must survive restarts without losing itself. Continuum chains
snapshots {epoch, digests, prev_hash, hash} over subsystem state digests,
keeps a chained autobiographical record (epoch summaries — the narrative
self), and replays EventStore ranges to verify determinism: refold and
compare digests. A mismatch is *evidence*, reported exactly, never hidden.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import Any

__all__ = ["Snapshot", "Continuum"]


def _digest(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


@dataclass
class Snapshot:
    epoch: int
    digests: dict[str, str]
    prev: str
    ts: float = field(default_factory=time.time)
    hash: str = ""

    def seal(self) -> Snapshot:
        self.hash = _digest({"e": self.epoch, "d": self.digests, "p": self.prev, "t": self.ts})
        return self

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class Continuum:
    name = "continuum"

    def __init__(self) -> None:
        self.epoch = 0
        self._chain: list[Snapshot] = []
        self._story: list[dict[str, Any]] = []  # autobiography
        self.restores = 0

    def snapshot(self, states: dict[str, Any], note: str = "") -> Snapshot:
        digests = {k: _digest(v) for k, v in states.items()}
        snap = Snapshot(self.epoch, digests, self._chain[-1].hash if self._chain else "GENESIS").seal()
        self._chain.append(snap)
        self._story.append({"epoch": self.epoch, "note": note,
                            "digests": len(digests), "hash": snap.hash[:12], "ts": snap.ts})
        self.epoch += 1
        return snap

    def verify_chain(self) -> dict[str, Any]:
        prev = "GENESIS"
        for s in self._chain:
            if s.prev != prev:
                return {"ok": False, "error": "chain break", "epoch": s.epoch}
            probe = Snapshot(s.epoch, s.digests, s.prev, s.ts)
            probe.hash = s.hash
            check = Snapshot(s.epoch, s.digests, s.prev, s.ts).seal()
            if check.hash != s.hash:
                return {"ok": False, "error": "tamper", "epoch": s.epoch}
            prev = s.hash
        return {"ok": True, "snapshots": len(self._chain), "head": prev[:12] if prev != "GENESIS" else None}

    def autobiography(self, limit: int = 20) -> list[dict[str, Any]]:
        return self._story[-limit:]

    def replay_check(self, events: list[Any], reducer: Callable[[Any, Any], Any],
                     initial: Any, expect_digest: str) -> dict[str, Any]:
        """Refold events; compare digest. Determinism, checked."""
        state = initial
        for ev in events:
            state = reducer(state, ev)
        got = _digest(state)
        return {"ok": got == expect_digest, "digest": got[:12],
                "expected": expect_digest[:12], "events": len(events)}

    def start(self) -> None: ...
    def stop(self) -> None: ...
    def health(self) -> dict[str, Any]:
        return {"ok": True, "epoch": self.epoch, **self.verify_chain()}
