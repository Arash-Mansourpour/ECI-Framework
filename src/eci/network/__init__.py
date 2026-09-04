"""Distributed coordination layer: consensus, aggregation, node lifecycle."""

from eci.network.aggregation import (
    byzantine_robust_aggregate,
    geometric_median,
    krum,
    bulyan,
)
from eci.network.consensus import ConsensusResult, PBFTConsensus, WBFTConsensus
from eci.network.manager import AutonomousNetworkManager
from eci.network.nodes import NodeFactory
from eci.network.transport import AsyncMemoryChannel
from eci.network.envelope import Envelope, ReplayGuard, seal, open_envelope
from eci.network.gossip import GossipNode, anti_entropy, gossip_round
from eci.network.reputation import Reputation, ReputationBoard

__all__ = [
    "PBFTConsensus", "WBFTConsensus", "ConsensusResult",
    "geometric_median", "byzantine_robust_aggregate", "krum", "bulyan",
    "NodeFactory", "AutonomousNetworkManager", "AsyncMemoryChannel",
    "Envelope", "ReplayGuard", "seal", "open_envelope",
    "GossipNode", "gossip_round", "anti_entropy",
    "Reputation", "ReputationBoard",
]
