"""In-process API gateway: versioned routes, auth hook, OpenAPI-ish schema.

The gateway is transport-agnostic: the same routes serve CLI, MCP, HTTP
and tests. Handlers are plain callables ``fn(params, ctx)``; the gateway
adds auth (via PolicyEngine), rate limiting, tracing spans and audit.
"""

from __future__ import annotations

import fnmatch
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

__all__ = ["Route", "Gateway"]


@dataclass
class Route:
    path: str          # e.g. "v1/ledger.append"
    handler: Callable[..., Any]
    auth_action: str = ""
    summary: str = ""


class Gateway:
    name = "api-gateway"

    def __init__(self, authz: Any | None = None, limiter: Any | None = None,
                 tracer: Any | None = None, audit: Any | None = None) -> None:
        self._routes: Dict[str, Route] = {}
        self.authz = authz
        self.limiter = limiter
        self.tracer = tracer
        self.audit = audit
        self.calls = 0
        self.denied = 0

    def route(self, path: str, auth_action: str = "", summary: str = ""):
        def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
            self._routes[path] = Route(path, fn, auth_action, summary or fn.__name__)
            return fn
        return deco

    def add(self, path: str, handler: Callable[..., Any], auth_action: str = "", summary: str = "") -> None:
        self._routes[path] = Route(path, handler, auth_action, summary or path)

    def paths(self) -> List[str]:
        return sorted(self._routes)

    def schema(self) -> Dict[str, Any]:
        return {"version": "v1", "routes": [
            {"path": r.path, "auth": r.auth_action, "summary": r.summary} for r in self._routes.values()]}

    def call(self, path: str, params: Dict[str, Any] | None = None,
             ctx: Dict[str, Any] | None = None) -> Dict[str, Any]:
        params, ctx = params or {}, ctx or {}
        if path not in self._routes:
            return {"ok": False, "error": f"unknown route {path}"}
        route = self._routes[path]
        self.calls += 1
        # rate limit
        if self.limiter is not None:
            try:
                self.limiter.require()
            except Exception as exc:  # noqa: BLE001
                self.denied += 1
                return {"ok": False, "error": f"rate-limited: {exc}"}
        # auth
        if route.auth_action and self.authz is not None:
            dec = self.authz.decide(ctx.get("subject", "anon"), route.auth_action, path,
                                    attrs=ctx.get("attrs"), attestation=ctx.get("attestation"))
            if not dec.allow:
                self.denied += 1
                return {"ok": False, "error": "denied", "reasons": dec.reasons}
        # invoke with tracing
        try:
            if self.tracer is not None:
                with self.tracer.span(f"api.{path}", {"subject": ctx.get("subject", "")}):
                    out = route.handler(params, ctx)
            else:
                out = route.handler(params, ctx)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": repr(exc)}
        if self.audit is not None:
            try:
                self.audit.append(str(ctx.get("subject", "anon")), f"api.{path}", {"params_keys": sorted(params)})
            except Exception:  # noqa: BLE001
                pass
        return {"ok": True, "data": out}

    def start(self) -> None: ...
    def stop(self) -> None: ...
    def health(self) -> Dict[str, Any]:
        return {"ok": True, "routes": len(self._routes), "calls": self.calls, "denied": self.denied}
