"""Quantum computation core of the ECI Framework (v5 Quantum-Supremacy).

Layers: Dirac operator algebra → statevector/density → channels/Lindblad →
algorithms → QEC/topological → tensor-networks/metrology/information →
unified ECI field Hamiltonian.
"""

from eci.quantum import algorithms, channels, density, entanglement, gates, hamiltonian, information, lindblad, metrology, mock_quantum, operator, qec, qnn, statevector, tensor_network, topological, unified_field
from eci.quantum.algorithms import grover_search, qaoa_maxcut, quantum_phase_estimation, qft, vqe
from eci.quantum.channels import NoiseModel
from eci.quantum.gates import CNOT, CZ, H, I, S, SWAP, T, X, Y, Z, controlled, pauli_string_matrix
from eci.quantum.hamiltonian import PauliSum, PauliTerm
from eci.quantum.qec import BitFlipCode, ShorCode
from eci.quantum.qnn import QuantumLayer, QuantumNeuralNetwork
from eci.quantum.statevector import StatevectorSimulator
from eci.quantum.topological import BivariateBicycleCode, SurfaceCode
from eci.quantum.unified_field import ECIFieldConfig, eci_unified_hamiltonian

__all__ = [
    "algorithms", "channels", "density", "entanglement", "gates",
    "hamiltonian", "information", "lindblad", "metrology", "mock_quantum",
    "operator", "qec", "qnn", "statevector", "tensor_network",
    "topological", "unified_field",
    "StatevectorSimulator", "NoiseModel", "PauliSum", "PauliTerm",
    "BitFlipCode", "ShorCode", "QuantumLayer", "QuantumNeuralNetwork",
    "qft", "grover_search", "quantum_phase_estimation", "vqe", "qaoa_maxcut",
    "I", "X", "Y", "Z", "H", "S", "T", "CNOT", "CZ", "SWAP",
    "controlled", "pauli_string_matrix",
    "SurfaceCode", "BivariateBicycleCode",
    "ECIFieldConfig", "eci_unified_hamiltonian",
]
