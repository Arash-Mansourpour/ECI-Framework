"""Autonomous network management.

Persistent topology, consciousness-gated joining, PBFT/WBFT consensus,
heartbeat supervision and reputation updates. Unlike the legacy manager,
the consensus engine is never recreated on membership changes (its
``update_topology`` method keeps view/sequence state intact).
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import torch

from eci.config import NetworkConfig
from eci.consciousness.analyzer import AdvancedConsciousnessAnalyzer
from eci.core.identity import ARCHITECT
from eci.core.types import NetworkNode, NetworkRole
from eci.logging import get_logger
from eci.network.consensus import ConsensusResult, PBFTConsensus, WBFTConsensus
from eci.network.nodes import NodeFactory

__all__ = ["AutonomousNetworkManager"]


class AutonomousNetworkManager:
    """Manages the decentralized autonomous AI network."""

    def __init__(
        self,
        config: Optional[NetworkConfig] = None,
        consensus_mode: str = "pbft",
        seed: Optional[int] = None,
    ) -> None:
        if consensus_mode not in ("pbft", "wbft"):
            raise ValueError("consensus_mode must be 'pbft' or 'wbft'")
        self.config = config or NetworkConfig()
        self.consensus_mode = consensus_mode
        self.seed = seed
        self.logger = get_logger("network.manager")
        self.nodes: Dict[str, NetworkNode] = {}
        self.network_state = "initializing"
        self.network_metrics: Dict[str, List[float]] = {}
        self.node_factory = NodeFactory(seed=seed)
        self.consensus_engine: Optional[PBFTConsensus] = None

    # ------------------------------------------------------------------
    async def initialize_network(self) -> Dict[str, Any]:
        """Bootstrap the network with an architect-signed seed node."""
        profile = await self._measure_consciousness(seed=1)
        seed_node = self.node_factory.create_node(
            role=NetworkRole.SEED_NODE,
            capabilities={
                "consciousness_analysis": 1.0,
                "quantum_processing": 1.0,
                "consensus_participation": 1.0,
                "federated_learning": 1.0,
            },
            consciousness_profile=profile,
            trust_score=1.0,
            reputation_score=1.0,
            computational_power=10.0,
            memory_capacity=64.0,
            network_bandwidth=1000.0,
            seed=self.seed if self.seed is not None else 0,
        )
        self.nodes[seed_node.node_id] = seed_node

        self.consensus_engine = self._make_consensus(len(self.nodes))
        self.network_state = "active"
        self.logger.info("network initialized with seed node %s", seed_node.node_id)
        return {
            "network_id": ARCHITECT.derive_id("network", {"seed": seed_node.node_id}),
            "seed_node": seed_node.node_id,
            "creator_verified": True,
            "status": self.network_state,
            "consensus_mode": self.consensus_mode,
            "architect": ARCHITECT.to_dict(),
        }

    def _make_consensus(self, n_nodes: int) -> PBFTConsensus:
        kwargs = {
            "n_nodes": max(1, n_nodes),
            "f_tolerance": 0 if n_nodes == 1 else None,
            "byzantine_rate": self.config.byzantine_rate,
            "consensus_seed": self.config.consensus_seed,
        }
        if self.consensus_mode == "wbft":
            return WBFTConsensus(**kwargs)
        return PBFTConsensus(**kwargs)

    # ------------------------------------------------------------------
    async def _measure_consciousness(self, seed: int = 0, n_neurons: int = 64):
        """Synthetic cognitive activity: shared rhythms + local coupling.

        Pure iid noise has Phi = 0 (correctly); a cognitive agent's
        activity is correlated, so the synthetic generator mixes shared
        oscillations, per-neuron coupling and local noise.
        """
        generator = torch.Generator().manual_seed(seed + (self.seed or 0))
        n_time = 1000
        t = torch.linspace(0, 30, n_time)
        shared = torch.sin(t).unsqueeze(1) + 0.5 * torch.sin(3.7 * t).unsqueeze(1)
        coupling = 0.3 * torch.randn(n_neurons, n_neurons, generator=generator)
        local = 0.15 * torch.randn(n_time, n_neurons, generator=generator)
        neural_data = shared * (0.5 + 0.5 * torch.rand(1, n_neurons, generator=generator)) \
            + local @ (torch.eye(n_neurons) + 0.2 * coupling)
        analyzer = AdvancedConsciousnessAnalyzer(phi_method="gaussian")
        return await analyzer.analyze_consciousness(neural_data)

    async def join_network(
        self,
        capabilities: Dict[str, float],
        role: NetworkRole = NetworkRole.VALIDATOR,
    ) -> Dict[str, Any]:
        """Consciousness-gated node admission."""
        if self.consensus_engine is None:
            return {"joined": False, "reason": "network not initialized"}

        profile = await self._measure_consciousness(
            seed=len(self.nodes) + 1,
        )
        if profile.phi_value < self.config.min_join_phi:
            return {
                "joined": False,
                "reason": "insufficient consciousness level",
                "required_phi": self.config.min_join_phi,
                "actual_phi": profile.phi_value,
            }

        node = self.node_factory.create_node(
            role=role,
            capabilities=capabilities,
            consciousness_profile=profile,
            trust_score=0.5,
            reputation_score=0.5,
            computational_power=capabilities.get("tflops", 1.0),
            memory_capacity=capabilities.get("memory_gb", 8.0),
            network_bandwidth=capabilities.get("bandwidth_mbps", 100.0),
        )
        self.nodes[node.node_id] = node
        self.consensus_engine.update_topology(len(self.nodes))
        self.logger.info("node %s joined (phi=%.4f)", node.node_id, profile.phi_value)
        return {
            "joined": True,
            "node_id": node.node_id,
            "network_size": len(self.nodes),
            "consciousness_level": profile.consciousness_level.name,
            "phi_value": profile.phi_value,
        }

    def leave_network(self, node_id: str) -> bool:
        """Remove a node; consensus topology shrinks (state preserved)."""
        if node_id not in self.nodes:
            return False
        del self.nodes[node_id]
        if self.consensus_engine is not None and self.nodes:
            self.consensus_engine.update_topology(len(self.nodes))
        return True

    # ------------------------------------------------------------------
    def propose_and_vote(self, proposal: Any) -> Dict[str, Any]:
        """Propose an action and run a consensus round."""
        if self.consensus_engine is None:
            return {
                "achieved": False,
                "outcome": "not_initialized",
                "reason": "consensus engine not initialized",
            }
        result: ConsensusResult = self.consensus_engine.achieve_consensus(self.nodes, proposal)
        if result.achieved:
            self._update_reputations(proposal, result)
        return result.to_dict()

    def _update_reputations(self, proposal: Any, result: ConsensusResult) -> None:
        for node_id, node in self.nodes.items():
            node.contribution_history.append(
                {
                    "timestamp": time.time(),
                    "type": "consensus_participation",
                    "sequence": result.sequence,
                    "proposal_hash": result.proposal_hash,
                    "voted": node_id in result.votes,
                }
            )
            # Decay + participation boost (votes earn, absence decays)
            if node_id in result.votes:
                node.reputation_score = min(1.0, node.reputation_score * 0.99 + 0.01)
            else:
                node.reputation_score = max(0.0, node.reputation_score * 0.99)
            node.last_heartbeat = time.time()

    # ------------------------------------------------------------------
    def sweep_heartbeats(self) -> List[str]:
        """Prune nodes whose heartbeat timed out; returns removed ids."""
        now = time.time()
        stale = [
            nid for nid, n in self.nodes.items()
            if now - n.last_heartbeat > self.config.heartbeat_timeout_s
        ]
        for nid in stale:
            self.leave_network(nid)
        return stale

    def network_report(self) -> Dict[str, Any]:
        """Aggregate network statistics."""
        if not self.nodes:
            return {"network_size": 0, "status": self.network_state}
        phis = [
            n.consciousness_profile.phi_value
            for n in self.nodes.values()
            if n.consciousness_profile is not None
        ]
        return {
            "network_size": len(self.nodes),
            "status": self.network_state,
            "consensus_mode": self.consensus_mode,
            "view_number": self.consensus_engine.view_number if self.consensus_engine else 0,
            "sequence_number": self.consensus_engine.sequence_number if self.consensus_engine else 0,
            "mean_phi": sum(phis) / len(phis) if phis else 0.0,
            "mean_reputation": sum(n.reputation_score for n in self.nodes.values()) / len(self.nodes),
            "total_stake": sum(n.stake for n in self.nodes.values()),
            "architect": ARCHITECT.name,
        }
