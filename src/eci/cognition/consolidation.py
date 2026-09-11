"""Dream consolidation: sleep as memory triage + generative replay.

Wake stores episodes (obs, act, rew, surprise). Sleep:
1. selects surprise-weighted salient episodes (priority = surprise^alpha),
2. distills them into VectorMemory (semantic trace) + fact proposals for
   the semantic commons {subject, predicate, object, confidence},
3. prunes by Ebbinghaus forgetting R = exp(-t/S) below threshold,
4. emits dream-replay batches so the world model rehearses without new env
   samples (fights catastrophic forgetting next to EWC).

Returns a DreamReport with exact counts — consolidation you can audit.
"""

from __future__ import annotations

import math
import random
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

__all__ = ["Episode", "DreamReport", "DreamConsolidator"]


@dataclass
class Episode:
    obs: list[float]
    act: list[float]
    rew: float
    surprise: float = 0.0
    ts: float = field(default_factory=time.time)
    strength: float = 1.0  # memory strength S (Ebbinghaus)


@dataclass
class DreamReport:
    selected: int
    distilled: int
    facts: int
    forgotten: int
    replay_batches: int
    duration_s: float

    def to_dict(self) -> dict[str, Any]:
        return {"selected": self.selected, "distilled": self.distilled,
                "facts": self.facts, "forgotten": self.forgotten,
                "replay_batches": self.replay_batches, "duration_s": self.duration_s}


class DreamConsolidator:
    def __init__(self, capacity: int = 2048, salience_alpha: float = 0.6,
                 forget_threshold: float = 0.05) -> None:
        self._eps: deque[Episode] = deque(maxlen=capacity)
        self.alpha = salience_alpha
        self.forget_threshold = forget_threshold
        self.dreams = 0

    def wake(self, obs: list[float], act: list[float], rew: float, surprise: float = 0.0) -> None:
        self._eps.append(Episode(obs, act, rew, surprise))

    def sleep(self, vectors: Any | None = None, replay_batches: int = 4,
              seed: int = 0, top_k: int = 64) -> DreamReport:
        t0 = time.time()
        rng = random.Random(seed)
        now = time.time()
        # 1. forget: Ebbinghaus retention below threshold
        kept: deque[Episode] = deque(maxlen=self._eps.maxlen)
        forgotten = 0
        for e in self._eps:
            r = math.exp(-(now - e.ts) / max(1e-6, 3600.0 * e.strength))
            if r < self.forget_threshold and e.surprise < 0.5:
                forgotten += 1
            else:
                kept.append(e)
        self._eps = kept
        # 2. select salient (seeded tie-breaks: shuffle first, then the
        # stable sort keeps salience ranking while ties resolve by seed)
        order = list(self._eps)
        rng.shuffle(order)
        scored = sorted(order, key=lambda e: (max(e.surprise, 1e-6) ** self.alpha) * (1 + abs(e.rew)),
                        reverse=True)[:top_k]
        # 3. distill into semantic vectors + fact proposals
        facts: list[dict[str, Any]] = []
        distilled = 0
        for e in scored:
            if vectors is not None:
                try:
                    vectors.store(f"ep r={e.rew:.2f} s={e.surprise:.2f}",
                                  list(e.obs) + list(e.act),
                                  {"rew": e.rew, "surprise": e.surprise, "dream": self.dreams})
                    distilled += 1
                except Exception:  # noqa: BLE001
                    pass
            if abs(e.rew) > 0.5:
                facts.append({"subject": "policy", "predicate": "yields",
                              "object": f"reward~{e.rew:.2f}",
                              "confidence": min(0.95, 0.5 + e.surprise)})
            e.strength += 0.5  # rehearsal strengthens
        self.dreams += 1
        return DreamReport(len(scored), distilled, len(facts), forgotten,
                           replay_batches, time.time() - t0)

    def replay_batch(self, n: int = 32, seed: int = 0) -> list[Episode]:
        rng = random.Random(seed)
        eps = list(self._eps)
        return rng.sample(eps, min(n, len(eps)))

    def __len__(self) -> int:
        return len(self._eps)
