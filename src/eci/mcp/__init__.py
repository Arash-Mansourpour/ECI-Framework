"""Omniverse MCP Fabric: registry + sessions + pipeline + server + transports.

One-liner for servers, CLIs, tests and the agent loop:

    from eci.mcp import McpFabric
    fabric = McpFabric(framework)          # wires ~30 tools, prompts, resources
    fabric.server.handle({"id":1,"method":"tools/list","params":{}})

Creative core: tools are a *federated mesh* (local + gateway-bridged +
agent-bridged + remote upstreams), calls flow through a policy pipeline
(auth/quota/budget/dry-run/breaker/observe), sessions carry budgets, and
every mutating tool supports dry_run twin simulation + idempotency keys.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from eci.mcp.fabric import build_default_registry
from eci.mcp.federation import FederatedUpstream, Federation
from eci.mcp.pipeline import CallCtx, McpPipeline
from eci.mcp.prompts import PROMPTS, get_prompt
from eci.mcp.registry import McpRegistry, McpTool
from eci.mcp.resources import RESOURCES, read_resource
from eci.mcp.schema import build_input_schema
from eci.mcp.server import McpServer
from eci.mcp.sessions import Session, SessionManager
from eci.mcp.transports import HttpTransport, InProcessTransport, StdioTransport

__all__ = ["McpFabric", "McpRegistry", "McpTool", "McpServer", "McpPipeline",
           "Session", "SessionManager", "Federation", "FederatedUpstream",
           "InProcessTransport", "StdioTransport", "HttpTransport",
           "PROMPTS", "RESOURCES", "build_input_schema"]


class McpFabric:
    """Owns the full MCP stack for one framework instance."""

    name = "mcp-fabric"

    def __init__(self, framework: Any = None) -> None:
        self.framework = framework
        F = framework
        self.registry = McpRegistry()
        if F is not None:
            build_default_registry(F, self.registry)
            # bridge remaining gateway routes + agent tools not covered above
            try:
                self.registry.bridge_gateway(F.gateway)
            except Exception:  # noqa: BLE001
                pass
            try:
                if getattr(F, "agents", None) is not None:
                    self.registry.bridge_agent_tools(F.agents.tools)
            except Exception:  # noqa: BLE001
                pass
        self.sessions = SessionManager()
        self.federation = Federation(self.registry)
        self.pipeline = McpPipeline(
            registry=self.registry, sessions=self.sessions,
            authz=getattr(F, "authz", None), economy=getattr(F, "economy", None),
            tenancy=getattr(F, "tenancy", None),
            tracer=getattr(getattr(F, "observability", None), "tracer", None),
            metrics=getattr(getattr(F, "observability", None), "metrics", None),
            audit=getattr(getattr(F, "observability", None), "audit", None),
            provenance=getattr(F, "provenance", None),
            bus=getattr(F, "bus", None))
        self.server = McpServer(framework=F, registry=self.registry,
                                sessions=self.sessions, pipeline=self.pipeline,
                                federation=self.federation)
        self.transport = InProcessTransport(self.server.handle)

    def request(self, method: str, params: Dict[str, Any] | None = None, _id: Any = 1) -> Dict[str, Any]:
        return self.transport.request(method, params, _id)

    def serve_stdio(self) -> None:
        StdioTransport(self.server.handle).serve_forever()

    def serve_http(self, host: str = "127.0.0.1", port: int = 8899) -> None:
        HttpTransport(self.server.handle, host, port).serve_forever()

    def start(self) -> None: ...
    def stop(self) -> None: ...
    def health(self) -> Dict[str, Any]:
        return {"ok": True, "fabric": self.server.health(),
                "federated": self.federation.federated_names()}
