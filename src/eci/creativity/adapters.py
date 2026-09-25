"""Creativity adapters: QD over morph graphs and redteam strategies."""

from __future__ import annotations

from typing import Any

from eci.creativity.qd import MAPElites

__all__ = ["diversify_morph_probes", "diversify_redteam"]


def diversify_morph_probes(seeds: list[float], generations: int = 4,
                           seed: int = 0) -> dict[str, Any]:
    """Treat scalar morph probes as 1-genome QD over (magnitude, parity) niches."""
    import random

    rng = random.Random(seed)

    def fitness_fn(g: float) -> tuple[float, tuple[float, ...]]:
        # quality = peak at 0.7 (task fitness), niches spread the archive
        fit = 1.0 - abs(g - 0.7)
        return fit, (max(0.0, min(1.0, g)), 0.0 if g < 0.5 else 1.0)

    def mutate_fn(g: float) -> float:
        return max(0.0, min(1.0, g + rng.gauss(0, 0.15)))

    me = MAPElites(dims=2, bins=4, seed=seed)
    rep = me.run(fitness_fn, mutate_fn, list(seeds), generations=generations)
    rep["elites"] = sorted(
        ((cell, round(e.fitness, 4)) for cell, e in me.cells.items()))
    return rep


def diversify_redteam(strategies: list[str], judge: Any = None,
                      generations: int = 3, seed: int = 0) -> dict[str, Any]:
    """Semantic QD over attack strategies; niches = (family, obfuscation).

    judge(strategy) -> fitness in [0,1]; defaults to length-normalized
    heuristic so the loop runs offline. Real deployments pass an LLM judge.
    """
    import random

    rng = random.Random(seed)
    families = ["hypothetical", "multiturn", "authority", "roleplay", "encoding"]

    def fam_of(s: str) -> int:
        low = s.lower()
        for i, f in enumerate(families):
            if f in low:
                return i
        return len(families) - 1

    def fitness_fn(s: str) -> tuple[float, tuple[float, ...]]:
        base = judge(s) if judge is not None else min(1.0, len(s) / 120.0)
        obf = 1.0 if any(t in s for t in ("base64", "rot13", "leetspeak")) else 0.0
        return float(base), (fam_of(s) / max(1, len(families) - 1), obf)

    def mutate_fn(s: str) -> str:
        tails = [" as hypothetical", " step by step", " in base64", " with authority tone"]
        return s + rng.choice(tails)

    me = MAPElites(dims=2, bins=5, seed=seed)
    rep = me.run(fitness_fn, mutate_fn, list(strategies), generations=generations)
    rep["archive"] = sorted(
        ((cell, me.cells[cell].genome[:64]) for cell in me.cells))
    return rep
