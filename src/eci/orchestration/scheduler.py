"""Priority scheduler + periodic jobs over asyncio.

Scheduler owns a heap of (run_at, priority, job); workers pull due jobs.
Periodic jobs re-arm themselves. All runs emit kernel bus events when a
bus is attached (``workflow.job.*``), feeding observability + provenance.
"""

from __future__ import annotations

import asyncio
import heapq
import itertools
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

__all__ = ["Job", "Scheduler"]


@dataclass(order=True)
class _Item:
    run_at: float
    neg_priority: int
    seq: int
    job_id: str = field(compare=False)


@dataclass
class Job:
    id: str
    fn: Callable[..., Any]
    args: tuple = ()
    kwargs: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    period_s: float = 0.0  # >0 => periodic
    runs: int = 0
    last_error: str = ""


class Scheduler:
    name = "scheduler"

    def __init__(self, bus: Any | None = None) -> None:
        self._heap: List[_Item] = []
        self._jobs: Dict[str, Job] = {}
        self._seq = itertools.count()
        self.bus = bus
        self.completed = 0
        self.failed = 0

    def submit(self, job_id: str, fn: Callable[..., Any], *args: Any,
               priority: int = 0, delay_s: float = 0.0, period_s: float = 0.0,
               **kwargs: Any) -> Job:
        job = Job(id=job_id, fn=fn, args=args, kwargs=kwargs,
                  priority=priority, period_s=period_s)
        self._jobs[job_id] = job
        heapq.heappush(self._heap, _Item(time.time() + delay_s, -priority, next(self._seq), job_id))
        return job

    def every(self, job_id: str, period_s: float, fn: Callable[..., Any], *args: Any,
              priority: int = 0, **kwargs: Any) -> Job:
        return self.submit(job_id, fn, *args, priority=priority, period_s=period_s, **kwargs)

    def pending(self) -> int:
        return len(self._heap)

    async def run_due(self, limit: int = 32) -> Dict[str, Any]:
        now = time.time()
        ran: List[str] = []
        errs: Dict[str, str] = {}
        n = 0
        while self._heap and self._heap[0].run_at <= now and n < limit:
            item = heapq.heappop(self._heap)
            job = self._jobs.get(item.job_id)
            if job is None:
                continue
            n += 1
            try:
                res = job.fn(*job.args, **job.kwargs)
                if asyncio.iscoroutine(res):
                    await res
                job.runs += 1
                self.completed += 1
                ran.append(job.id)
                if self.bus is not None:
                    from eci.kernel.bus import Event
                    self.bus.publish(Event(type="workflow.job.done", source="scheduler",
                                           payload={"job": job.id, "runs": job.runs}))
            except Exception as exc:  # noqa: BLE001
                job.last_error = repr(exc)
                self.failed += 1
                errs[job.id] = repr(exc)
            finally:
                if job.period_s > 0:
                    heapq.heappush(self._heap, _Item(now + job.period_s, item.neg_priority,
                                                    next(self._seq), job.id))
        return {"ran": ran, "errors": errs, "pending": len(self._heap)}

    def start(self) -> None: ...
    def stop(self) -> None: ...
    def health(self) -> Dict[str, Any]:
        return {"ok": True, "pending": len(self._heap), "completed": self.completed, "failed": self.failed}
