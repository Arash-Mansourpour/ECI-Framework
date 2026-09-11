"""MCP federation: merge remote tool meshes under a prefix.

A proxy entry maps ``{prefix}.{tool}`` -> remote call (in-process handle
or HTTP POST /mcp). Server side stays dumb; all policy (allowlist,
breaker, timeout) lives here so a rogue upstream can't cascade. Merged
tools appear in tools/list with ``federated: true`` + origin labels.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

__all__ = ["FederatedUpstream", "Federation"]


@dataclass
class FederatedUpstream:
    prefix: str
    call_remote: Callable[[str, dict[str, Any]], Any]  # (tool, args) -> data|awaitable
    allow: list[str] = field(default_factory=lambda: ["*"])
    failures: int = 0
    opened_until: float = 0.0
    breaker_threshold: int = 5
    breaker_cooldown_s: float = 30.0


class Federation:
    def __init__(self, registry=None) -> None:
        self.registry = registry
        self.upstreams: list[FederatedUpstream] = []

    def add(self, upstream: FederatedUpstream) -> None:
        self.upstreams.append(upstream)
        # NOTE: remote tool enumeration is lazy (list on demand) to avoid
        # blocking the mesh on a slow upstream at boot.

    def federated_names(self) -> list[str]:
        return [u.prefix for u in self.upstreams]

    async def call(self, prefixed: str, args: dict[str, Any]) -> Any:
        import asyncio
        import fnmatch
        for u in self.upstreams:
            if prefixed == u.prefix or prefixed.startswith(u.prefix + "."):
                tool = prefixed[len(u.prefix) + 1:]
                if not any(fnmatch.fnmatchcase(tool, pat) for pat in u.allow):
                    raise PermissionError(f"federation deny {prefixed}")
                if time.time() < u.opened_until:
                    raise RuntimeError(f"upstream {u.prefix} circuit-open")
                try:
                    res = u.call_remote(tool, args)
                    if asyncio.iscoroutine(res):
                        res = await asyncio.wait_for(res, timeout=20.0)
                    u.failures = 0
                    return res
                except Exception:
                    u.failures += 1
                    if u.failures >= u.breaker_threshold:
                        u.opened_until = time.time() + u.breaker_cooldown_s
                    raise
        raise KeyError(f"no upstream for {prefixed}")
