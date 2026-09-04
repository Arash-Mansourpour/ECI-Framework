"""Core primitives of the ECI Framework."""

from eci.core.device import configure_seeds, get_device, seed_context
from eci.core.identity import ARCHITECT, ArchitectIdentity
from eci.core.registry import GLOBAL_REGISTRY, Registry, register_component
from eci.core.types import (
    ConsciousnessLevel,
    ConsciousnessProfile,
    ConsensusOutcome,
    LearningParadigm,
    NetworkNode,
    NetworkRole,
    QuantumState,
)

__all__ = [
    "get_device",
    "configure_seeds",
    "seed_context",
    "ARCHITECT",
    "ArchitectIdentity",
    "GLOBAL_REGISTRY",
    "Registry",
    "register_component",
    "ConsciousnessLevel",
    "ConsciousnessProfile",
    "ConsensusOutcome",
    "LearningParadigm",
    "NetworkNode",
    "NetworkRole",
    "QuantumState",
]
