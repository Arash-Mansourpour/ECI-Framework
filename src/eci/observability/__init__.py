"""Observability facade: tracer + metrics + audit wired to the kernel bus."""

from eci.observability.audit import AuditLogger, AuditRecord
from eci.observability.metrics import Counter, Gauge, Histogram, MetricsRegistry
from eci.observability.otel import OtelBridge
from eci.observability.tracing import Span, Tracer

__all__ = ["Tracer", "Span", "MetricsRegistry", "Counter", "Gauge", "Histogram",
           "AuditLogger", "AuditRecord", "Observability", "OtelBridge"]


class Observability:
    """One handle owned by ECIFramework; also subscribes audit.* to the bus."""

    name = "observability"

    def __init__(self, service: str = "eci", audit_path=None) -> None:
        self.tracer = Tracer(service=service)
        self.metrics = MetricsRegistry()
        self.audit = AuditLogger(path=audit_path)
        self._started = False

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False

    def health(self) -> dict:
        return {"ok": True, "spans": self.tracer.stats()["spans"],
                "audit_records": len(self.audit), "audit_ok": self.audit.verify()["ok"]}

    def bind_bus(self, bus) -> None:
        def _on_audit(event) -> None:
            try:
                self.audit.append(actor=str(event.source), action=str(event.type),
                                  details=dict(event.payload))
            except Exception:  # noqa: BLE001
                pass
        bus.subscribe("audit.*", _on_audit, name="observability-audit-sink")
