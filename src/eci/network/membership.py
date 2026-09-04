"""Dynamic membership: heartbeats, timeout eviction, attested joins.

The mesh survives churn: dead nodes are evicted after `timeout_s` missed
heartbeats, newcomers join only with a valid Protocol-0 attestation, and
the voter set is always derived live (no static config = no single point
of administration). Quorum math reads f from the LIVE set each round.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

__all__ = ["Member", "Membership"]


@dataclass
class Member:
    node_id: str
    last_beat: float = 0.0
    trust: float = 1.0
    stake: float = 1.0


@dataclass
class Membership:
    timeout_s: float = 300.0
    members: Dict[str, Member] = field(default_factory=dict)
    clock: float = 0.0  # injectable for tests; 0 = wall time

    def _now(self) -> float:
        return self.clock if self.clock > 0 else time.time()

    def join(self, node_id: str, attestation_ok: bool, trust: float = 1.0, stake: float = 1.0) -> bool:
        """Admit only attested nodes (Protocol-0 gate at the door)."""
        if not attestation_ok:
            return False
        self.members[node_id] = Member(node_id, self._now(), trust, stake)
        return True

    def beat(self, node_id: str) -> None:
        if node_id in self.members:
            self.members[node_id].last_beat = self._now()

    def sweep(self) -> List[str]:
        """Evict timed-out nodes. Returns evicted ids."""
        now, dead = self._now(), []
        for nid, m in list(self.members.items()):
            if now - m.last_beat > self.timeout_s:
                dead.append(nid)
                del self.members[nid]
        return dead

    def voters(self) -> List[str]:
        self.sweep()
        return sorted(self.members)

    def fault_bound(self) -> int:
        return max(0, (len(self.voters()) - 1) // 3)
