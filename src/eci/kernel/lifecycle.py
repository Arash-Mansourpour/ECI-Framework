"""Service lifecycle manager: ordered start/stop with dependency DAG."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol

__all__ = ["Service", "ServiceState", "LifecycleManager"]


class ServiceState:
    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


class Service(Protocol):
    name: str
    def start(self) -> Any: ...
    def stop(self) -> Any: ...
    def health(self) -> Dict[str, Any]: ...


@dataclass
class _Entry:
    name: str
    svc: Any
    depends_on: List[str] = field(default_factory=list)
    state: str = ServiceState.CREATED
    started_at: float = 0.0
    error: str = ""


class LifecycleManager:
    """Topological start (deps first), reverse stop, aggregated health."""

    def __init__(self) -> None:
        self._services: Dict[str, _Entry] = {}

    def register(self, svc: Any, depends_on: List[str] | None = None) -> None:
        name = getattr(svc, "name", svc.__class__.__name__)
        self._services[name] = _Entry(name=name, svc=svc, depends_on=list(depends_on or []))

    def order(self) -> List[str]:
        visited: Dict[str, str] = {}
        out: List[str] = []

        def visit(n: str, stack: List[str]) -> None:
            if n not in self._services:
                raise KeyError(f"unknown service dependency {n!r}")
            mark = visited.get(n)
            if mark == "done":
                return
            if mark == "wip":
                raise ValueError(f"dependency cycle: {' -> '.join(stack + [n])}")
            visited[n] = "wip"
            for dep in self._services[n].depends_on:
                visit(dep, stack + [n])
            visited[n] = "done"
            out.append(n)

        for name in self._services:
            visit(name, [])
        return out

    async def start_all(self) -> Dict[str, str]:
        results: Dict[str, str] = {}
        for name in self.order():
            e = self._services[name]
            e.state = ServiceState.STARTING
            try:
                fn = getattr(e.svc, "start", None)
                res = fn() if callable(fn) else None
                if asyncio.iscoroutine(res):
                    await res
                e.state = ServiceState.RUNNING
                e.started_at = time.time()
                results[name] = "running"
            except Exception as exc:  # noqa: BLE001
                e.state = ServiceState.FAILED
                e.error = repr(exc)
                results[name] = f"failed: {exc}"
        return results

    async def stop_all(self) -> Dict[str, str]:
        results: Dict[str, str] = {}
        for name in reversed(self.order()):
            e = self._services[name]
            e.state = ServiceState.STOPPING
            try:
                fn = getattr(e.svc, "stop", None)
                res = fn() if callable(fn) else None
                if asyncio.iscoroutine(res):
                    await res
                e.state = ServiceState.STOPPED
                results[name] = "stopped"
            except Exception as exc:  # noqa: BLE001
                e.state = ServiceState.FAILED
                e.error = repr(exc)
                results[name] = f"failed: {exc}"
        return results

    def health(self) -> Dict[str, Any]:
        per: Dict[str, Any] = {}
        ok = True
        for name, e in self._services.items():
            try:
                h = e.svc.health() if hasattr(e.svc, "health") else {"state": e.state}
            except Exception as exc:  # noqa: BLE001
                h = {"ok": False, "error": repr(exc)}
            h = {"state": e.state, **h}
            per[name] = h
            if e.state == ServiceState.FAILED or h.get("ok") is False:
                ok = False
        return {"ok": ok, "services": per}
