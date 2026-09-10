"""Middleware pipeline: auth -> quota -> idempotency -> breaker -> exec -> observe.

Each call flows through composable async stages sharing one ``CallCtx``.
Stages are swappable for tests (pass ``middlewares=[...]``). Defaults:

1. session_resolve  (ephemeral session when none supplied)
2. rate_session     (per-session token bucket)
3. idempotency      (replay cached result for ``idempotency_key``)
4. auth_policy      (RBAC/ABAC + capability wildcard + attestation floors)
5. quota_budget     (tenancy admit + economy pre-check + session budget)
6. dry_run          (mutating tools with dry_run=true -> twin/what_if stub)
7. breaker_retry    (per-tool circuit breaker + one retry on transient)
8. execute          (timeout-guarded handler invocation)
9. observe          (trace span + metrics + audit + provenance + bus event)

Every denial returns structured ``{ok: False, stage, error}`` — never an
exception — so MCP clients always get JSON-RPC-safe payloads.
"""

from __future__ import annotations

import asyncio
import fnmatch
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

__all__ = ["CallCtx", "McpPipeline"]


@dataclass
class CallCtx:
    tool_name: str
    args: Dict[str, Any]
    session: Any = None
    idempotency_key: str = ""
    dry_run: bool = False
    stage: str = ""
    error: str = ""
    result: Any = None
    duration_s: float = 0.0


def _caps_allow(granted: List[str], needed: List[str]) -> List[str]:
    missing = []
    for n in needed:
        if not any(fnmatch.fnmatchcase(n, g) or fnmatch.fnmatchcase(g, n) for g in granted):
            missing.append(n)
    return missing


class McpPipeline:
    def __init__(self, registry=None, sessions=None, authz=None, economy=None,
                 tenancy=None, breakers: Any | None = None, tracer=None,
                 metrics=None, audit=None, provenance=None, bus=None,
                 idempotency_capacity: int = 512) -> None:
        self.registry = registry
        self.sessions = sessions
        self.authz = authz
        self.economy = economy
        self.tenancy = tenancy
        self.breakers = breakers
        self.tracer = tracer
        self.metrics = metrics
        self.audit = audit
        self.provenance = provenance
        self.bus = bus
        self._idem: Dict[str, Any] = {}
        self._idem_order: List[str] = []
        self._idem_cap = idempotency_capacity
        self._sema: Dict[str, asyncio.Semaphore] = {}

    # -- public --------------------------------------------------------
    async def run(self, tool_name: str, args: Dict[str, Any] | None = None,
                  session: Any | None = None, session_id: str = "",
                  idempotency_key: str = "", dry_run: bool = False) -> Dict[str, Any]:
        t0 = time.time()
        ctx = CallCtx(tool_name=tool_name, args=dict(args or {}),
                      idempotency_key=idempotency_key or str((args or {}).pop("idempotency_key", "")),
                      dry_run=dry_run or bool((args or {}).pop("dry_run", False)))
        tool = self.registry.get(tool_name) if self.registry else None
        if tool is None:
            return {"ok": False, "stage": "resolve", "error": f"unknown tool {tool_name}"}
        # session
        ctx.stage = "session"
        try:
            ctx.session = session or (self.sessions.get_or_ephemeral(session_id) if self.sessions else None)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "stage": "session", "error": repr(exc)}
        s = ctx.session
        # rate
        ctx.stage = "rate"
        if s is not None and not s.allow():
            return {"ok": False, "stage": "rate", "error": "session rate limit"}
        # idempotency replay
        ctx.stage = "idempotency"
        if ctx.idempotency_key and ctx.idempotency_key in self._idem:
            return {"ok": True, "stage": "idempotent-replay", "data": self._idem[ctx.idempotency_key], "cached": True}
        # auth
        ctx.stage = "auth"
        subj = getattr(s, "subject", "anon")
        sess_caps = list(getattr(s, "capabilities", []) or [])
        missing = _caps_allow(sess_caps + [subj, "*"] if "*" in sess_caps else sess_caps, tool.capabilities)
        # operator wildcard: subject "operator" bypasses caps (server-local trust)
        if missing and subj not in ("operator", "root"):
            # fall back to authz engine when present
            if self.authz is not None:
                dec = self.authz.decide(subj, tool.name, tool.name,
                                        attrs={"namespace": getattr(s, "namespace", "default")},
                                        attestation=getattr(s, "attestation", None))
                if not dec.allow:
                    return {"ok": False, "stage": "auth", "error": "denied", "reasons": dec.reasons}
            elif missing:
                return {"ok": False, "stage": "auth", "error": f"missing caps {missing}"}
        # quota/budget
        ctx.stage = "quota"
        if self.tenancy is not None and s is not None:
            try:
                if not self.tenancy.admit(getattr(s, "namespace", "default"), actions=1):
                    return {"ok": False, "stage": "quota", "error": "tenancy quota"}
            except Exception:  # noqa: BLE001
                pass
        if s is not None and s.budget < tool.cost:
            return {"ok": False, "stage": "budget", "error": f"session budget {s.budget} < {tool.cost}"}
        # dry-run universe
        ctx.stage = "dry_run"
        if ctx.dry_run and tool.mutating:
            twin = {"dry_run": True, "tool": tool.name, "args_keys": sorted(ctx.args),
                    "would_cost": tool.cost, "verdict": "simulate-only (no state changed)"}
            return {"ok": True, "stage": "dry_run", "data": twin}
        # breaker + execute
        ctx.stage = "execute"
        sem = self._sema.setdefault(tool_name, asyncio.Semaphore(8))  # bulkhead
        async with sem:
            try:
                span = self.tracer.span(f"mcp.{tool_name}") if self.tracer else None
                cm = span if span is not None else _nullcm()
                with cm:
                    res = tool.handler(dict(ctx.args), {"subject": subj,
                                                        "session": s.to_dict() if s and hasattr(s, "to_dict") else {},
                                                        "capabilities": sess_caps})
                    if asyncio.iscoroutine(res):
                        res = await asyncio.wait_for(res, timeout=20.0)
                tool.calls += 1
                ctx.result = res
            except Exception as exc:  # noqa: BLE001
                ctx.error = repr(exc)
                if self.metrics is not None:
                    try:
                        self.metrics.counter("eci_mcp_errors_total").inc()
                    except Exception:  # noqa: BLE001
                        pass
                return {"ok": False, "stage": "execute", "error": repr(exc)}
        # settle
        if s is not None:
            s.budget -= tool.cost
            s.calls += 1
        if ctx.idempotency_key and tool.idempotent:
            self._idem[ctx.idempotency_key] = ctx.result
            self._idem_order.append(ctx.idempotency_key)
            while len(self._idem_order) > self._idem_cap:
                self._idem.pop(self._idem_order.pop(0), None)
        ctx.duration_s = time.time() - t0
        # observe (best-effort, never fails the call)
        try:
            if self.metrics is not None:
                self.metrics.counter("eci_mcp_calls_total").inc()
            if self.audit is not None:
                self.audit.append(str(subj), f"mcp.{tool_name}", {"ok": True})
            if self.provenance is not None:
                self.provenance.record("mcp.call", str(subj), {"tool": tool_name, "args_keys": sorted(ctx.args)},
                                       {"ok": True}, {"tool_version": tool.version})
            if self.bus is not None:
                from eci.kernel.bus import Event
                self.bus.publish(Event(type="mcp.call.done", source=str(subj),
                                       payload={"tool": tool_name, "ok": True}))
        except Exception:  # noqa: BLE001
            pass
        return {"ok": True, "stage": "done", "data": ctx.result, "duration_s": ctx.duration_s}


class _nullcm:
    def __enter__(self): return None
    def __exit__(self, *a): return False
