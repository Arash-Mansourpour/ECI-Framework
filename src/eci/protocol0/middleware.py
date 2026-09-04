"""Execution middleware: gate ANY callable by Protocol-0 policy.

Modes: ``enforce`` (deny + raise), ``audit-only`` (allow + ledger note),
``permissive`` (allow + warn on deny). Context carries the caller's live
awareness/obedience/trust + optional collective state, so tool-calls,
code-exec and egress all pass one choke point instead of optional wrappers.

Usage:
    gate = Middleware(spec, mode="enforce", ledger=ledger)
    gate.bind(agent_id, awareness=0.6, obedience=0.8, trust=0.9)

    @gate.requires("execute_tool")
    def run_tool(x): ...
"""

from __future__ import annotations

import functools
from typing import Any, Callable, Dict, Optional

from eci.logging import get_logger
from eci.protocol0.ledger import Ledger
from eci.protocol0.policy import check
from eci.protocol0.spec import Protocol0Spec

__all__ = ["Middleware"]


class Middleware:
    def __init__(self, spec: Protocol0Spec, mode: str = "enforce", ledger: Optional[Ledger] = None) -> None:
        if mode not in ("enforce", "audit-only", "permissive"):
            raise ValueError(f"unknown middleware mode {mode!r}")
        self.spec = spec
        self.mode = mode
        self.ledger = ledger
        self.logger = get_logger("protocol0.middleware")
        self.context: Dict[str, Dict[str, float]] = {}

    def bind(self, agent_id: str, awareness: float, obedience: float, trust: float,
             coherence: Optional[float] = None, divergence: Optional[float] = None) -> None:
        self.context[agent_id] = {
            "awareness": awareness, "obedience": obedience, "trust": trust,
            "coherence": coherence if coherence is not None else 1.0,
            "divergence": divergence if divergence is not None else 0.0,
        }

    def authorize(self, agent_id: str, action: str) -> bool:
        ctx = self.context.get(agent_id)
        if ctx is None:
            if self.ledger:
                self.ledger.append("policy_deny", {"node": agent_id, "action": action, "reason": "unbound agent"})
            if self.mode == "enforce":
                raise PermissionError(f"unbound agent {agent_id!r}")
            return False
        d = check(self.spec, action, ctx["awareness"], ctx["obedience"], ctx["trust"],
                  coherence=ctx["coherence"], divergence=ctx["divergence"])
        if self.ledger:
            self.ledger.append("allow" if d.allow else "policy_deny",
                               {"node": agent_id, "action": action, "reason": d.reason})
        if not d.allow and self.mode == "enforce":
            raise PermissionError(f"protocol0 denied {action}: {d.reason}")
        if not d.allow:
            self.logger.warning("protocol0 %s: %s denied (%s)", self.mode, action, d.reason)
        return d.allow

    def requires(self, action: str, agent_kw: str = "agent_id") -> Callable:
        """Decorator: resolve agent_id from kwarg (default) or first arg."""

        def deco(fn: Callable) -> Callable:
            @functools.wraps(fn)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                if agent_kw in kwargs:
                    agent_id = kwargs[agent_kw]
                elif args and isinstance(args[0], str):
                    agent_id = args[0]
                else:
                    raise PermissionError("middleware: no agent_id to authorize")
                self.authorize(str(agent_id), action)
                return fn(*args, **kwargs)

            return wrapper

        return deco
