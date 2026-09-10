"""Distributed tracing (OTel-flavoured, stdlib-only).

Spans form a tree via parent_id; Tracer keeps a bounded ring so
long-running meshes don't leak memory. Export as JSON or OTLP-ish dicts.
"""

from __future__ import annotations

import time
import uuid
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, Iterator, List, Optional

__all__ = ["Span", "Tracer"]


@dataclass
class Span:
    trace_id: str
    span_id: str
    name: str
    parent_id: str = ""
    start: float = field(default_factory=time.time)
    end: float = 0.0
    attrs: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "ok"

    @property
    def duration_s(self) -> float:
        return (self.end or time.time()) - self.start

    def event(self, name: str, attrs: Dict[str, Any] | None = None) -> None:
        self.events.append({"name": name, "ts": time.time(), "attrs": attrs or {}})

    def to_dict(self) -> Dict[str, Any]:
        return {"trace_id": self.trace_id, "span_id": self.span_id, "parent_id": self.parent_id,
                "name": self.name, "start": self.start, "end": self.end,
                "duration_s": self.duration_s, "attrs": self.attrs,
                "events": self.events, "status": self.status}


class Tracer:
    def __init__(self, service: str = "eci", capacity: int = 2048) -> None:
        self.service = service
        self._spans: Deque[Span] = deque(maxlen=capacity)
        self._active: List[Span] = []

    @contextmanager
    def span(self, name: str, attrs: Dict[str, Any] | None = None,
             parent: Span | None = None) -> Iterator[Span]:
        parent = parent or (self._active[-1] if self._active else None)
        sp = Span(trace_id=parent.trace_id if parent else uuid.uuid4().hex[:16],
                  span_id=uuid.uuid4().hex[:8], name=name,
                  parent_id=parent.span_id if parent else "",
                  attrs=dict(attrs or {}))
        self._active.append(sp)
        try:
            yield sp
        except Exception as exc:  # noqa: BLE001
            sp.status = f"error: {exc}"
            raise
        finally:
            sp.end = time.time()
            self._active.pop()
            self._spans.append(sp)

    def spans(self, name: str = "", limit: int = 200) -> List[Span]:
        out = [s for s in self._spans if not name or s.name == name]
        return out[-limit:]

    def trace(self, trace_id: str) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self._spans if s.trace_id == trace_id]

    def stats(self) -> Dict[str, Any]:
        durs = [s.duration_s for s in self._spans]
        return {"service": self.service, "spans": len(self._spans),
                "active": len(self._active),
                "p50_s": sorted(durs)[len(durs) // 2] if durs else 0.0,
                "max_s": max(durs) if durs else 0.0}
