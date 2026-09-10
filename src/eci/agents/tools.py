"""Tool registry: versioned, schema-validated, budget-metered tools.

Every agent action goes through here so authz + economy + provenance see
the same call. Tools declare JSON-schema-ish params (name->type), a cost
in economy credits, and required capabilities. Execution is sync-or-async
transparent, with timeout and per-call budget deduction hooks.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

__all__ = ["ToolSpec", "ToolRegistry", "ToolDenied", "ToolBudgetExceeded"]


class ToolDenied(PermissionError):
    pass


class ToolBudgetExceeded(RuntimeError):
    pass


@dataclass
class ToolSpec:
    name: str
    fn: Callable[..., Any]
    params: Dict[str, str] = field(default_factory=dict)  # name -> "str|int|float|bool|any"
    cost: float = 5.0
    capabilities: List[str] = field(default_factory=list)
    timeout_s: float = 15.0
    description: str = ""
    calls: int = 0


def _coerce(params: Dict[str, str], args: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, t in params.items():
        if k not in args:
            raise ValueError(f"missing param {k!r}")
        v = args[k]
        try:
            if t == "str": out[k] = str(v)
            elif t == "int": out[k] = int(v)
            elif t == "float": out[k] = float(v)
            elif t == "bool": out[k] = bool(v)
            else: out[k] = v
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"param {k!r}: {exc}")
    return out


class ToolRegistry:
    name = "tools"

    def __init__(self) -> None:
        self._tools: Dict[str, ToolSpec] = {}

    def register(self, name: str, fn: Callable[..., Any], params: Dict[str, str] | None = None,
                 cost: float = 5.0, capabilities: List[str] | None = None,
                 description: str = "", timeout_s: float = 15.0) -> ToolSpec:
        spec = ToolSpec(name, fn, params or {}, cost, capabilities or [], timeout_s, description)
        self._tools[name] = spec
        return spec

    def names(self) -> List[str]:
        return sorted(self._tools)

    def manifest(self) -> List[Dict[str, Any]]:
        return [{"name": s.name, "params": s.params, "cost": s.cost,
                 "capabilities": s.capabilities, "description": s.description}
                for s in self._tools.values()]

    async def call(self, name: str, args: Dict[str, Any] | None = None,
                   ctx: Dict[str, Any] | None = None) -> Dict[str, Any]:
        t0 = time.time()
        ctx = ctx or {}
        spec = self._tools.get(name)
        if spec is None:
            return {"ok": False, "error": f"unknown tool {name}"}
        # capability gate
        have = set(ctx.get("capabilities", []))
        missing = [c for c in spec.capabilities if c not in have]
        if missing:
            return {"ok": False, "error": f"missing caps {missing}"}
        # budget gate
        budget = ctx.get("budget")
        if budget is not None and budget < spec.cost:
            return {"ok": False, "error": f"budget {budget} < cost {spec.cost}"}
        try:
            coerced = _coerce(spec.params, args or {})
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": f"bad params: {exc}"}
        try:
            res = spec.fn(coerced, ctx)
            if asyncio.iscoroutine(res):
                res = await asyncio.wait_for(res, timeout=spec.timeout_s)
            spec.calls += 1
            return {"ok": True, "data": res, "cost": spec.cost,
                    "duration_s": time.time() - t0, "calls": spec.calls}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": repr(exc), "cost": 0.0}

    def start(self) -> None: ...
    def stop(self) -> None: ...
    def health(self) -> Dict[str, Any]:
        return {"ok": True, "tools": len(self._tools),
                "calls": {k: v.calls for k, v in self._tools.items()}}
