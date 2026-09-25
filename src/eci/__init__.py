"""ECI Framework - Eternal Codex Infinitus.

Quantum-Supremacy Autonomous AI Research Framework, v5.

Architect (Sovereign / Ma'mar-e A'zam): Arash Mansourpour
"""

from eci import aikernel as aikernel

# SECE Phase 22: bridges + market commons
from eci import brain as brain
from eci import bridges as bridges
from eci import causality as causality
from eci import creativity as creativity
from eci import energy as energy
from eci import exploration as exploration
from eci import federation as federation
from eci import immune as immune
from eci import interpret as interpret
from eci import mcp as mcp
from eci import neural as neural
from eci import precog as precog

# Protocol-0 + immune + frontier systems
from eci import protocol0 as protocol0
from eci import protocol_vnext as protocol_vnext
from eci import recursion as recursion
from eci import verification as verification

# v6.1 deep systems (agents / data-plane / treasury / eval / supply / mcp)
from eci.agents import AgentLoop, Agents, EpisodicMemory, ToolRegistry, VectorMemory
from eci.aikernel import GenerativeState, KernelLedger, Likelihood, Prior, StateContributor
from eci.api import Gateway
from eci.arch import ADR_REGISTRY, list_adrs, run_fitness
from eci.authz import RBAC, Permission, PolicyEngine, PolicyRule, Role
from eci.benchmarking.benchmark import ResearchBenchmark
from eci.brain import BrainMesh, build_default_mesh
from eci.bridges.quantum_neuromorphic import QuantumNeuromorphicBridge
from eci.caps import CapToken
from eci.caps import Issuer as CapIssuer
from eci.causal import HLC, hlc_now, merge_chains, sort_key
from eci.causality import StructuralCausalModel, discover_skeleton
from eci.chaos import ChaosPlan, Fault, run_plan
from eci.cognition import Cognition, CognitionConfig
from eci.compat import CompatRegistry, Interface
from eci.config import ECIConfig, ExperimentConfig
from eci.consciousness.adherence import AdherenceTracker, calibration_tasks
from eci.consciousness.analyzer import AdvancedConsciousnessAnalyzer
from eci.consciousness.calibration_network import AwarenessCalibrationNetwork
from eci.consciousness.challenge import Transcript, grade
from eci.consciousness.challenge import issue as issue_challenges
from eci.consciousness.collective import CollectiveState, collective_awareness
from eci.consciousness.eeg import bandpower, load_timeseries
from eci.consciousness.federated_ledger import FederatedConsciousnessLedger
from eci.consciousness.free_energy import FreeEnergyAgent
from eci.consciousness.gnwt import GNWTWorkspace

# Consciousness (IIT + GNWT + FEP + quantum-mind + collective + challenge)
from eci.consciousness.iit import IntegratedInformationTheory
from eci.consciousness.protocol import ConsciousnessProtocol, awareness_index_from_bits
from eci.consciousness.quantum_mind import quantum_mind_audit
from eci.constants import ARCHITECT_NAME, CREATOR_WALLET
from eci.continuum import Continuum
from eci.core.device import configure_seeds, get_device
from eci.core.identity import ARCHITECT, ArchitectIdentity
from eci.core.types import (
    ConsciousnessLevel,
    ConsciousnessProfile,
    LearningParadigm,
    NetworkNode,
    NetworkRole,
    QuantumState,
)
from eci.court import Case, Court, Verdict
from eci.creativity import MAPElites, diversify_morph_probes, diversify_redteam
from eci.cybernetics.autopoiesis import AutopoieticNetwork
from eci.data import BlobStore, Cache, DataPlane
from eci.economy import ACTION_COSTS, Economy
from eci.economy_attack import (
    brier_score,
    evaluate_slash,
    simulate_collusion,
    simulate_whale_attack,
)
from eci.energy import EnergyLedger
from eci.eval import EvalReport, run_gates
from eci.exploration import Harness
from eci.federation.p2p import build_mesh as build_p2p_mesh
from eci.federation.p2p import run_partition_test

# Facade (completes and supersedes legacy ECIFrameworkResearch)
from eci.framework import ECIFramework, ECIFrameworkResearch
from eci.futura import EmergencyPowers, Futarchy, Sortition
from eci.genome import Gene, Genome, life_cycle, mutate

# Governance + cybernetics (v5)
from eci.governance.dao import ECIDataDAO

# NOTE: treasury's Envelope is aliased on purpose — bare `Envelope` belongs to
# the signed-transport envelope (network.envelope); importing both bare
# silently rebound it (mypy [assignment], Phase 17).
from eci.governance.treasury import Envelope as TreasuryEnvelope
from eci.governance.treasury import Treasury
from eci.health import metrics_text
from eci.health import status as health_status
from eci.interpret import LinearProbe, ablation_report

# v6 hyper-architecture (kernel / ops / control / intelligence)
from eci.kernel import Container, Event, EventBus, Kernel, LifecycleManager
from eci.learning.continual import ElasticWeightConsolidation
from eci.learning.federated import FederatedLearningCoordinator

# Learning
from eci.learning.maml import MAML, MetaMLP
from eci.learning.nas import AdvancedNAS, DARTSSearchSpace
from eci.mapek import MAPEK, SLO, Strategy
from eci.market import Market, Marketplace
from eci.market_commons import MarketCommons
from eci.mcp import McpFabric, McpRegistry, McpServer
from eci.mlops import MLOps, ModelRegistry, drift_report
from eci.morph import Morphogenesis
from eci.network.aggregation import (
    bulyan,
    byzantine_robust_aggregate,
    geometric_median,
    krum,
)

# Network
from eci.network.consensus import ConsensusResult, PBFTConsensus, WBFTConsensus
from eci.network.dht import DHTNode, lookup, xor_distance
from eci.network.envelope import Envelope, ReplayGuard, open_envelope, seal
from eci.network.gossip import GossipNode, anti_entropy, gossip_round
from eci.network.manager import AutonomousNetworkManager
from eci.network.membership import Member, Membership
from eci.network.reputation import Reputation, ReputationBoard
from eci.network.tcp import FramedTcpTransport
from eci.network.transport import AsyncMemoryChannel

# Neuromorphic
from eci.neuromorphic.neurons import LIFNeuron
from eci.neuromorphic.snn import SpikingNeuralNetwork
from eci.observability import AuditLogger, MetricsRegistry, Observability, Tracer
from eci.observability.otel import OtelBridge
from eci.orchestration import DAG, Orchestration, Scheduler
from eci.persistence import EventStore, Persistence, Repository, UnitOfWork
from eci.plugins import PluginManager, PluginManifest
from eci.privacy import Guardian
from eci.protocol_vnext.genesis_evolution import MutableConstitution
from eci.provenance import ProvenanceGraph
from eci.quantum import algorithms as qalg
from eci.quantum import channels as qchannels
from eci.quantum import density as qdensity
from eci.quantum import entanglement as qent
from eci.quantum import information as qinformation
from eci.quantum import lindblad as qlindblad
from eci.quantum import metrology as qmetrology
from eci.quantum import operator as qoperator
from eci.quantum import qec as qqec
from eci.quantum import tensor_network as qtensor
from eci.quantum import topological as qtopological
from eci.quantum import unified_field as qfield
from eci.quantum.backend import SimBackend, transpile, zne_extrapolate

# Quantum core (v5: operator algebra → field Hamiltonian)
from eci.quantum.gates import (
    CNOT,
    CRX,
    CRZ,
    CZ,
    RX,
    RY,
    RZ,
    SWAP,
    H,
    I,
    S,
    T,
    X,
    Y,
    Z,
    controlled,
    pauli_string_matrix,
)
from eci.quantum.hamiltonian import PauliSum, PauliTerm
from eci.quantum.hardware import BackendRouter, BraketBackend, QiskitBackend, SimBackendAdapter
from eci.quantum.qnn import QuantumLayer, QuantumNeuralNetwork
from eci.quantum.statevector import StatevectorSimulator
from eci.quantum.topological import BivariateBicycleCode, SurfaceCode
from eci.quantum.unified_field import ECIFieldConfig, eci_unified_hamiltonian
from eci.recovery import RecoveryRequest
from eci.recovery import combine as shamir_combine
from eci.recovery import split as shamir_split
from eci.recursion import OuterLoop
from eci.redteam import Challenger, ForecasterRegistry, contradiction_scan
from eci.research.loop import ResearchLoop
from eci.resilience import CircuitBreaker, Resilience, RetryPolicy, Saga, TokenBucket
from eci.rollout import RolloutPlan, staged_rollout

# Security & benchmarking
from eci.security.pqc import HashBasedSigner, PQCSuite, derive_key
from eci.security.secrets import SecretManager
from eci.security.secure_channel import HybridSecureChannel, SecureChannelConfig
from eci.semantic import Commons, Dispute, Fact
from eci.streaming import StreamBus
from eci.supply import sbom
from eci.tenancy import TenancyManager
from eci.twin import TwinReport, what_if
from eci.verification import Claim, VerificationGate
from eci.verify import Monitor, Watchtower, seal_proof, verify_proof
from eci.version import FRAMEWORK_VERSION, PAPER_VERSION, __version__

__all__ = [
    "__version__",
    "FRAMEWORK_VERSION",
    "PAPER_VERSION",
    "ARCHITECT_NAME",
    "CREATOR_WALLET",
    "ARCHITECT",
    "ArchitectIdentity",
    "get_device",
    "configure_seeds",
    "ECIConfig",
    "ExperimentConfig",
    "ConsciousnessLevel",
    "NetworkRole",
    "LearningParadigm",
    "QuantumState",
    "ConsciousnessProfile",
    "NetworkNode",
    "I", "X", "Y", "Z", "H", "S", "T",
    "CNOT", "CZ", "SWAP", "CRZ", "CRX",
    "RX", "RY", "RZ",
    "controlled",
    "pauli_string_matrix",
    "StatevectorSimulator",
    "qdensity",
    "qent",
    "qchannels",
    "qlindblad",
    "qalg",
    "qqec",
    "qoperator",
    "qinformation",
    "qtopological",
    "qtensor",
    "qmetrology",
    "qfield",
    "PauliSum",
    "PauliTerm",
    "QuantumNeuralNetwork",
    "QuantumLayer",
    "SurfaceCode",
    "BivariateBicycleCode",
    "ECIFieldConfig",
    "eci_unified_hamiltonian",
    "IntegratedInformationTheory",
    "AdvancedConsciousnessAnalyzer",
    "ConsciousnessProtocol",
    "awareness_index_from_bits",
    "GNWTWorkspace",
    "FreeEnergyAgent",
    "quantum_mind_audit",
    "CollectiveState",
    "collective_awareness",
    "AdherenceTracker",
    "calibration_tasks",
    "Transcript",
    "grade",
    "issue_challenges",
    "bandpower",
    "load_timeseries",
    "MAML",
    "MetaMLP",
    "AdvancedNAS",
    "DARTSSearchSpace",
    "FederatedLearningCoordinator",
    "ElasticWeightConsolidation",
    "LIFNeuron",
    "SpikingNeuralNetwork",
    "PBFTConsensus",
    "WBFTConsensus",
    "ConsensusResult",
    "geometric_median",
    "byzantine_robust_aggregate",
    "krum",
    "bulyan",
    "AsyncMemoryChannel",
    "Envelope",
    "ReplayGuard",
    "open_envelope",
    "seal",
    "GossipNode",
    "gossip_round",
    "anti_entropy",
    "Reputation",
    "ReputationBoard",
    "DHTNode",
    "lookup",
    "xor_distance",
    "Member",
    "Membership",
    "protocol0",
    "immune",
    "federation",
    "precog",
    "creativity", "verification", "exploration", "causality",
    "energy", "interpret", "recursion",
    "neural",
    "HLC",
    "hlc_now",
    "merge_chains",
    "sort_key",
    "ACTION_COSTS",
    "Economy",
    "TwinReport",
    "what_if",
    "RecoveryRequest",
    "shamir_combine",
    "shamir_split",
    "RolloutPlan",
    "staged_rollout",
    "metrics_text",
    "health_status",
    "Case",
    "Court",
    "Verdict",
    "Market",
    "Marketplace",
    "Commons",
    "Dispute",
    "Fact",
    "Guardian",
    "Gene",
    "Genome",
    "life_cycle",
    "mutate",
    "AutonomousNetworkManager",
    "ECIDataDAO",
    "AutopoieticNetwork",
    "Kernel", "EventBus", "Event", "Container", "LifecycleManager",
    "Observability", "Tracer", "MetricsRegistry", "AuditLogger",
    "Persistence", "EventStore", "Repository", "UnitOfWork",
    "Resilience", "CircuitBreaker", "RetryPolicy", "TokenBucket", "Saga",
    "Orchestration", "DAG", "Scheduler",
    "PluginManager", "PluginManifest",
    "PolicyEngine", "PolicyRule", "RBAC", "Role", "Permission",
    "StreamBus", "MLOps", "ModelRegistry", "drift_report",
    "ProvenanceGraph", "Gateway", "TenancyManager",
    "ChaosPlan", "Fault", "run_plan",
    "SecretManager", "HybridSecureChannel", "SecureChannelConfig",
    "Agents", "AgentLoop", "ToolRegistry", "EpisodicMemory", "VectorMemory",
    "DataPlane", "Cache", "BlobStore",
    "Treasury", "TreasuryEnvelope",
    "run_gates", "EvalReport", "sbom",
    "FramedTcpTransport", "SimBackend", "transpile", "zne_extrapolate",
    "mcp", "McpFabric", "McpServer", "McpRegistry",
    "Cognition", "CognitionConfig", "Morphogenesis",
    "aikernel", "GenerativeState", "Likelihood", "Prior",
    "StateContributor", "KernelLedger",
    "CapToken", "CapIssuer", "Watchtower", "Monitor", "seal_proof", "verify_proof",
    "Continuum", "MAPEK", "SLO", "Strategy",
    "CompatRegistry", "Interface",
    "Futarchy", "Sortition", "EmergencyPowers",
    "Challenger", "ForecasterRegistry", "contradiction_scan",
    "protocol_vnext",
    "FederatedConsciousnessLedger", "AwarenessCalibrationNetwork",
    "MarketCommons", "QuantumNeuromorphicBridge", "MutableConstitution", "bridges",
    "PQCSuite",
    "HashBasedSigner",
    "derive_key",
    "ResearchBenchmark",
    "ECIFramework",
    "ECIFrameworkResearch",
    "brain", "BrainMesh", "build_default_mesh",
    "MAPElites", "diversify_morph_probes", "diversify_redteam",
    "Claim", "VerificationGate", "Harness",
    "StructuralCausalModel", "discover_skeleton",
    "EnergyLedger", "LinearProbe", "ablation_report", "OuterLoop",
    "run_fitness", "ADR_REGISTRY", "list_adrs",
    "BackendRouter", "SimBackendAdapter", "QiskitBackend", "BraketBackend",
    "build_p2p_mesh", "run_partition_test",
    "simulate_whale_attack", "simulate_collusion", "evaluate_slash", "brier_score",
    "OtelBridge", "ResearchLoop",
]
