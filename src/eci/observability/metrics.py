"""Metrics registry: Counter / Gauge / Histogram + Prometheus exposition."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field

__all__ = ["Counter", "Gauge", "Histogram", "MetricsRegistry"]


@dataclass
class Counter:
    name: str
    value: float = 0.0
    def inc(self, amount: float = 1.0) -> None:
        self.value += amount


@dataclass
class Gauge:
    name: str
    value: float = 0.0
    def set(self, v: float) -> None:
        self.value = v
    def inc(self, d: float = 1.0) -> None:
        self.value += d
    def dec(self, d: float = 1.0) -> None:
        self.value -= d


@dataclass
class Histogram:
    name: str
    buckets: list[float] = field(default_factory=lambda: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0])
    counts: list[int] = field(default_factory=list)
    count: int = 0
    total: float = 0.0
    def __post_init__(self) -> None:
        if not self.counts:
            self.counts = [0] * (len(self.buckets) + 1)
    def observe(self, v: float) -> None:
        self.count += 1
        self.total += v
        for i, b in enumerate(self.buckets):
            if v <= b:
                self.counts[i] += 1
                return
        self.counts[-1] += 1
    @property
    def mean(self) -> float:
        return self.total / self.count if self.count else 0.0


class MetricsRegistry:
    """Thread-safe registry with Prometheus text exposition."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.counters: dict[str, Counter] = {}
        self.gauges: dict[str, Gauge] = {}
        self.histograms: dict[str, Histogram] = {}

    def counter(self, name: str) -> Counter:
        with self._lock:
            return self.counters.setdefault(name, Counter(name))

    def gauge(self, name: str) -> Gauge:
        with self._lock:
            return self.gauges.setdefault(name, Gauge(name))

    def histogram(self, name: str) -> Histogram:
        with self._lock:
            return self.histograms.setdefault(name, Histogram(name))

    def to_prometheus(self) -> str:
        lines: list[str] = []
        for c in self.counters.values():
            lines.append(f"# TYPE {c.name} counter\n{c.name} {c.value}")
        for g in self.gauges.values():
            lines.append(f"# TYPE {g.name} gauge\n{g.name} {g.value}")
        for h in self.histograms.values():
            lines.append(f"# TYPE {h.name} histogram\n{h.name}_count {h.count}\n{h.name}_sum {h.total}")
            for i, b in enumerate(h.buckets):
                lines.append(f'{h.name}_bucket{{le="{b}"}} {sum(h.counts[:i+1])}')
            lines.append(f'{h.name}_bucket{{le="+Inf"}} {h.count}')
        return "\n".join(lines) + ("\n" if lines else "")

    def snapshot(self) -> dict[str, float]:
        out: dict[str, float] = {}
        out.update({k: v.value for k, v in self.counters.items()})
        out.update({k: v.value for k, v in self.gauges.items()})
        out.update({k + "_mean": v.mean for k, v in self.histograms.items()})
        return out
