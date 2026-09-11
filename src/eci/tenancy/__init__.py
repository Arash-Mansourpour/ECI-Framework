"""Multi-tenancy: namespaces with quotas, isolation and usage accounting.

Tenants isolate ledgers, topics, plugins and budgets. Quotas are enforced
at admission (actions consume budget via economy costs); usage is metered
for the /metrics surface and DAO settlement.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

__all__ = ["Quota", "Namespace", "TenancyManager"]


@dataclass
class Quota:
    actions_per_epoch: int = 10_000
    bytes_per_epoch: int = 100_000_000
    plugins_max: int = 16


@dataclass
class Namespace:
    id: str
    quota: Quota = field(default_factory=Quota)
    used_actions: int = 0
    used_bytes: int = 0
    members: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def admit(self, actions: int = 1, nbytes: int = 0) -> bool:
        if self.used_actions + actions > self.quota.actions_per_epoch:
            return False
        if self.used_bytes + nbytes > self.quota.bytes_per_epoch:
            return False
        self.used_actions += actions
        self.used_bytes += nbytes
        return True

    def reset_epoch(self) -> None:
        self.used_actions = 0
        self.used_bytes = 0


class TenancyManager:
    name = "tenancy"

    def __init__(self) -> None:
        self._ns: dict[str, Namespace] = {}
        self.create("default")

    def create(self, ns_id: str, quota: Quota | None = None) -> Namespace:
        if ns_id in self._ns:
            raise KeyError(f"namespace {ns_id!r} exists")
        ns = Namespace(id=ns_id, quota=quota or Quota())
        self._ns[ns_id] = ns
        return ns

    def get(self, ns_id: str) -> Namespace:
        return self._ns[ns_id]

    def admit(self, ns_id: str, actions: int = 1, nbytes: int = 0) -> bool:
        return self._ns[ns_id].admit(actions, nbytes)

    def start(self) -> None: ...
    def stop(self) -> None: ...
    def health(self) -> dict[str, Any]:
        return {"ok": True, "namespaces": sorted(self._ns),
                "usage": {k: {"actions": v.used_actions, "bytes": v.used_bytes} for k, v in self._ns.items()}}
