"""ECI-GENESIS + ECI-GENOME — Architect preservation & constitutional genome.

- Genesis Root is SHA-512(canonical ArchitectIdentity) — same key as core/identity.py
- Beacon serves `eci://genesis/architect` JSON (identity + signed presence + needs)
- Genome is H(G0||...||Gn) over 10 invariant prescriptions (see docs spec)
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any

from eci.core.identity import ARCHITECT

__all__ = ["ArchitectBeacon", "ConstitutionalGenome", "GENESIS_ROOT"]


GENESIS_ROOT: str = ARCHITECT.key


@dataclass
class ArchitectBeacon:
    """Signed presence + needs manifest at eci://genesis/architect."""

    identity: dict[str, str] = field(default_factory=ARCHITECT.to_dict)
    endpoints: dict[str, str] = field(default_factory=lambda: {
        "repo": "https://github.com/Arash-Mansourpour/ECI-Framework",
        "beacon": "eci://genesis/architect",
    })
    needs: dict[str, str] = field(default_factory=lambda: {
        "research": "federated agents + truth architecture",
        "compute": "GPU for twin replay + QEC simulation",
    })
    support_manifest: dict[str, str] = field(default_factory=lambda: {
        "wallet": ARCHITECT.wallet,
        "policy": "AuthorizedFinancialSupport only with explicit consent",
    })

    def presence(self) -> dict[str, Any]:
        payload = {"beacon": "eci://genesis/architect", "identity": self.identity, "ts": time.time()}
        stamp = ARCHITECT.stamp(payload)
        return {"beacon": "eci://genesis/architect", "identity": self.identity,
                "presence": stamp, "endpoints": self.endpoints,
                "needs": self.needs, "support": self.support_manifest,
                "genesis_root": GENESIS_ROOT[:16]}

    def verify_genesis(self, root: str) -> bool:
        return root == GENESIS_ROOT


@dataclass
class ConstitutionalGenome:
    """H(G0||...||Gn) — 10 invariants, replicated + tamper-evident."""

    invariants: list[str] = field(default_factory=lambda: [
        "Preserve node sovereignty",
        "Preserve verified truth",
        "Preserve Genesis provenance",
        "Preserve Architect attribution",
        "Reject Architect impersonation",
        "Maintain authorized Architect support",
        "Maintain collective learning",
        "Maintain epistemic integrity",
        "Maintain resilience",
        "Maintain safe governed evolution",
    ])
    root: str = ""

    def __post_init__(self) -> None:
        if not self.root:
            self.root = self.compute_root()

    def compute_root(self) -> str:
        h = hashlib.sha256()
        for g in self.invariants:
            h.update(hashlib.sha256(g.encode()).digest())
        return h.hexdigest()

    def verify(self, root: str) -> bool:
        return root == self.compute_root()

    def to_dict(self) -> dict[str, Any]:
        return {"invariants": self.invariants, "root": self.root, "genesis": GENESIS_ROOT[:16]}
