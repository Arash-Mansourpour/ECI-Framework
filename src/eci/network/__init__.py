"""Distributed coordination layer: consensus, aggregation, node lifecycle."""

from eci.network.aggregation import byzantine_robust_aggregate, geometric_median
from eci.network.consensus import ConsensusResult, PBFTConsensus, WBFTConsensus
from eci.network.manager import AutonomousNetworkManager
from eci.network.nodes import NodeFactory

__all__ = [
    "PBFTConsensus", "WBFTConsensus", "ConsensusResult",
    "geometric_median", "byzantine_robust_aggregate",
    "NodeFactory", "AutonomousNetworkManager",
]
