"""Unified MCP tool registry: one mesh for gateway routes + agent tools.

A McpTool wraps any callable ``fn(args, ctx) -> data|awaitable`` with:
versioning + deprecation, capability tags (wildcard-grantable like
``quantum.*``), economy cost, mutating flag (enables dry_run/twin),
idempotency support and JSON inputSchema. Bridges import from Gateway
routes (``v1/system.status`` -> ``system.status``) and ToolRegistry
(``echo`` -> ``agent.echo``) without duplicating logic.
"""

from __future__ import annotations

import fnmatch
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from eci.mcp.schema import build_input_schema

__all__ = ["McpTool", "McpRegistry"]


@dataclass
class McpTool:
    name: str
    description: str
    handler: Callable[..., Any]
    inputSchema: Dict[str, Any] = field(default_factory=lambda: {"type": "object"})
    version: str = "1.0.0"
    capabilities: List[str] = field(default_factory=list)
    cost: float = 1.0
    mutating: bool = False
    idempotent: bool = True
    deprecated: str = ""
    calls: int = 0

    def descriptor(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"name": self.name, "description": self.description,
                             "inputSchema": self.inputSchema, "version": self.version,
                             "capabilities": self.capabilities, "cost": self.cost,
                             "mutating": self.mutating, "idempotent": self.idempotent}
        if self.deprecated:
            d["deprecated"] = self.deprecated
        # MCP annotations hint execution semantics to clients
        d["annotations"] = {"readOnlyHint": not self.mutating,
                            "idempotentHint": self.idempotent,
                            "openWorldHint": False}
        return d


class McpRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, McpTool] = {}

    def register(self, tool: McpTool, overwrite: bool = False) -> None:
        if tool.name in self._tools and not overwrite:
            raise KeyError(f"tool {tool.name!r} already registered")
        self._tools[tool.name] = tool

    def tool(self, name: str, fn: Callable[..., Any], description: str = "",
             params: Dict[str, str] | None = None, **kw: Any) -> McpTool:
        t = McpTool(name=name, description=description or name, handler=fn,
                    inputSchema=build_input_schema(params or {}), **kw)
        self.register(t, overwrite=kw.pop("overwrite", False))
        return t

    def get(self, name: str) -> Optional[McpTool]:
        return self._tools.get(name)

    def names(self) -> List[str]:
        return sorted(self._tools)

    def list(self, prefix: str = "", capability: str = "",
             include_deprecated: bool = False) -> List[Dict[str, Any]]:
        out = []
        for t in self._tools.values():
            if prefix and not (t.name == prefix or t.name.startswith(prefix)):
                continue
            if capability and not any(fnmatch.fnmatchcase(t.name, c) or fnmatch.fnmatchcase(c, t.name)
                                      for c in [capability] + t.capabilities):
                # capability filter matches tool caps OR name patterns
                if capability not in t.capabilities and not fnmatch.fnmatchcase(t.name, capability):
                    continue
            if t.deprecated and not include_deprecated:
                continue
            out.append(t.descriptor())
        return sorted(out, key=lambda d: d["name"])

    # -- bridges ------------------------------------------------------
    def bridge_gateway(self, gateway: Any, prefix_map: Dict[str, str] | None = None,
                       auth_default: str = "") -> int:
        """Expose Gateway routes as ``ns.action`` tools (read-only unless mutating)."""
        n = 0
        for path in gateway.paths():
            route = gateway._routes[path]
            name = (prefix_map or {}).get(path, path.replace("v1/", "").replace("/", ".").replace("-", "."))
            mutating = any(k in name for k in ("append", "vote", "propose", "spend", "allocate", "run", "execute", "register"))
            self.register(McpTool(
                name=name, description=route.summary or name,
                handler=(lambda p, _r=route: _r.handler(p, {})),
                inputSchema={"type": "object", "additionalProperties": True},
                capabilities=[route.auth_action] if route.auth_action else [],
                mutating=mutating), overwrite=True)
            n += 1
        return n

    def bridge_agent_tools(self, tools: Any, prefix: str = "agent") -> int:
        from eci.mcp.schema import build_input_schema as _b
        n = 0
        for name in tools.names():
            spec = tools._tools[name]
            async def _h(args: Dict[str, Any], ctx: Dict[str, Any], _n=name) -> Any:
                out = await tools.call(_n, args, ctx)
                if not out.get("ok"):
                    raise RuntimeError(out.get("error", "tool failed"))
                return out.get("data")
            self.register(McpTool(
                name=f"{prefix}.{name}", description=spec.description or name, handler=_h,
                inputSchema=_b(spec.params), capabilities=list(spec.capabilities),
                cost=spec.cost, mutating=name not in ("echo",)), overwrite=True)
            n += 1
        return n
