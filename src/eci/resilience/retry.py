"""Retry with exponential backoff + jitter + deadline, sync and async."""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Tuple, Type

__all__ = ["RetryPolicy"]


@dataclass
class RetryPolicy:
    attempts: int = 3
    base_delay_s: float = 0.05
    max_delay_s: float = 2.0
    multiplier: float = 2.0
    jitter: float = 0.1
    retry_on: Tuple[Type[BaseException], ...] = (Exception,)
    deadline_s: float = 30.0

    def _delay(self, attempt: int) -> float:
        d = min(self.base_delay_s * (self.multiplier ** attempt), self.max_delay_s)
        return d * (1.0 + random.uniform(-self.jitter, self.jitter))

    def run(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        start = time.time()
        last: BaseException | None = None
        for i in range(self.attempts):
            try:
                return fn(*args, **kwargs)
            except self.retry_on as exc:  # noqa: BLE001
                last = exc
                if i == self.attempts - 1 or (time.time() - start) > self.deadline_s:
                    raise
                time.sleep(max(0.0, self._delay(i)))
        assert last is not None
        raise last

    async def arun(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        start = time.time()
        last: BaseException | None = None
        for i in range(self.attempts):
            try:
                res = fn(*args, **kwargs)
                if asyncio.iscoroutine(res):
                    res = await res
                return res
            except self.retry_on as exc:  # noqa: BLE001
                last = exc
                if i == self.attempts - 1 or (time.time() - start) > self.deadline_s:
                    raise
                await asyncio.sleep(max(0.0, self._delay(i)))
        assert last is not None
        raise last
