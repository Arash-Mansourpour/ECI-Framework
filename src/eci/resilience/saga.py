"""Token-bucket rate limiter + Saga orchestrator with compensation."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

__all__ = ["TokenBucket", "RateLimitExceeded", "Saga", "SagaStep"]


class RateLimitExceeded(RuntimeError):
    pass


class TokenBucket:
    """Thread-unsafe but deterministic; per-tenant instances expected."""

    def __init__(self, rate_per_s: float = 10.0, capacity: float = 20.0) -> None:
        self.rate = rate_per_s
        self.capacity = capacity
        self.tokens = capacity
        self.updated = time.time()
        self.allowed = 0
        self.denied = 0

    def _refill(self) -> None:
        now = time.time()
        self.tokens = min(self.capacity, self.tokens + (now - self.updated) * self.rate)
        self.updated = now

    def allow(self, cost: float = 1.0) -> bool:
        self._refill()
        if self.tokens >= cost:
            self.tokens -= cost
            self.allowed += 1
            return True
        self.denied += 1
        return False

    def require(self, cost: float = 1.0) -> None:
        if not self.allow(cost):
            raise RateLimitExceeded("rate limit exceeded")


@dataclass
class SagaStep:
    name: str
    action: Callable[..., Any]
    compensate: Callable[..., Any] | None = None


class Saga:
    """Sequential saga: on step failure, run compensations in reverse."""

    def __init__(self, name: str = "saga") -> None:
        self.name = name
        self.steps: list[SagaStep] = []

    def add(self, name: str, action: Callable[..., Any],
            compensate: Callable[..., Any] | None = None) -> Saga:
        self.steps.append(SagaStep(name, action, compensate))
        return self

    async def run(self, ctx: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx = ctx or {}
        done: list[SagaStep] = []
        try:
            for st in self.steps:
                res = st.action(ctx)
                if asyncio.iscoroutine(res):
                    res = await res
                ctx[st.name] = res
                done.append(st)
            return {"ok": True, "ctx": ctx}
        except Exception as exc:  # noqa: BLE001
            comp_errors: list[str] = []
            for st in reversed(done):
                if st.compensate is not None:
                    try:
                        r = st.compensate(ctx)
                        if asyncio.iscoroutine(r):
                            await r
                    except Exception as cexc:  # noqa: BLE001
                        comp_errors.append(f"{st.name}: {cexc}")
            return {"ok": False, "error": repr(exc), "compensated": [s.name for s in done],
                    "compensation_errors": comp_errors, "ctx": ctx}
