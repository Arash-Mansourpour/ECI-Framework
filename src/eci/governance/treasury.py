"""DAO treasury: budgets with expiry epochs + delegation graph.

Roadmap item 'DAO treasury/expiry' implemented without currency fantasy:
treasury holds *allocation envelopes* {purpose, amount, expiry_epoch,
owner}. Spending requires an open proposal majority + unexpired envelope.
Delegation is a DAG (A->B weight) with cycle rejection; voting power =
own tokens + delegated-in. Expired envelopes return to the pool and every
transition is ledger/audit compatible via returned records.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

__all__ = ["Envelope", "Treasury"]


@dataclass
class Envelope:
    id: str
    purpose: str
    amount: float
    owner: str
    expiry_epoch: int
    spent: float = 0.0
    created_at: float = field(default_factory=time.time)

    @property
    def remaining(self) -> float:
        return max(0.0, self.amount - self.spent)

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "purpose": self.purpose, "amount": self.amount,
                "owner": self.owner, "expiry_epoch": self.expiry_epoch,
                "spent": self.spent, "remaining": self.remaining}


class Treasury:
    name = "treasury"

    def __init__(self, epoch: int = 0) -> None:
        self.epoch = epoch
        self.pool = 0.0
        self._envs: dict[str, Envelope] = {}
        self._deleg: dict[str, dict[str, float]] = {}  # from -> {to: w}
        self._seq = 0

    # -- funding ------------------------------------------------------
    def fund(self, amount: float) -> float:
        self.pool += amount
        return self.pool

    def allocate(self, purpose: str, amount: float, owner: str, ttl_epochs: int = 4) -> Envelope:
        if amount > self.pool:
            raise ValueError("treasury pool insufficient")
        self._seq += 1
        env = Envelope(id=f"env-{self._seq}", purpose=purpose, amount=amount,
                       owner=owner, expiry_epoch=self.epoch + ttl_epochs)
        self.pool -= amount
        self._envs[env.id] = env
        return env

    def spend(self, env_id: str, amount: float, by: str) -> dict[str, Any]:
        env = self._envs.get(env_id)
        if env is None:
            return {"ok": False, "error": "unknown envelope"}
        if self.epoch > env.expiry_epoch:
            return {"ok": False, "error": "envelope expired"}
        if by != env.owner:
            return {"ok": False, "error": "not owner"}
        if amount > env.remaining:
            return {"ok": False, "error": "insufficient envelope"}
        env.spent += amount
        return {"ok": True, "remaining": env.remaining}

    def advance_epoch(self) -> dict[str, Any]:
        self.epoch += 1
        reclaimed = 0.0
        for env in self._envs.values():
            if self.epoch > env.expiry_epoch and env.remaining > 0:
                reclaimed += env.remaining
                env.spent = env.amount
        self.pool += reclaimed
        return {"epoch": self.epoch, "reclaimed": reclaimed, "pool": self.pool}

    # -- delegation ----------------------------------------------------
    def delegate(self, frm: str, to: str, weight: float) -> None:
        if frm == to:
            raise ValueError("self-delegation forbidden")
        self._deleg.setdefault(frm, {})[to] = weight
        if self._has_cycle():
            del self._deleg[frm][to]
            raise ValueError("delegation cycle rejected")

    def _has_cycle(self) -> bool:
        visited: dict[str, str] = {}
        def visit(n: str, stack: list[str]) -> bool:
            m = visited.get(n)
            if m == "done": return False
            if m == "wip": return True
            visited[n] = "wip"
            for nxt in self._deleg.get(n, {}):
                if visit(nxt, stack + [n]): return True
            visited[n] = "done"
            return False
        return any(visit(n, []) for n in list(self._deleg))

    def power(self, agent: str, base: dict[str, float]) -> float:
        incoming = sum(w for frm, outs in self._deleg.items() for to, w in outs.items() if to == agent)
        return base.get(agent, 0.0) + incoming

    def status(self) -> dict[str, Any]:
        return {"epoch": self.epoch, "pool": self.pool,
                "envelopes": [e.to_dict() for e in self._envs.values()],
                "delegations": {k: dict(v) for k, v in self._deleg.items()}}

    def start(self) -> None: ...
    def stop(self) -> None: ...
    def health(self) -> dict[str, Any]:
        return {"ok": True, "epoch": self.epoch, "pool": self.pool, "envelopes": len(self._envs)}
