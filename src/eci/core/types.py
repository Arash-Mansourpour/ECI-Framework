"""Shared types: enums and serializable dataclasses.

All tensor-bearing dataclasses provide ``to_dict`` serialization that
converts tensors to nested lists, keeping the structures JSON-exportable.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import torch

__all__ = [
    "ConsciousnessLevel",
    "NetworkRole",
    "LearningParadigm",
    "ConsensusOutcome",
    "QuantumState",
    "ConsciousnessProfile",
    "NetworkNode",
]


class ConsciousnessLevel(Enum):
    """Consciousness levels based on IIT phi values."""

    NONE = 0  # Phi < 0.01
    MINIMAL = 1  # 0.01 <= Phi < 0.1
    BASIC = 2  # 0.1 <= Phi < 0.5
    INTERMEDIATE = 3  # 0.5 <= Phi < 1.0
    ADVANCED = 4  # 1.0 <= Phi < 2.0
    EMERGENT = 5  # 2.0 <= Phi < 5.0
    TRANSCENDENT = 6  # Phi >= 5.0


class NetworkRole(Enum):
    """Roles in the distributed autonomous network."""

    SEED_NODE = "seed"
    VALIDATOR = "validator"
    RESEARCHER = "researcher"
    CONSENSUS_LEADER = "consensus_leader"
    LEARNER = "learner"
    META_LEARNER = "meta_learner"


class LearningParadigm(Enum):
    """Learning paradigms supported by the framework."""

    SUPERVISED = "supervised"
    UNSUPERVISED = "unsupervised"
    REINFORCEMENT = "reinforcement"
    META_LEARNING = "meta_learning"
    CONTINUAL = "continual"
    FEDERATED = "federated"


class ConsensusOutcome(Enum):
    """Outcome of a consensus round."""

    ACHIEVED = "achieved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"
    NOT_INITIALIZED = "not_initialized"


@dataclass
class QuantumState:
    """Quantum state representation (Nielsen & Chuang conventions).

    ``statevector`` has shape ``(batch, 2**n)`` with qubit 0 as the most
    significant bit; ``density_matrix`` has shape ``(batch, 2**n, 2**n)``.
    """

    statevector: Optional[torch.Tensor] = None
    density_matrix: Optional[torch.Tensor] = None
    coherence_time: float = 0.0  # T2 coherence time (seconds)
    fidelity: float = 0.0  # F = |<psi|phi>|^2 against a reference
    entanglement_entropy: float = 0.0  # Von Neumann entropy (bits)
    purity: float = 0.0  # Tr(rho^2)

    def __post_init__(self) -> None:
        if self.density_matrix is None and self.statevector is not None:
            psi = self.statevector
            if psi.dim() == 1:
                psi = psi.unsqueeze(0)
            self.density_matrix = torch.einsum("bi,bj->bij", psi, psi.conj())
            self.purity = float(
                torch.einsum("bij,bji->b", self.density_matrix, self.density_matrix)
                .real.mean()
                .item()
            )

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        for key in ("statevector", "density_matrix"):
            value = d.get(key)
            if isinstance(value, torch.Tensor):
                d[key] = None  # keep JSON export small; full arrays on demand
            elif value is not None:
                d[key] = value
        return d


@dataclass
class ConsciousnessProfile:
    """Consciousness profile based on IIT 4.0."""

    phi_value: float  # Integrated information Phi
    phi_components: Dict[str, float] = field(default_factory=dict)
    consciousness_level: ConsciousnessLevel = ConsciousnessLevel.NONE
    neural_complexity: float = 0.0  # Lempel-Ziv / entropy mix
    quantum_coherence: float = 0.0  # Quantum contribution
    self_awareness_score: float = 0.0  # Meta-cognitive score
    temporal_consistency: float = 0.0
    information_integration: float = 0.0
    causal_density: float = 0.0
    signature_pattern: Optional[torch.Tensor] = None  # Unique signature
    architect_stamp: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["consciousness_level"] = self.consciousness_level.name
        if isinstance(self.signature_pattern, torch.Tensor):
            d["signature_pattern"] = self.signature_pattern.detach().cpu().numpy().tolist()
        return d


@dataclass
class NetworkNode:
    """Enhanced autonomous network node."""

    node_id: str
    role: NetworkRole
    consciousness_profile: Optional[ConsciousnessProfile] = None
    quantum_signature: str = ""
    capabilities: Dict[str, float] = field(default_factory=dict)
    trust_score: float = 1.0
    reputation_score: float = 1.0
    stake: float = 1.0  # weight for WBFT
    contribution_history: List[Dict[str, Any]] = field(default_factory=list)
    model_weights_hash: Optional[str] = None
    last_heartbeat: float = 0.0
    computational_power: float = 1.0  # TFLOPS
    memory_capacity: float = 8.0  # GB
    network_bandwidth: float = 100.0  # Mbps
    architect_stamp: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["role"] = self.role.name
        if self.consciousness_profile is not None:
            d["consciousness_profile"] = self.consciousness_profile.to_dict()
        else:
            d["consciousness_profile"] = None
        return d
