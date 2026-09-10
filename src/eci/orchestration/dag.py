"""DAG workflow engine: topological levels, parallel fan-out, retry/timeout.

Nodes are pure callables ``fn(ctx) -> value|awaitable``; edges declare
dependencies. Execution is level-by-level with asyncio.gather inside a
level, so independent branches run concurrently while dependents wait.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

__all__ = ["TaskNode", "DAG", "WorkflowRun"]


@dataclass
class TaskNode:
    name: str
    fn: Callable[..., Any]
    depends_on: List[str] = field(default_factory=list)
    timeout_s: float = 30.0
    retries: int = 0


@dataclass
class WorkflowRun:
    ok: bool
    outputs: Dict[str, Any]
    errors: Dict[str, str]
    duration_s: float


class DAG:
    def __init__(self, name: str = "dag") -> None:
        self.name = name
        self.nodes: Dict[str, TaskNode] = {}

    def task(self, name: str, depends_on: List[str] | None = None,
             timeout_s: float = 30.0, retries: int = 0):
        def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
            self.nodes[name] = TaskNode(name, fn, list(depends_on or []), timeout_s, retries)
            return fn
        return deco

    def add(self, name: str, fn: Callable[..., Any], depends_on: List[str] | None = None,
            timeout_s: float = 30.0, retries: int = 0) -> None:
        self.nodes[name] = TaskNode(name, fn, list(depends_on or []), timeout_s, retries)

    def levels(self) -> List[List[str]]:
        indeg = {n: len(nd.depends_on) for n, nd in self.nodes.items()}
        for n, nd in self.nodes.items():
            for d in nd.depends_on:
                if d not in self.nodes:
                    raise KeyError(f"task {n} depends on unknown {d}")
        levels: List[List[str]] = []
        remaining = dict(indeg)
        while remaining:
            ready = sorted([n for n, d in remaining.items() if d == 0])
            if not ready:
                raise ValueError(f"cycle in DAG {self.name}: {sorted(remaining)}")
            levels.append(ready)
            for n in ready:
                del remaining[n]
            for n in remaining:
                remaining[n] -= sum(1 for d in self.nodes[n].depends_on if d in ready)
        return levels

    async def _run_one(self, node: TaskNode, ctx: Dict[str, Any]) -> Any:
        last: BaseException | None = None
        for attempt in range(node.retries + 1):
            try:
                res = node.fn(ctx)
                if asyncio.iscoroutine(res):
                    res = await asyncio.wait_for(res, timeout=node.timeout_s)
                return res
            except Exception as exc:  # noqa: BLE001
                last = exc
        assert last is not None
        raise last

    async def run(self, ctx: Dict[str, Any] | None = None) -> WorkflowRun:
        t0 = time.time()
        ctx = dict(ctx or {})
        outputs: Dict[str, Any] = {}
        errors: Dict[str, str] = {}
        for level in self.levels():
            # skip tasks whose deps failed
            runnable = [n for n in level if all(d not in errors for d in self.nodes[n].depends_on)]
            results = await asyncio.gather(*[self._run_one(self.nodes[n], {**ctx, **outputs}) for n in runnable],
                                           return_exceptions=True)
            for n, r in zip(runnable, results):
                if isinstance(r, BaseException):
                    errors[n] = repr(r)
                else:
                    outputs[n] = r
            for n in level:
                if n not in runnable and n not in errors:
                    errors[n] = "skipped: dependency failed"
        return WorkflowRun(ok=not errors, outputs=outputs, errors=errors, duration_s=time.time() - t0)
