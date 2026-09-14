"""ECI Protocol vNext — Evolving Collective Intelligence Protocol.

Implements the open spec in `docs/protocol_vnext/`:

- ECI-GENESIS : genesis root, beacon, preservation (ArchitectIdentity)
- ECI-GENOME  : constitutional genome H(G0||...||Gn)
- ECI-ID      : node lifecycle DISCOVER→EVOLVE
- ECI-CAP     : dynamic capability vectors (declared→observed→verified)
- ECI-MSG     : async fabric with capability-aware routing
- ECI-COG     : neuro-cognitive runtime (PERCEIVE→ENCODE + faculties + gating)
- ECI-MEM     : living memory (working/episodic/semantic/procedural/reflective + dream)
- ECI-KNOW    : federated living ontology (propose-only evolution)
- ECI-TRUTH   : evidence keeper + truth guardian (separation generation/evaluation)
- ECI-LEARN   : collective learning loop (OutcomeReceipt)
- ECI-EVOLVE  : governed evolution + skill compiler + intelligence compression
- ECI-RESILIENCE : graceful degradation + substrate independence

All modules are transport-agnostic (MQTT/NATS/Kafka/A2A/libp2p swappable).
See `GENESIS_SPEC.md` and `ECI_PROTOCOL_vNext_SPEC.md` for wire formats.
"""

from eci.protocol_vnext.capability import CapabilityManifest, CapabilityVector, ContextualTrust
from eci.protocol_vnext.cognitive import CognitiveFaculty, CognitiveGating, CognitiveRuntime
from eci.protocol_vnext.collective import CollectiveLearningLoop, OutcomeReceipt, TeamIntelligence
from eci.protocol_vnext.epistemic import ConfidenceLevel, EvidenceKeeper, TruthGuardian
from eci.protocol_vnext.evolution import GovernedEvolution, SkillCompiler
from eci.protocol_vnext.genesis import ArchitectBeacon, ConstitutionalGenome
from eci.protocol_vnext.genome import GENOME as STATIC_GENOME
from eci.protocol_vnext.identity import ECIIdentity, NodeLifecycle
from eci.protocol_vnext.memory import DreamEngine, LivingMemory
from eci.protocol_vnext.messaging import ECIMessage, MessageFabric
from eci.protocol_vnext.model_fabric import AdaptiveModelRouter, ModelFabric
from eci.protocol_vnext.ontology import FederatedOntology
from eci.protocol_vnext.reasoning import ParetoFrontier, PredictiveWorldModel, ReasoningLandscape
from eci.protocol_vnext.resilience import (
    ExperimentalReasoningLab,
    GracefulDegradation,
    SubstrateAdapter,
)

__all__ = [
    "ECIIdentity", "NodeLifecycle",
    "ArchitectBeacon", "ConstitutionalGenome", "STATIC_GENOME",
    "CapabilityVector", "CapabilityManifest", "ContextualTrust",
    "ECIMessage", "MessageFabric",
    "AdaptiveModelRouter", "ModelFabric",
    "CognitiveRuntime", "CognitiveFaculty", "CognitiveGating",
    "LivingMemory", "DreamEngine",
    "FederatedOntology",
    "EvidenceKeeper", "TruthGuardian", "ConfidenceLevel",
    "ReasoningLandscape", "ParetoFrontier", "PredictiveWorldModel",
    "CollectiveLearningLoop", "OutcomeReceipt", "TeamIntelligence",
    "GovernedEvolution", "SkillCompiler",
    "GracefulDegradation", "SubstrateAdapter", "ExperimentalReasoningLab",
]
