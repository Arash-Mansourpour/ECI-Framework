"""MCP server: full protocol surface over registry + pipeline + sessions.

Methods
  initialize / ping
  tools/list {prefix?, capability?} / tools/call {name, arguments, session_id?, idempotency_key?, dry_run?}
  sessions/create / sessions/info
  prompts/list / prompts/get {name, arguments}
  resources/list / resources/read {uri} / resources/subscribe {uri}
  gateway/schema  (introspection passthrough)

Design notes
- handle() is sync-safe (schedules coroutines); handle_async() awaits.
- tools/call never raises: pipeline denials become {error} results AND
  JSON-RPC result envelopes (MCP-friendly), never protocol errors.
- Federation: names with a registered upstream prefix route remote.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from eci.mcp.prompts import PROMPTS, get_prompt
from eci.mcp.resources import RESOURCES, read_resource

__all__ = ["McpServer", "PROTOCOL_VERSION"]

PROTOCOL_VERSION = "2024-11-05"


class McpServer:
    name = "mcp-server"

    def __init__(self, framework: Any = None, registry=None, sessions=None,
                 pipeline=None, federation=None, server_name: str = "eci-omiverse") -> None:
        self.framework = framework
        self.registry = registry
        self.sessions = sessions
        self.pipeline = pipeline
        self.federation = federation
        self.server_name = server_name
        self.started = time.time()
        self.calls = 0

    # -- sync wrapper ---------------------------------------------------
    def handle(self, msg: dict[str, Any]) -> dict[str, Any]:
        res = self.handle_async(msg)
        if asyncio.iscoroutine(res):
            try:
                _loop = asyncio.get_running_loop()
            except RuntimeError:
                return asyncio.run(res)
            # inside a loop (rare for stdio): run in a fresh thread-less way is
            # impossible; fall back to creating a task result placeholder.
            # Callers inside loops should use handle_async directly.
            return {"id": msg.get("id"), "error": "use handle_async inside event loops"}
        return res

    async def handle_async(self, msg: dict[str, Any]) -> dict[str, Any]:
        mid, method, params = msg.get("id"), msg.get("method"), msg.get("params", {}) or {}
        try:
            if method == "initialize":
                return {"id": mid, "result": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "serverInfo": {"name": self.server_name, "version": _ver()},
                    "capabilities": {"tools": True, "prompts": True, "resources": True, "sessions": True,
                                     "dryRun": True, "idempotency": True, "federation": True}}}
            if method == "ping":
                return {"id": mid, "result": {"pong": True, "uptime_s": round(time.time() - self.started, 1)}}
            if method == "tools/list":
                tools = self.registry.list(prefix=params.get("prefix", ""),
                                           capability=params.get("capability", "")) if self.registry else []
                fed = [{"name": f"{p}.*", "description": f"federated via {p}", "federated": True}
                       for p in (self.federation.federated_names() if self.federation else [])]
                return {"id": mid, "result": {"tools": tools + fed}}
            if method == "tools/call":
                return {"id": mid, "result": await self._call(params)}
            if method == "sessions/create":
                s = self.sessions.create(subject=params.get("subject", "anon"),
                                         namespace=params.get("namespace", "default"),
                                         attestation=params.get("attestation", {}),
                                         capabilities=params.get("capabilities", []),
                                         budget=float(params.get("budget", 100.0))) if self.sessions else None
                return {"id": mid, "result": s.to_dict() if s else {}}
            if method == "sessions/info":
                s = self.sessions.get(params.get("session_id", "")) if self.sessions else None
                return {"id": mid, "result": s.to_dict() if s else {"error": "unknown session"}}
            if method == "prompts/list":
                return {"id": mid, "result": {"prompts": [{"name": p["name"], "title": p["title"]} for p in PROMPTS]}}
            if method == "prompts/get":
                return {"id": mid, "result": get_prompt(params.get("name", ""), params.get("arguments", {}))}
            if method == "resources/list":
                return {"id": mid, "result": {"resources": RESOURCES}}
            if method == "resources/read":
                return {"id": mid, "result": read_resource(params.get("uri", ""), self.framework)}
            if method == "resources/subscribe":
                return {"id": mid, "result": {"subscribed": params.get("uri", ""), "via": "/mcp/events (SSE)"}}
            if method == "gateway/schema":
                gw = getattr(self.framework, "gateway", None)
                return {"id": mid, "result": gw.schema() if gw else {}}
            return {"id": mid, "error": f"unknown method {method}"}
        except Exception as exc:  # noqa: BLE001
            return {"id": mid, "error": f"{type(exc).__name__}: {exc}"}

    async def _call(self, params: dict[str, Any]) -> dict[str, Any]:
        self.calls += 1
        name = params.get("name", "")
        args = params.get("arguments", {}) or {}
        # federation route
        if self.federation:
            for prefix in self.federation.federated_names():
                if name == prefix or name.startswith(prefix + "."):
                    try:
                        data = await self.federation.call(name, args)
                        return {"ok": True, "data": data, "federated": prefix}
                    except Exception as exc:  # noqa: BLE001
                        return {"ok": False, "error": repr(exc), "federated": prefix}
        if self.pipeline is None:
            return {"ok": False, "error": "no pipeline"}
        sess = None
        if self.sessions and params.get("session_id"):
            sess = self.sessions.get(params["session_id"])
        return await self.pipeline.run(name, args, session=sess,
                                       session_id=params.get("session_id", ""),
                                       idempotency_key=params.get("idempotency_key", ""),
                                       dry_run=bool(params.get("dry_run", False)))

    def start(self) -> None: ...
    def stop(self) -> None: ...
    def health(self) -> dict[str, Any]:
        return {"ok": True, "tools": len(self.registry.names()) if self.registry else 0,
                "calls": self.calls,
                "sessions": self.sessions.stats() if self.sessions else {}}


def _ver() -> str:
    try:
        from eci.version import FRAMEWORK_VERSION
        return FRAMEWORK_VERSION
    except Exception:  # noqa: BLE001
        return "6.x"
