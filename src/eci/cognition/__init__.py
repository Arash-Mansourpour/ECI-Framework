"""Cognition facade: the AGI executive stack in one handle.

Wires world-model imagination + uncertainty-aware planning + curiosity +
dream consolidation + causal inference + autonomous science + theory of
mind + constitutional charter + metacognitive executive. The ``think()``
loop is the flagship: charter-gated, strategy-aware (fast/deliberate/
council), provenance-recorded end-to-end cognition.

    out = cognition.think(goal_vec, obs, budget=...)
    # -> {action, value, system, charter, strategy, provenance_id}
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Sequence

import torch

from eci.cognition.causal import CausalGraph, ate_backdoor, discover
from eci.cognition.charter import DUTIES, Charter
from eci.cognition.consolidation import DreamConsolidator, DreamReport
from eci.cognition.curiosity import CuriosityConfig, IntrinsicMotivation
from eci.cognition.executive import Executive
from eci.cognition.planner import CEMPlanner, PlannerConfig
from eci.cognition.scientist import Hypothesis, Scientist
from eci.cognition.tom import TheoryOfMind
from eci.cognition.world_model import LatentWorldModel, WorldModelConfig

__all__ = ["CognitionConfig", "Cognition", "DUTIES"]


class CognitionConfig:
    def __init__(self, obs_dim: int = 16, act_dim: int = 4, hidden: int = 64,
                 latent: int = 16, horizon: int = 8) -> None:
        self.wm = WorldModelConfig(obs_dim, act_dim, hidden, latent)
        self.plan = PlannerConfig(horizon=horizon)
        self.cur = CuriosityConfig(obs_dim=obs_dim, hidden=hidden)


class Cognition:
    name = "cognition"

    def __init__(self, cfg: CognitionConfig | None = None, bus=None,
                 provenance=None, vectors=None) -> None:
        self.cfg = cfg or CognitionConfig()
        self.world = LatentWorldModel(self.cfg.wm)
        self.planner = CEMPlanner(self.world, self.cfg.plan)
        self.curiosity = IntrinsicMotivation(self.cfg.cur)
        self.dream = DreamConsolidator()
        self.scientist = Scientist()
        self.tom = TheoryOfMind()
        self.charter = Charter()
        self.executive = Executive()
        self.bus = bus
        self.provenance = provenance
        self.vectors = vectors
        self.thinks = 0

    @torch.no_grad()
    def think(self, obs: Sequence[float], goal: str = "act",
              stakes: float = 0.5, action_name: str = "actuate",
              precog_tier: str = "none") -> Dict[str, Any]:
        """One full cognitive beat: charter -> strategy -> imagine+plan -> record."""
        t0 = time.time()
        c = self.cfg.wm
        o = torch.tensor([list(obs)], dtype=torch.float32)
        h = torch.zeros(1, c.hidden)
        z = torch.zeros(1, c.latent)
        # 1. charter gate (duties 0-2 + precog hold are hard stops)
        verdict = self.charter.check(action_name, {"precog_tier": precog_tier})
        if not verdict["allow"]:
            return {"ok": False, "refused": True, **verdict, "system": 0}
        # 2. uncertainty probe -> strategy (System-1/2/council)
        probe = self.world.imagine(h, z, lambda hh, zz: torch.zeros(1, c.act_dim), horizon=2)
        u0 = float(probe["uncertainty"].mean().item())
        strat = self.executive.strategy(stakes, min(1.0, u0 * 10))
        if strat["mode"] == "council":
            esc = self.executive.adjudicate("policy", {"goal": goal, "u0": u0})
            return {"ok": False, "council": True, "strategy": strat, "escalation": esc,
                    "charter": verdict, "system": 3}
        # 3. deliberate: CEM over imagined futures
        plan = self.planner.plan(h, z, seed=self.thinks)
        # 4. curiosity top-up on the live obs
        cur = self.curiosity.bonus(o)
        self.thinks += 1
        out = {"ok": True, "action": plan["action"].squeeze(0).tolist(),
               "value": plan["value"], "system": plan["system"], "u0": u0,
               "strategy": strat, "charter": verdict,
               "curiosity": float(cur["bonus"].mean().item()),
               "duration_s": time.time() - t0}
        # 5. record (best-effort; cognition never fails on bookkeeping)
        try:
            if self.provenance is not None:
                node = self.provenance.record("cognition.think", "cognition",
                                              {"goal": goal, "stakes": stakes},
                                              {"value": out["value"], "system": out["system"]},
                                              {"planner": "CEM", "world": "RSSM-lite"})
                out["provenance_id"] = node.id
            if self.bus is not None:
                from eci.kernel.bus import Event
                self.bus.publish(Event(type="cognition.think.done", source="cognition",
                                       payload={"goal": goal, "system": out["system"]}))
        except Exception:  # noqa: BLE001
            pass
        return out

    def dream_cycle(self, vectors: Any | None = None, seed: int = 0) -> Dict[str, Any]:
        rep = self.dream.sleep(vectors or self.vectors, seed=seed)
        return rep.to_dict()

    def start(self) -> None: ...
    def stop(self) -> None: ...
    def health(self) -> Dict[str, Any]:
        return {"ok": True, "thinks": self.thinks, "dreams": self.dream.dreams,
                "world_steps": self.world.train_steps,
                "executive": self.executive.health(), "charter": self.charter.health()}
