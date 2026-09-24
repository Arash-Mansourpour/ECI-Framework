"""OTel bridge v8 (ADR-005). NoOp unless opentelemetry SDK installed.

Wraps eci.observability.tracing.Tracer spans as OTel spans when available.
Never raises: all failures degrade to local tracer.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator


class OtelBridge:
    """Graceful OpenTelemetry facade."""

    def __init__(self, service: str = "eci") -> None:
        self.service = service
        self._tracer = None
        try:
            from opentelemetry import trace as _trace  # type: ignore

            self._tracer = _trace.get_tracer(service)
            self.available = True
        except Exception:  # noqa: BLE001
            self.available = False

    @contextmanager
    def span(self, name: str, attributes: dict[str, Any] | None = None) -> Iterator[Any]:
        if self._tracer is None:
            yield {"name": name, "noop": True, "attributes": attributes or {}}
            return
        try:
            with self._tracer.start_as_current_span(name) as span:
                if attributes:
                    for k, v in attributes.items():
                        try:
                            span.set_attribute(k, str(v))
                        except Exception:  # noqa: BLE001
                            pass
                yield span
        except Exception:  # noqa: BLE001
            yield {"name": name, "noop": True, "fallback": True}

    def health(self) -> dict[str, Any]:
        return {"otel_available": self.available, "service": self.service}
