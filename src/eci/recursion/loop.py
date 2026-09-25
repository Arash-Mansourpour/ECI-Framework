"""Recursive self-improvement (P1-7, AREX-style bi-level loop).

- Inner loop: the existing ResearchLoop runs hypothesis cycles
- Outer loop: mutates the loop's own params (quorum, drill choice) by
  hill-climbing on mean Brier — the system improves its improvement method
- Verification-driven transitions: a round's state advances only when its
  verifier passes; history is consolidated, not accumulated (context hygiene)
"""

from __future__ import annotations

import copy
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
        trial = self._propose_params(len(self.rounds))
        inner = self.make_inner(trial)
        outcomes: list[dict[str, Any]] = []
        for t in tasks:
            hyp = inner.propose(t.get("claim", "probe"), t.get("prob", 0.7),
                                t.get("payload", {}))
            cyc = inner.run_cycle(hyp, drill=t.get("drill", lambda p: 0.5),
                                  voters=t.get("voters"), outcome=t.get("outcome", 1))
            outcomes.append(cyc.to_dict())
        state = {"params": trial, "mean_brier": inner.mean_brier(),
                 "cycles": len(outcomes)}
        # verification-driven transition: only verified states persist
        verified = verifier(state)
        if verified and state["mean_brier"] < self.best_brier:
            self.best_brier = state["mean_brier"]
            self.best_params = dict(trial)
            self.params = dict(trial)  # consolidate winner into context
        rec = {"round": len(self.rounds), "params": trial,
               "mean_brier": round(state["mean_brier"], 4),
               "verified": verified, "adopted": verified and state["mean_brier"] <= self.best_brier}
        self.rounds.append(rec)
        return rec

    def run(self, task_fn: Callable[[int], list[dict[str, Any]]],
            verifier: Callable[[dict[str, Any]], bool],
            rounds: int = 3) -> dict[str, Any]:
        for r in range(rounds):
            self.run_round(task_fn(r), verifier)
        return {"rounds": len(self.rounds), "best_brier": round(self.best_brier, 4),
                "best_params": copy.deepcopy(self.best_params),
                "adopted": sum(1 for r in self.rounds if r["adopted"])}
