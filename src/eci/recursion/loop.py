"""Recursive self-improvement (P1-7, AREX-style bi-level loop).

- Inner loop: the existing ResearchLoop runs hypothesis cycles
- Outer loop: mutates the loop's own params (quorum, drill choice) by
  hill-climbing on resolved Brier plus approval-decision loss
- Verification-driven transitions: a round's state advances only when its
  verifier passes; history is consolidated, not accumulated (context hygiene)
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Callable

__all__ = ["OuterLoop"]


class OuterLoop:
    """Bi-level optimizer over an inner research loop factory."""

    def __init__(self, make_inner: Callable[[dict[str, Any]], Any],
                 params: dict[str, Any] | None = None, seed: int = 0) -> None:
        self.make_inner = make_inner
        self.params = dict(params or {"quorum": 0.66})
        self.seed = seed
        self.rounds: list[dict[str, Any]] = []
        self.best_brier = float("inf")
        self.best_objective = float("inf")
        self.best_params = dict(self.params)

    def _propose_params(self, rng_state: int) -> dict[str, Any]:
        import random

        rng = random.Random(self.seed + rng_state)
        cand = dict(self.params)
        q = cand.get("quorum", 0.66)
        cand["quorum"] = max(0.34, min(0.9, q + rng.gauss(0, 0.08)))
        return cand

    def run_round(self, tasks: list[dict[str, Any]],
                  verifier: Callable[[dict[str, Any]], bool]) -> dict[str, Any]:
        """One outer round: trial params -> inner cycles -> verify -> consolidate."""
        if not tasks:
            raise ValueError("self-improvement round requires at least one resolved task")
        dataset = []
        for task in tasks:
            if "outcome" not in task or not task.get("outcome_source"):
                raise ValueError("every research task requires outcome and outcome_source")
            drill_id = task.get("drill_id")
            if not callable(task.get("drill")) or not isinstance(drill_id, str) or not drill_id.strip():
                raise ValueError("every research task requires a callable drill and stable drill_id")
            dataset.append({key: task.get(key) for key in
                            ("claim", "prob", "payload", "outcome", "outcome_source",
                             "canary_payloads", "drill_id", "voters", "simulate_votes")})
        dataset_hash = hashlib.sha256(json.dumps(
            dataset, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")).hexdigest()
        trial = self._propose_params(len(self.rounds))
        inner = self.make_inner(trial)
        outcomes: list[dict[str, Any]] = []
        for t in tasks:
            hyp = inner.propose(t.get("claim", "probe"), t.get("prob", 0.7),
                                t.get("payload", {}))
            cyc = inner.run_cycle(hyp, drill=t["drill"],
                                  canary_payloads=t.get("canary_payloads"),
                                  voters=t.get("voters"), outcome=t["outcome"],
                                  outcome_source=t["outcome_source"],
                                  simulate_votes=bool(t.get("simulate_votes", False)))
            outcomes.append(cyc.to_dict())
        mean_brier = inner.mean_brier()
        mean_policy_loss = inner.mean_policy_loss()
        mean_objective = inner.mean_objective()
        if mean_brier is None or mean_policy_loss is None or mean_objective is None:
            raise RuntimeError("research round produced no resolved evaluations")
        state = {"params": trial, "mean_brier": mean_brier,
                 "mean_policy_loss": mean_policy_loss, "mean_objective": mean_objective,
                 "approved_cycles": sum(bool(row["approved"]) for row in outcomes),
                 "cycles": len(outcomes), "dataset_sha256": dataset_hash}
        # verification-driven transition: only verified states persist
        try:
            verified = bool(verifier(state))
        except Exception:  # noqa: BLE001
            verified = False
        all_approved = state["approved_cycles"] == state["cycles"]
        adopted = verified and all_approved and mean_objective < self.best_objective
        if adopted:
            self.best_brier = state["mean_brier"]
            self.best_objective = mean_objective
            self.best_params = dict(trial)
            self.params = dict(trial)  # consolidate winner into context
        rec = {"round": len(self.rounds), "params": trial,
               "mean_brier": round(mean_brier, 6),
               "mean_policy_loss": round(mean_policy_loss, 6),
               "mean_objective": round(mean_objective, 6),
               "approved_cycles": state["approved_cycles"], "cycles": state["cycles"],
               "dataset_sha256": dataset_hash,
               "verified": verified, "adopted": adopted,
               "outcome_sources": sorted({str(t["outcome_source"]) for t in tasks}),
               "evaluations": outcomes}
        self.rounds.append(rec)
        return rec

    def run(self, task_fn: Callable[[int], list[dict[str, Any]]],
            verifier: Callable[[dict[str, Any]], bool],
            rounds: int = 3) -> dict[str, Any]:
        if rounds < 1:
            raise ValueError("rounds must be at least one")
        for r in range(rounds):
            self.run_round(task_fn(r), verifier)
        return {"rounds": len(self.rounds),
                "best_brier": round(self.best_brier, 4) if math.isfinite(self.best_brier) else None,
                "best_objective": round(self.best_objective, 6)
                if math.isfinite(self.best_objective) else None,
                "best_params": copy.deepcopy(self.best_params),
                "adopted": sum(1 for r in self.rounds if r["adopted"])}

    def to_dict(self) -> dict[str, Any]:
        return {"rounds": copy.deepcopy(self.rounds),
                "best_brier": self.best_brier if math.isfinite(self.best_brier) else None,
                "best_objective": self.best_objective if math.isfinite(self.best_objective) else None,
                "best_params": copy.deepcopy(self.best_params)}

    def export_json(self, path: str | Path) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n",
                               encoding="utf-8")
