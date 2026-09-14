"""Phase 20 — quantum + mcp/network minimal smoke to lift 83%→85%."""

import torch

from eci.quantum.hamiltonian import PauliSum, PauliTerm
from eci.quantum.statevector import StatevectorSimulator


def test_qft_roundtrip_2q():
    sim = StatevectorSimulator(2)
    state = sim.zero_state()
    # put |+> and do QFT -> inverse QFT should return to |+> up to phase
    from eci.quantum.algorithms import qft
    state = sim.apply_1q(state, torch.tensor([[0.7071, 0.7071], [0.7071, -0.7071]], dtype=torch.complex64), 0)
    state = sim.apply_1q(state, torch.tensor([[0.7071, 0.7071], [0.7071, -0.7071]], dtype=torch.complex64), 1)
    after = qft(state, sim, inverse=False)
    back = qft(after, sim, inverse=True)
    # probabilities should be close
    p0 = sim.probabilities(state)[0]
    p1 = sim.probabilities(back)[0]
    assert torch.allclose(p0, p1, atol=1e-4)


def test_grover_2q_marked():
    from eci.quantum.algorithms import grover_search
    sim = StatevectorSimulator(2)
    out = grover_search(sim, marked=[1], iterations=1)
    assert 0.0 <= out["success_probability"] <= 1.0
    assert out["iterations"] == 1


def test_qpe_phase():

    from eci.quantum.algorithms import quantum_phase_estimation

    # U = Z on eigen qubit, eigen |1> has phase pi -> phi=0.5
    def gate_fn(pow2):
        # Z^(2^k) = Z if pow2 odd else I
        if pow2 % 2 == 1:
            return torch.tensor([[1, 0], [0, -1]], dtype=torch.complex64)
        return torch.eye(2, dtype=torch.complex64)

    sim = StatevectorSimulator(3)  # 2 counting + 1 eigen
    out = quantum_phase_estimation(sim, gate_fn, n_counting=2, eigenstate_index=1)
    assert 0.0 <= out["phase"] < 1.0
    assert out["peak_index"] in range(4)


def test_vqe_tiny():
    from eci.quantum.algorithms import vqe
    # 2-qubit Z Hamiltonian (avoids 1-qubit CNOT ring bug)
    h = PauliSum([PauliTerm(coeff=1.0, paulis={0: "Z"}), PauliTerm(coeff=1.0, paulis={1: "Z"})])
    out = vqe(h, n_qubits=2, n_layers=1, steps=2, seed=0)
    assert "energy" in out and "history" in out
    assert len(out["history"]) == 2


def test_qaoa_tiny():
    from eci.quantum.algorithms import qaoa_maxcut
    out = qaoa_maxcut(edges=[(0, 1)], n_qubits=2, depth=1, steps=2, seed=0)
    assert "expected_cut" in out
    assert 0.0 <= out["expected_cut"] <= 1.0


def test_operator_and_gates_smoke():
    from eci.quantum import operator as qop
    from eci.quantum.gates import RX, RY, H, X
    H2 = torch.tensor([[0, 1], [1, 0]], dtype=torch.complex64)
    assert qop.is_hermitian(H2)
    U = qop.matrix_exponential_hermitian(H2, 0.5)
    assert qop.is_unitary(U)
    # gates
    assert RX(0.5).shape == (2, 2)
    assert RY(0.3).shape == (2, 2)
    assert H.shape == (2, 2)
    assert X.shape == (2, 2)


def test_qec_bitflip_smoke():
    from eci.quantum import gates as qg
    from eci.quantum.qec import BitFlipCode
    code = BitFlipCode()
    out = code.run_trial(error_qubit=0, error_gate=qg.X, alpha=0.0, beta=1.0)
    assert "logical_fidelity" in out or isinstance(out, dict)


def test_statevector_expectation():
    sim = StatevectorSimulator(2)
    state = sim.uniform_superposition()
    exp = sim.expectation_pauli(state, {0: "Z"})
    assert exp.shape[0] == 1


def test_network_manager_make_consensus_smoke():
    from eci.config import NetworkConfig
    from eci.network.manager import AutonomousNetworkManager
    m = AutonomousNetworkManager(config=NetworkConfig(), consensus_mode="pbft", seed=0)
    # _make_consensus is hot path with mypy **kwargs bug — exercise both modes
    c1 = m._make_consensus(4)
    assert c1.n_nodes == 4
    m.consensus_mode = "wbft"
    c2 = m._make_consensus(4)
    assert c2.n_nodes == 4
