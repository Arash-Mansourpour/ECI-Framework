"""Byzantine fault-tolerant consensus: PBFT and Weighted BFT.

References
----------
* Castro & Liskov (1999) "Practical Byzantine Fault Tolerance" OSDI.
* WBFT (2025) arXiv:2505.05103 - reputation-weighted consensus for
  multi-agent networks (paper section 2.4.1).

The fault model is *deterministic and seedable*: each (sequence, node) pair
is mapped through a keyed hash to a reproducible fault decision, so
experiments are auditable and repeatable - unlike the legacy implementation
which rolled a fresh random number on every call.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from eci.constants import PBFT_QUORUM_FRACTION, WBFT_QUORUM_WEIGHT
from eci.core.identity import ARCHITECT
from eci.core.types import ConsensusOutcome, NetworkNode
from eci.logging import get_logger

__all__ = ["ConsensusResult", "PBFTConsensus", "WBFTConsensus"]


@dataclass
class ConsensusResult:
    """Outcome of a consensus round."""

    achieved: bool
    outcome: ConsensusOutcome
    proposal_hash: str
    view: int
    sequence: int
    votes: List[str] = field(default_factory=list)
    quorum: float = 0.0
    required: float = 0.0
    reason: str = ""
    architect_stamp: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = self.__dict__.copy()
        d["outcome"] = self.outcome.value
        return d


def _proposal_digest(proposal: Any) -> str:
    return hashlib.sha256(
        json.dumps(proposal, sort_keys=True, default=str, separators=(",", ":")).encode()
    ).hexdigest()


class PBFTConsensus:
    """Three-phase PBFT with a persistent, seedable fault model.

    ``byzantine_mode``: ``"random"`` (hash-rate faults), ``"silent"``
    (lowest-trust f nodes always faulty), ``"equivocate"`` (faulty nodes
    send conflicting votes that cancel: they count in prepare but not in
    commit, modelling split-brain equivocation).
    """

    def __init__(
        self,
        n_nodes: int,
        f_tolerance: Optional[int] = None,
        byzantine_rate: float = 0.05,
        consensus_seed: int = 7,
        min_trust: float = 0.5,
        byzantine_mode: str = "random",
    ) -> None:
        self.n_nodes = n_nodes
        self.f = f_tolerance if f_tolerance is not None else (n_nodes - 1) // 3
        if n_nodes < 3 * self.f + 1:
            raise ValueError(
                f"need at least {3 * self.f + 1} nodes for f={self.f} tolerance, got {n_nodes}"
            )
        if not (0.0 <= byzantine_rate <= 1.0):
            raise ValueError("byzantine_rate must be in [0, 1]")
        if byzantine_mode not in ("random", "silent", "equivocate"):
            raise ValueError(f"unknown byzantine_mode: {byzantine_mode}")
        self.byzantine_rate = byzantine_rate
        self.byzantine_mode = byzantine_mode
        self.consensus_seed = consensus_seed
        self.min_trust = min_trust
        self.logger = get_logger("network.consensus")

        self.view_number = 0
        self.sequence_number = 0
        self.message_log: Dict[str, List[Dict[str, Any]]] = {}
        self._msg_cap = 4096

    # ------------------------------------------------------------------
    def update_topology(self, n_nodes: int) -> None:
        """Re-derive the fault bound after membership changes (state kept)."""
        self.n_nodes = n_nodes
        new_f = (n_nodes - 1) // 3
        if n_nodes < 3 * new_f + 1:
            raise ValueError(f"cannot tolerate any faults with {n_nodes} nodes")
        self.f = new_f

    def _is_faulty(self, sequence: int, node_id: str) -> bool:
        """Deterministic, keyed fault decision per (sequence, node)."""
        payload = f"{self.consensus_seed}|{sequence}|{node_id}".encode()
        digest = hashlib.sha256(payload).digest()
        value = int.from_bytes(digest[:8], "big") / 2 ** 64
        return value < self.byzantine_rate

    def _primary(self, node_ids: Sequence[str]) -> str:
        ordered = sorted(node_ids)
        return ordered[self.view_number % len(ordered)]

    def _fault_set(self, nodes: Dict[str, NetworkNode]) -> set:
        if self.byzantine_mode == "silent":
            ordered = sorted(nodes.items(), key=lambda kv: kv[1].trust_score)
            return {nid for nid, _ in ordered[: self.f]}
        return {
            nid for nid in nodes
            if self._is_faulty(self.sequence_number, nid)
        }

    # ------------------------------------------------------------------
    def achieve_consensus(
        self,
        nodes: Dict[str, NetworkNode],
        proposal: Any,
    ) -> ConsensusResult:
        """Run pre-prepare / prepare / commit for ``proposal``."""
        if not nodes:
            return ConsensusResult(
                achieved=False, outcome=ConsensusOutcome.NOT_INITIALIZED,
                proposal_hash=_proposal_digest(proposal), view=self.view_number,
                sequence=self.sequence_number, reason="no nodes registered",
            )

        digest = _proposal_digest(proposal)
        primary = self._primary(list(nodes.keys()))
        quorum = 2 * self.f + 1
        faults = self._fault_set(nodes)

        prepare_votes: List[str] = []
        commit_votes: List[str] = []
        for node_id, node in sorted(nodes.items()):
            faulty = (node_id in faults) or node.trust_score < self.min_trust
            # Prepare phase: honest nodes validate and vote
            if not faulty:
                prepare_votes.append(node_id)
                commit_votes.append(node_id)
            elif self.byzantine_mode == "equivocate":
                # Equivocating nodes vote prepare (split-brain) but their
                # commit conflicts and is discarded — stresses quorum logic.
                prepare_votes.append(node_id)
            self.message_log.setdefault(digest, []).append(
                {
                    "phase": "prepare/commit" if not faulty else ("equivocate" if self.byzantine_mode == "equivocate" else "fault"),
                    "node": node_id,
                    "view": self.view_number,
                    "sequence": self.sequence_number,
                    "timestamp": time.time(),
                }
            )
            if len(self.message_log[digest]) > self._msg_cap:
                del self.message_log[digest][: len(self.message_log[digest]) - self._msg_cap]

        prepared = len(prepare_votes) >= quorum
        committed = len(commit_votes) >= quorum
        achieved = prepared and committed
        result = ConsensusResult(
            achieved=achieved,
            outcome=ConsensusOutcome.ACHIEVED if achieved else ConsensusOutcome.REJECTED,
            proposal_hash=digest,
            view=self.view_number,
            sequence=self.sequence_number,
            votes=commit_votes if achieved else prepare_votes,
            quorum=len(commit_votes),
            required=quorum,
            reason="" if achieved else "insufficient quorum (Byzantine faults or low trust)",
            architect_stamp=ARCHITECT.stamp(
                {"kind": "consensus", "proposal_hash": digest, "achieved": achieved}
            ),
        )
        if achieved:
            self.sequence_number += 1
        else:
            self.view_number += 1  # view change on failure
        return result


class WBFTConsensus(PBFTConsensus):
    """Weighted BFT: quorum by accumulated weight (reputation * stake).

    Safety holds while the total Byzantine weight stays below 1/3 (paper
    theorem 2.9).
    """

    def node_weight(self, node: NetworkNode) -> float:
        return max(0.0, node.reputation_score) * max(0.0, node.stake)

    def achieve_consensus(
        self,
        nodes: Dict[str, NetworkNode],
        proposal: Any,
    ) -> ConsensusResult:
        if not nodes:
            return ConsensusResult(
                achieved=False, outcome=ConsensusOutcome.NOT_INITIALIZED,
                proposal_hash=_proposal_digest(proposal), view=self.view_number,
                sequence=self.sequence_number, reason="no nodes registered",
            )
        digest = _proposal_digest(proposal)
        quorum = 2 * self.f + 1

        total_weight = sum(self.node_weight(n) for n in nodes.values())
        commit_weight = 0.0
        commit_nodes: List[str] = []
        for node_id, node in sorted(nodes.items()):
            faulty = self._is_faulty(self.sequence_number, node_id) or node.trust_score < self.min_trust
            if not faulty:
                commit_weight += self.node_weight(node)
                commit_nodes.append(node_id)
            self.message_log.setdefault(digest, []).append(
                {
                    "phase": "prepare/commit" if not faulty else "fault",
                    "node": node_id,
                    "weight": self.node_weight(node),
                    "sequence": self.sequence_number,
                    "timestamp": time.time(),
                }
            )

        achieved = (
            commit_weight > WBFT_QUORUM_WEIGHT * total_weight
            and len(commit_nodes) >= quorum
        )
        result = ConsensusResult(
            achieved=achieved,
            outcome=ConsensusOutcome.ACHIEVED if achieved else ConsensusOutcome.REJECTED,
            proposal_hash=digest,
            view=self.view_number,
            sequence=self.sequence_number,
            votes=commit_nodes,
            quorum=commit_weight,
            required=WBFT_QUORUM_WEIGHT * total_weight,
            reason="" if achieved else "weighted quorum not reached",
            architect_stamp=ARCHITECT.stamp(
                {"kind": "wbft_consensus", "proposal_hash": digest, "achieved": achieved}
            ),
        )
        if achieved:
            self.sequence_number += 1
        else:
            self.view_number += 1
        return result
