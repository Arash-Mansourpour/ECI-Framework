"""Resilience facade: breaker registry + default retry + rate limiters + sagas."""

from typing import Any

from eci.resilience.circuit import CircuitBreaker, CircuitOpenError, CircuitState
from eci.resilience.retry import RetryPolicy
from eci.resilience.saga import RateLimitExceeded, Saga, SagaStep, TokenBucket

__all__ = ["CircuitBreaker", "CircuitOpenError", "CircuitState", "RetryPolicy",
           "Saga", "SagaStep", "TokenBucket", "RateLimitExceeded", "Resilience"]


class Resilience:
    name = "resilience"

    def __init__(self) -> None:
        self.breakers: dict[str, CircuitBreaker] = {}
        self.limiters: dict[str, TokenBucket] = {}
        self.retry = RetryPolicy()

    def breaker(self, name: str, **kw: Any) -> CircuitBreaker:
        return self.breakers.setdefault(name, CircuitBreaker(name=name, **kw))

    def limiter(self, name: str, **kw: Any) -> TokenBucket:
        return self.limiters.setdefault(name, TokenBucket(**kw))

    def saga(self, name: str = "saga") -> Saga:
        return Saga(name)

    def start(self) -> None: ...
    def stop(self) -> None: ...
    def health(self) -> dict[str, Any]:
        return {"ok": True, "breakers": {k: v.stats() for k, v in self.breakers.items()},
                "limiters": len(self.limiters)}
