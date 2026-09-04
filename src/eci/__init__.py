"""ECI Framework - Eternal Codex Infinitus.

Quantum-Supremacy Autonomous AI Research Framework, v5.

Architect (Sovereign / Ma'mar-e A'zam): Arash Mansourpour
"""

from eci.version import FRAMEWORK_VERSION, PAPER_VERSION, __version__
from eci.constants import ARCHITECT_NAME, CREATOR_WALLET
from eci.core.identity import ARCHITECT, ArchitectIdentity
from eci.core.device import get_device, configure_seeds
from eci.config import ECIConfig, ExperimentConfig
from eci.core.types import (
    ConsciousnessLevel,
    NetworkRole,
    LearningParadigm,
    QuantumState,
    ConsciousnessProfile,
    NetworkNode,
)

# Quantum core (v5: operator algebra → field Hamiltonian)
from eci.quantum.gates import (
    CNOT,
    CZ,
    H,
    I,
    S,
    SWAP,
    T,
    X,
    Y,
    Z,
    RX,
    RY,
    RZ,
    controlled,
    pauli_string_matrix,
)
from eci.quantum.statevector import StatevectorSimulator
from eci.quantum import density as qdensity
from eci.quantum import entanglement as qent
from eci.quantum import channels as qchannels
from eci.quantum import lindblad as qlindblad
from eci.quantum import algorithms as qalg
from eci.quantum import qec as qqec
from eci.quantum import operator as qoperator
from eci.quantum import information as qinformation
from eci.quantum import topological as qtopological
from eci.quantum import tensor_network as qtensor
from eci.quantum import metrology as qmetrology
from eci.quantum import unified_field as qfield
from eci.quantum.hamiltonian import PauliSum, PauliTerm
from eci.quantum.qnn import QuantumNeuralNetwork, QuantumLayer
from eci.quantum.topological import BivariateBicycleCode, SurfaceCode
from eci.quantum.unified_field import ECIFieldConfig, eci_unified_hamiltonian

# Consciousness (v5: IIT + GNWT + FEP + quantum-mind)
from eci.consciousness.iit import IntegratedInformationTheory
from eci.consciousness.analyzer import AdvancedConsciousnessAnalyzer
from eci.consciousness.protocol import ConsciousnessProtocol
from eci.consciousness.gnwt import GNWTWorkspace
from eci.consciousness.free_energy import FreeEnergyAgent
from eci.consciousness.quantum_mind import quantum_mind_audit

# Learning
from eci.learning.maml import MAML, MetaMLP
from eci.learning.nas import AdvancedNAS, DARTSSearchSpace
from eci.learning.federated import FederatedLearningCoordinator
from eci.learning.continual import ElasticWeightConsolidation

# Neuromorphic
from eci.neuromorphic.neurons import LIFNeuron
from eci.neuromorphic.snn import SpikingNeuralNetwork

# Network
from eci.network.consensus import PBFTConsensus, WBFTConsensus, ConsensusResult
from eci.network.aggregation import geometric_median, byzantine_robust_aggregate
from eci.network.manager import AutonomousNetworkManager

# Governance + cybernetics (v5)
from eci.governance.dao import ECIDataDAO
from eci.cybernetics.autopoiesis import AutopoieticNetwork

# Security & benchmarking
from eci.security.pqc import PQCSuite, HashBasedSigner, derive_key
from eci.benchmarking.benchmark import ResearchBenchmark

# Facade (completes and supersedes legacy ECIFrameworkResearch)
from eci.framework import ECIFramework, ECIFrameworkResearch

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
    "CNOT", "CZ", "SWAP",
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
    "GNWTWorkspace",
    "FreeEnergyAgent",
    "quantum_mind_audit",
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
    "AutonomousNetworkManager",
    "ECIDataDAO",
    "AutopoieticNetwork",
    "PQCSuite",
    "HashBasedSigner",
    "derive_key",
    "ResearchBenchmark",
    "ECIFramework",
    "ECIFrameworkResearch",
]
