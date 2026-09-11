"""Circuit breaker: fail-fast wrapper around flaky calls."""

from __future__ import annotations

import time
from collections.abc import Callable
from enum import Enum
from typing import Any

__all__ = ["CircuitState", "CircuitBreaker", "CircuitOpenError"]


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(RuntimeError):
    pass


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, reset_timeout_s: float = 30.0,
                 success_threshold: int = 2, name: str = "cb") -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_timeout_s = reset_timeout_s
        self.success_threshold = success_threshold
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.successes = 0
        self.opened_at = 0.0
        self.calls = 0
        self.rejected = 0

    def _maybe_half_open(self) -> None:
        if self.state == CircuitState.OPEN and (time.time() - self.opened_at) >= self.reset_timeout_s:
            self.state = CircuitState.HALF_OPEN
            self.successes = 0

    def call(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        self._maybe_half_open()
        if self.state == CircuitState.OPEN:
            self.rejected += 1
            raise CircuitOpenError(f"circuit {self.name} is OPEN")
        self.calls += 1
        try:
            out = fn(*args, **kwargs)
        except Exception:
            self.failures += 1
            self.successes = 0
            if self.failures >= self.failure_threshold:
                self.state = CircuitState.OPEN
                self.opened_at = time.time()
            raise
        else:
            if self.state == CircuitState.HALF_OPEN:
                self.successes += 1
                if self.successes >= self.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.failures = 0
            else:
                self.failures = 0
            return out

    def stats(self) -> dict[str, Any]:
        return {"name": self.name, "state": self.state.value, "calls": self.calls,
                "failures": self.failures, "rejected": self.rejected}
