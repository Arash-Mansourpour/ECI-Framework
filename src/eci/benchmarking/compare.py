"""Versioned, paired benchmark comparisons for research agents and policies.

Every candidate is evaluated on the same cases and seeds. Scores are
normalized to [0, 1], failures count as zero and remain visible, and the JSON
report carries a content hash for the exact suite used.
"""

from __future__ import annotations

import asyncio
import copy
import hashlib
import inspect
import json
import math
import platform
import random
import statistics
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ScoreFunction = Callable[[Any, Any], float]
Candidate = Callable[[dict[str, Any], int], Any]


def exact_match_score(actual: Any, expected: Any) -> float:
    """Binary score suitable for exact-answer tasks."""
    return float(actual == expected)


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    input: dict[str, Any]
    expected: Any

    def __post_init__(self) -> None:
        if not self.case_id.strip():
            raise ValueError("case_id must not be empty")
        # Fail at suite construction rather than midway through a long run.
        json.dumps({"input": self.input, "expected": self.expected}, sort_keys=True,
                   allow_nan=False)


@dataclass(frozen=True)
class BenchmarkSuite:
    name: str
    version: str
    cases: tuple[BenchmarkCase, ...]
    scorer: ScoreFunction = field(default=exact_match_score, compare=False, repr=False)
    scorer_id: str = "exact-match-v1"
    metric_name: str = "score"
    scorer_config: dict[str, Any] = field(default_factory=dict, compare=False)

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.version.strip():
            raise ValueError("benchmark suite name and version are required")
        if not self.cases:
            raise ValueError("benchmark suite must contain at least one case")
        ids = [case.case_id for case in self.cases]
        if len(ids) != len(set(ids)):
            raise ValueError("benchmark case IDs must be unique")
        if not self.scorer_id.strip() or not self.metric_name.strip():
            raise ValueError("scorer_id and metric_name are required")
        json.dumps(self.scorer_config, sort_keys=True, allow_nan=False)

    def fingerprint(self) -> str:
        body = {
            "name": self.name,
            "version": self.version,
            "scorer_id": self.scorer_id,
            "metric_name": self.metric_name,
            "scorer_config": self.scorer_config,
            "cases": [
                {"case_id": c.case_id, "input": c.input, "expected": c.expected}
                for c in self.cases
            ],
        }
        encoded = json.dumps(body, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * p
    lo = int(position)
    hi = min(lo + 1, len(ordered) - 1)
    weight = position - lo
    return ordered[lo] * (1.0 - weight) + ordered[hi] * weight


def _bootstrap_ci(values: list[float], seed: int, samples: int = 2000) -> list[float]:
    if len(values) == 1:
        return [values[0], values[0]]
    rng = random.Random(seed)
    means = [statistics.fmean(rng.choices(values, k=len(values))) for _ in range(samples)]
    return [round(_percentile(means, 0.025), 8), round(_percentile(means, 0.975), 8)]


def _paired_cluster_ci(rows: list[dict[str, Any]], metric: str,
                       seed: int, samples: int = 1000) -> list[float]:
    """Two-way bootstrap over cases and seeds, preserving paired repeats."""
    case_ids = sorted({str(row["case_id"]) for row in rows})
    seeds = sorted({int(row["seed"]) for row in rows})
    if len(case_ids) * len(seeds) == 1:
        value = float(rows[0][metric])
        return [value, value]
    values = {(str(row["case_id"]), int(row["seed"])): float(row[metric]) for row in rows}
    rng = random.Random(seed)
    means = []
    for _ in range(samples):
        sampled_cases = rng.choices(case_ids, k=len(case_ids))
        sampled_seeds = rng.choices(seeds, k=len(seeds))
        means.append(statistics.fmean(
            values[(case_id, seed_value)]
            for case_id in sampled_cases for seed_value in sampled_seeds
        ))
    return [round(_percentile(means, 0.025), 8), round(_percentile(means, 0.975), 8)]


def _summary(name: str, rows: list[dict[str, Any]], bootstrap_seed: int) -> dict[str, Any]:
    scores = [float(row["score"]) for row in rows]
    latencies = [float(row["latency_s"]) for row in rows]
    return {
        "name": name,
        "mean_score": round(statistics.fmean(scores), 8),
        "std_score": round(statistics.pstdev(scores), 8),
        "score_ci95_bootstrap": _paired_cluster_ci(rows, "score", seed=bootstrap_seed),
        "mean_latency_s": round(statistics.fmean(latencies), 8),
        "n": len(scores),
        "failures": sum(1 for row in rows if row["error"] is not None),
    }


async def _evaluate(suite: BenchmarkSuite, name: str, candidate: Candidate,
                    seeds: Sequence[int]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for seed in seeds:
        for case in suite.cases:
            error = None
            score = 0.0
            started = asyncio.get_running_loop().time()
            try:
                args = (copy.deepcopy(case.input), int(seed))
                if inspect.iscoroutinefunction(candidate):
                    output = await candidate(*args)
                else:
                    output = await asyncio.to_thread(candidate, *args)
                if inspect.isawaitable(output):
                    output = await output
                score = float(suite.scorer(output, case.expected))
                if not math.isfinite(score) or not 0.0 <= score <= 1.0:
                    raise ValueError("scorer must return a finite value in [0, 1]")
            except Exception as exc:  # noqa: BLE001
                error = f"{type(exc).__name__}: {str(exc)[:200]}"
                score = 0.0
            rows.append({
                "case_id": case.case_id,
                "seed": int(seed),
                "score": round(score, 8),
                "latency_s": round(asyncio.get_running_loop().time() - started, 8),
                "error": error,
            })
    return rows


@dataclass
class BenchmarkComparison:
    suite: dict[str, Any]
    seeds: list[int]
    baseline: dict[str, Any]
    candidate: dict[str, Any]
    paired: dict[str, Any]
    observations: list[dict[str, Any]]
    environment: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "suite": dict(self.suite),
            "seeds": list(self.seeds),
            "baseline": dict(self.baseline),
            "candidate": dict(self.candidate),
            "paired": dict(self.paired),
            "observations": [dict(row) for row in self.observations],
            "environment": dict(self.environment),
        }

    def to_json(self, path: str | Path | None = None) -> str:
        text = json.dumps(self.to_dict(), indent=2, sort_keys=True, ensure_ascii=False)
        if path is not None:
            destination = Path(path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(text + "\n", encoding="utf-8")
        return text


async def compare_async(suite: BenchmarkSuite, baseline_name: str, baseline: Candidate,
                        candidate_name: str, candidate: Candidate,
                        seeds: Sequence[int] = (0,), bootstrap_seed: int = 0,
                        bus: Any = None,
                        baseline_metadata: dict[str, Any] | None = None,
                        candidate_metadata: dict[str, Any] | None = None) -> BenchmarkComparison:
    """Compare two implementations on identical cases and seeds.

    Candidate functions receive ``(input_dict, seed)`` and may be synchronous
    or asynchronous. Exceptions and invalid scores are recorded as failures
    with score zero rather than silently omitted from the aggregate.
    """
    if not baseline_name.strip() or not candidate_name.strip() or baseline_name == candidate_name:
        raise ValueError("baseline and candidate require distinct non-empty names")
    normalized_seeds = [int(seed) for seed in seeds]
    if not normalized_seeds or len(normalized_seeds) != len(set(normalized_seeds)):
        raise ValueError("seeds must be non-empty and unique")
    baseline_metadata = dict(baseline_metadata or {})
    candidate_metadata = dict(candidate_metadata or {})
    json.dumps(baseline_metadata, sort_keys=True, allow_nan=False)
    json.dumps(candidate_metadata, sort_keys=True, allow_nan=False)

    baseline_rows, candidate_rows = await asyncio.gather(
        _evaluate(suite, baseline_name, baseline, normalized_seeds),
        _evaluate(suite, candidate_name, candidate, normalized_seeds),
    )
    pairs = []
    for b_row, c_row in zip(baseline_rows, candidate_rows):
        delta = round(c_row["score"] - b_row["score"], 8)
        pairs.append({
            "case_id": b_row["case_id"],
            "seed": b_row["seed"],
            "baseline_score": b_row["score"],
            "candidate_score": c_row["score"],
            "delta": delta,
            "baseline_error": b_row["error"],
            "candidate_error": c_row["error"],
        })
    deltas = [float(row["delta"]) for row in pairs]
    paired_rows = [{**row, "score": row["delta"]} for row in pairs]
    paired = {
        "mean_delta": round(statistics.fmean(deltas), 8),
        "delta_ci95_bootstrap": _paired_cluster_ci(paired_rows, "score", seed=bootstrap_seed),
        "candidate_wins": sum(1 for value in deltas if value > 0),
        "ties": sum(1 for value in deltas if value == 0),
        "candidate_losses": sum(1 for value in deltas if value < 0),
        "n_pairs": len(pairs),
    }
    try:
        from eci.version import __version__
    except Exception:  # noqa: BLE001
        __version__ = "unknown"
    baseline_report = _summary(baseline_name, baseline_rows, bootstrap_seed)
    candidate_report = _summary(candidate_name, candidate_rows, bootstrap_seed + 1)
    baseline_report["metadata"] = baseline_metadata
    candidate_report["metadata"] = candidate_metadata
    report = BenchmarkComparison(
        suite={"name": suite.name, "version": suite.version,
               "scorer_id": suite.scorer_id, "metric_name": suite.metric_name,
               "scorer_config": dict(suite.scorer_config),
               "sha256": suite.fingerprint()},
        seeds=normalized_seeds,
        baseline=baseline_report,
        candidate=candidate_report,
        paired=paired,
        observations=pairs,
        environment={"eci_version": __version__, "python": sys.version.split()[0],
                     "platform": platform.platform()},
    )
    if bus is not None:
        try:
            from eci.kernel.bus import Event

            bus.publish(Event(
                type="benchmark.comparison.completed", source="benchmark.compare",
                payload={"suite": suite.name, "suite_version": suite.version,
                         "suite_sha256": suite.fingerprint(),
                         "baseline": baseline_name, "candidate": candidate_name,
                         "mean_delta": paired["mean_delta"], "n_pairs": paired["n_pairs"]},
            ))
        except Exception:  # noqa: BLE001
            pass
    return report


def compare(suite: BenchmarkSuite, baseline_name: str, baseline: Candidate,
            candidate_name: str, candidate: Candidate,
            seeds: Sequence[int] = (0,), bootstrap_seed: int = 0,
            bus: Any = None,
            baseline_metadata: dict[str, Any] | None = None,
            candidate_metadata: dict[str, Any] | None = None) -> BenchmarkComparison:
    """Synchronous wrapper around :func:`compare_async` for scripts and CLI tools."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(compare_async(suite, baseline_name, baseline, candidate_name,
                                         candidate, seeds, bootstrap_seed, bus,
                                         baseline_metadata, candidate_metadata))
    raise RuntimeError("compare() cannot run inside an event loop; use await compare_async()")
