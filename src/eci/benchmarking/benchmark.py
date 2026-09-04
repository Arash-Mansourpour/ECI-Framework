"""Research benchmarking with statistics, timing and export."""

from __future__ import annotations

import csv
import io
import json
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterator, List, Optional

import numpy as np

from eci.logging import get_logger

__all__ = ["ResearchBenchmark"]


class ResearchBenchmark:
    """Metric recording, statistical summary and report generation."""

    def __init__(self, experiment_name: str) -> None:
        if not experiment_name:
            raise ValueError("experiment_name must be non-empty")
        self.experiment_name = experiment_name
        self.logger = get_logger("benchmark")
        self.metrics: Dict[str, List[dict]] = {}
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

    # ------------------------------------------------------------------
    def start_experiment(self) -> None:
        self.start_time = time.time()
        self.logger.info("starting experiment: %s", self.experiment_name)

    def end_experiment(self) -> float:
        self.end_time = time.time()
        duration = self._duration()
        self.logger.info("experiment completed in %.2fs", duration)
        return duration

    def _duration(self) -> float:
        if self.start_time is None:
            return 0.0
        return (self.end_time if self.end_time is not None else time.time()) - self.start_time

    @contextmanager
    def timer(self, metric_name: str) -> Iterator[None]:
        """Context manager recording wall-clock duration of a block."""
        t0 = time.perf_counter()
        try:
            yield
        finally:
            self.record_metric(metric_name, time.perf_counter() - t0)

    # ------------------------------------------------------------------
    def record_metric(self, metric_name: str, value: float, step: Optional[int] = None) -> None:
        self.metrics.setdefault(metric_name, []).append(
            {"value": float(value), "step": step, "timestamp": time.time()}
        )

    def get_statistics(self, metric_name: str) -> Dict[str, float]:
        if metric_name not in self.metrics:
            return {}
        values = np.array([m["value"] for m in self.metrics[metric_name]], dtype=float)
        return {
            "mean": float(values.mean()),
            "std": float(values.std()),
            "min": float(values.min()),
            "max": float(values.max()),
            "median": float(np.median(values)),
            "count": int(values.size),
        }

    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "experiment_name": self.experiment_name,
            "duration_seconds": self._duration(),
            "metrics": {name: self.get_statistics(name) for name in sorted(self.metrics)},
        }

    def generate_report(self) -> str:
        bar = "=" * 78
        report = f"\n{bar}\nBENCHMARK REPORT: {self.experiment_name}\n{bar}\n\n"
        if self.start_time is not None:
            report += f"Duration: {self._duration():.2f} seconds\n\n"
        report += "METRICS SUMMARY:\n" + "-" * 78 + "\n"
        for metric_name in sorted(self.metrics):
            stats = self.get_statistics(metric_name)
            report += (
                f"\n{metric_name}:\n"
                f"  Mean:   {stats['mean']:.6f}\n"
                f"  Std:    {stats['std']:.6f}\n"
                f"  Min:    {stats['min']:.6f}\n"
                f"  Max:    {stats['max']:.6f}\n"
                f"  Median: {stats['median']:.6f}\n"
                f"  Count:  {stats['count']}\n"
            )
        report += "\n" + bar + "\n"
        return report

    # ------------------------------------------------------------------
    def export_json(self, path: Path | str) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    def export_csv(self, path: Path | str) -> None:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["metric", "value", "step", "timestamp"])
        for name, entries in self.metrics.items():
            for entry in entries:
                writer.writerow([name, entry["value"], entry["step"], entry["timestamp"]])
        Path(path).write_text(buffer.getvalue(), encoding="utf-8")
