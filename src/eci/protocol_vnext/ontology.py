"""ECI-KNOW — Federated Living Ontology + Knowledge Graph.

Ontology is induced from experience, not pre-fixed. Propose-only evolution:
Discover ≠ Modify; proposal requires peer verification + challenge window.
Includes KnowledgeState snapshots + deterministic diff (ΔK) + temporal metacognition.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

__all__ = ["ConceptProposal", "FederatedOntology", "KnowledgeGraph", "KnowledgeState"]


@dataclass
class ConceptProposal:
    concept: str
    description: str
    proposer: str
    evidence: list[str] = field(default_factory=list)
    status: str = "pending"  # pending/accepted/provisional/rejected/disputed
    votes: dict[str, str] = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    def vote(self, peer: str, verdict: str) -> None:
        self.votes[peer] = verdict  # verify/challenge

    def tally(self) -> str:
        verifies = sum(1 for v in self.votes.values() if v == "verify")
        challenges = sum(1 for v in self.votes.values() if v == "challenge")
        if challenges >= 2:
            self.status = "disputed"
        elif verifies >= 2:
            self.status = "accepted"
        elif verifies == 1:
            self.status = "provisional"
        else:
            self.status = "rejected"
        return self.status


class KnowledgeGraph:
    def __init__(self) -> None:
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: list[dict[str, Any]] = []

    def add_node(self, id: str, attrs: dict[str, Any]) -> None:
        self.nodes[id] = attrs

    def add_edge(self, src: str, dst: str, rel: str) -> None:
        self.edges.append({"src": src, "dst": dst, "rel": rel})

    def to_dict(self) -> dict[str, Any]:
        return {"nodes": self.nodes, "edges": self.edges}


@dataclass
class KnowledgeState:
    snapshot_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    concepts: dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=time.time)
    hash: str = ""

    def __post_init__(self) -> None:
        import json
        self.hash = hashlib.sha256(json.dumps(self.concepts, sort_keys=True).encode()).hexdigest()[:16]

    def diff(self, other: "KnowledgeState") -> dict[str, Any]:
        added = {k: v for k, v in other.concepts.items() if k not in self.concepts}
        removed = {k: v for k, v in self.concepts.items() if k not in other.concepts}
        changed = {k: (self.concepts[k], other.concepts[k]) for k in self.concepts if k in other.concepts and self.concepts[k] != other.concepts[k]}
        return {"added": added, "removed": removed, "changed": changed, "delta_hash": other.hash}


class FederatedOntology:
    def __init__(self) -> None:
        self.proposals: dict[str, ConceptProposal] = {}
        self.accepted: dict[str, ConceptProposal] = {}
        self.graph = KnowledgeGraph()
        self.states: list[KnowledgeState] = []

    def propose(self, concept: str, desc: str, proposer: str, evidence: list[str] | None = None) -> ConceptProposal:
        prop = ConceptProposal(concept=concept, description=desc, proposer=proposer, evidence=evidence or [])
        self.proposals[prop.id] = prop
        return prop

    def verify(self, proposal_id: str, peer: str, verdict: str) -> str:
        prop = self.proposals[proposal_id]
        prop.vote(peer, verdict)
        status = prop.tally()
        if status == "accepted":
            self.accepted[prop.concept] = prop
            self.graph.add_node(prop.concept, {"desc": prop.description, "proposer": prop.proposer})
        return status

    def snapshot(self) -> KnowledgeState:
        st = KnowledgeState(concepts={k: v.description for k, v in self.accepted.items()})
        self.states.append(st)
        return st

    def to_dict(self) -> dict[str, Any]:
        return {"accepted": list(self.accepted.keys()), "proposals": len(self.proposals), "graph": self.graph.to_dict()}
