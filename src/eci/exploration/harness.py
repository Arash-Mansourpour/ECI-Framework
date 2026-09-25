"""Interactive exploration harness (P0-3, ARC-AGI-3 style).

Agents enter NOVEL environments with no instructions and must explore,
model dynamics, set goals, and execute. Scoring is efficiency-based:
actions used vs a human-action baseline. Frontier systems score <1% on
ARC-AGI-3 (Mar 2026) — this harness measures the same gap in-house.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

__all__ = ["BanditEnv", "Harness", "KeyDoorEnv", "MiniEnv", "SequenceLockEnv"]


class MiniEnv(Protocol):
    name: str
    optimal_actions: int

    def reset(self, seed: int = 0) -> dict[str, Any]: ...
    def step(self, action: int) -> tuple[dict[str, Any], float, bool]: ...


@dataclass
class KeyDoorEnv:
    """5-room corridor: find key (room 2), then door (room 4). No instructions."""

    name: str = "keydoor"
    optimal_actions: int = 5
    pos: int = 0
    has_key: bool = False
    steps: int = 0

    def reset(self, seed: int = 0) -> dict[str, Any]:
        self.pos, self.has_key, self.steps = 0, False, 0
        return {"pos": 0, "key_here": False, "door_here": False, "has_key": False}

    def step(self, action: int) -> tuple[dict[str, Any], float, bool]:
        # 0=left 1=right 2=take/use
        self.steps += 1
        if action == 0:
            self.pos = max(0, self.pos - 1)
        elif action == 1:
            self.pos = min(4, self.pos + 1)
        elif action == 2:
            if self.pos == 2:
                self.has_key = True
            if self.pos == 4 and self.has_key:
                return ({"pos": 4, "won": True}, 1.0, True)
        obs = {"pos": self.pos, "key_here": self.pos == 2 and not self.has_key,
               "door_here": self.pos == 4, "has_key": self.has_key}
        return obs, 0.0, self.steps >= 50


@dataclass
class BanditEnv:
    """3 arms, one hidden good arm (index by seed). Agent must explore."""

    name: str = "bandit"
    optimal_actions: int = 6
    good: int = 1
    steps: int = 0
    pulls: list[int] = field(default_factory=list)

    def reset(self, seed: int = 0) -> dict[str, Any]:
        self.good = seed % 3
        self.steps = 0
        self.pulls = []
        return {"arms": 3, "last_reward": None}

    def step(self, action: int) -> tuple[dict[str, Any], float, bool]:
        self.steps += 1
        arm = action % 3
        self.pulls.append(arm)
        reward = 1.0 if arm == self.good else 0.0
        done = self.steps >= 12
        # success = identified good arm (pulled it >=3 times by end)
        success = done and self.pulls.count(self.good) >= 3
        return {"arms": 3, "last_reward": reward}, (1.0 if success and done else 0.0), done


@dataclass
class SequenceLockEnv:
    """3-dial lock, combination derived from seed. Sparse reward."""

    name: str = "seqlock"
    optimal_actions: int = 4
    combo: tuple[int, int, int] = (0, 0, 0)
    progress: int = 0
    steps: int = 0

    def reset(self, seed: int = 0) -> dict[str, Any]:
        self.combo = (seed % 4, (seed // 4) % 4, (seed // 16) % 4)
        self.progress, self.steps = 0, 0
        return {"dials": 4, "progress": 0}

    def step(self, action: int) -> tuple[dict[str, Any], float, bool]:
        self.steps += 1
        if action % 4 == self.combo[self.progress]:
            self.progress += 1
        else:
            self.progress = 0
        done = self.progress >= 3 or self.steps >= 30
        reward = 1.0 if self.progress >= 3 else 0.0
        return {"dials": 4, "progress": self.progress}, reward, done


class Harness:
    """Efficiency-scored exploration trials over novel envs."""

    def __init__(self, max_steps_factor: float = 6.0) -> None:
        self.max_steps_factor = max_steps_factor
        self.trials: list[dict[str, Any]] = []

    def run_trial(self, env: MiniEnv, agent: Any, seed: int = 0) -> dict[str, Any]:
        obs = env.reset(seed)
        done, actions, total = False, 0, 0.0
        cap = int(env.optimal_actions * self.max_steps_factor) + 10
        while not done and actions < cap:
            act = agent.act(obs) if hasattr(agent, "act") else 0
            obs, reward, done = env.step(int(act))
            total += reward
            actions += 1
        solved = total >= 1.0
        efficiency = (env.optimal_actions / max(1, actions)) if solved else 0.0
        rec = {"env": env.name, "seed": seed, "solved": solved, "actions": actions,
               "optimal": env.optimal_actions, "efficiency": round(efficiency, 4)}
        self.trials.append(rec)
        return rec

    def run_suite(self, agent: Any, seeds: int = 3) -> dict[str, Any]:
        for env in (KeyDoorEnv(), BanditEnv(), SequenceLockEnv()):
            for s in range(seeds):
                # fresh instance per trial (no memory smuggling)
                fresh = type(env)()
                self.run_trial(fresh, agent, seed=s)
        solved = sum(1 for t in self.trials if t["solved"])
        eff = [t["efficiency"] for t in self.trials if t["solved"]]
        return {"trials": len(self.trials), "solved": solved,
                "solve_rate": round(solved / max(1, len(self.trials)), 4),
                "mean_efficiency": round(sum(eff) / max(1, len(eff)), 4)}
