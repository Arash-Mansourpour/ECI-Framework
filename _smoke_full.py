"""Full-package smoke: imports, QEC, algorithms, consciousness, network."""
import sys

sys.path.insert(0, "src")
import asyncio

import torch

import eci
from eci.quantum import qec as qqec
from eci.quantum import algorithms as qalg
from eci.quantum import lindblad as qlin
from eci.quantum import channels as qch
from eci.quantum import density as qd
from eci.quantum.mock_quantum import MockOscillatorEnsemble

print("import eci OK, version:", eci.__version__)

# QEC
bfc = qqec.BitFlipCode()
r = bfc.run_trial(error_qubit=1)
print("bitflip fidelity:", r["logical_fidelity"], "corrected:", r["corrected_qubit"])
shor = qqec.ShorCode()
for gate in ("X", "Y", "Z"):
    r = shor.run_trial(error_qubit=4, error_gate=gate)
    print("shor", gate, "fidelity:", round(r["logical_fidelity"], 6))

# QPE
from eci.framework import _rz_matrix
qpe = qalg.quantum_phase_estimation(
    __import__("eci.quantum.statevector", fromlist=["StatevectorSimulator"]).StatevectorSimulator(4),
    gate_fn=lambda e: _rz_matrix(0.5 * 3.141592653589793 * e),
    n_counting=3,
)
print("qpe phase (expect 0.125):", qpe["phase"])

# Grover
g = qalg.grover_search(__import__("eci.quantum.statevector", fromlist=["StatevectorSimulator"]).StatevectorSimulator(3), [5])
print("grover success (expect ~1):", round(g["success_probability"], 4))

# VQE
from eci.quantum.hamiltonian import PauliSum, PauliTerm
h = PauliSum([PauliTerm(0.5, {0: "Z", 1: "Z"}), PauliTerm(0.3, {0: "X"})])
v = qalg.vqe(h, n_qubits=2, n_layers=2, steps=80, lr=0.1)
print("vqe energy:", round(v["energy"], 5), "initial:", round(v["history"][0], 5))

# QAOA
q = qalg.qaoa_maxcut([(0, 1), (1, 2), (2, 0)], n_qubits=3, depth=2, steps=60)
print("qaoa best cut (expect 3):", q["best_cut"], "expected:", round(q["expected_cut"], 3))

# Lindblad + channels
rho0 = qd.from_statevector(torch.tensor([1 / 2**0.5, 1 / 2**0.5], dtype=torch.complex64))
collapse = [torch.tensor([[0.0, 1.0], [0.0, 0.0]], dtype=torch.complex64)]
traj = qlin.lindblad_evolve(rho0, torch.zeros(2, 2, dtype=torch.complex64), collapse, n_steps=30, dt=0.1)
print("coherence decay:", round(float(qlin.coherence_measure(traj[0])[0]), 3), "->",
      round(float(qlin.coherence_measure(traj[-1])[0]), 3))
stabilizer = qlin.MockQuantumStabilizer()
traj2 = qlin.lindblad_evolve(
    rho0, torch.zeros(2, 2, dtype=torch.complex64), collapse, n_steps=30, dt=0.1,
    hamiltonian_schedule=stabilizer.schedule(collapse),
)
print("stabilized coherence:", round(float(qlin.coherence_measure(traj2[-1])[0]), 3))
kraus = qch.depolarizing(0.1)
print("cptp depolarizing:", qd.is_cptp(kraus))

# Mock quantum
ens = MockOscillatorEnsemble(n_oscillators=8)
for _ in range(50):
    ens.step()
print("mock hbar:", ens.hbar_mock, "coherence indicator:", round(ens.coherence_indicator(), 3))

# Consciousness + network (facade)
from eci.framework import ECIFramework
fw = ECIFramework()
profile = asyncio.run(fw.analyze_consciousness(n_steps=256, n_neurons=16, seed=3))
print("phi:", round(profile.phi_value, 4), "level:", profile.consciousness_level.name)
net = asyncio.run(fw.run_network_simulation(n_joins=3, n_proposals=2))
print("network size:", net["report"]["network_size"])
print("vote outcomes:", [v["outcome"] for v in net["votes"]])

# QNN gradient flow
from eci.quantum.qnn import QuantumNeuralNetwork
qnn = QuantumNeuralNetwork(in_features=4, n_qubits=3, out_features=2, n_layers=1)
x = torch.randn(5, 4, requires_grad=True)
out = qnn(x)
loss = out.sum()
loss.backward()
print("qnn grad norm (expect > 0):", float(qnn.q_layer.angles.grad.norm()))

# PQC
from eci.security.pqc import PQCSuite, SecureChannel, derive_key
suite = PQCSuite()
tok = suite.architect_signed_token(b"test-payload")
print("architect token verified:", suite.verify_architect_token(tok))
ch = SecureChannel(b"shared-secret")
nonce, ct, tag = ch.encrypt(b"hello quantum world")
print("channel decrypt:", ch.decrypt(nonce, ct, tag))

# Consensus + aggregation
from eci.network.consensus import PBFTConsensus, WBFTConsensus
from eci.network.nodes import NodeFactory
from eci.core.types import NetworkRole
factory = NodeFactory(seed=11)
nodes = {n.node_id: n for n in (factory.create_node(NetworkRole.VALIDATOR, seed=i) for i in range(7))}
pbft = PBFTConsensus(n_nodes=7, byzantine_rate=0.0)
res = pbft.achieve_consensus(nodes, {"action": "test"})
print("pbft honest (expect achieved):", res.achieved)
pbft_f = PBFTConsensus(n_nodes=7, byzantine_rate=0.9)
res2 = pbft_f.achieve_consensus(nodes, {"action": "test"})
print("pbft heavy byzantine (expect rejected):", res2.achieved)

from eci.network.aggregation import geometric_median, byzantine_robust_aggregate
pts = torch.tensor([[0.0, 0.0], [0.1, 0.0], [0.0, 0.1], [100.0, 100.0]])
gm = geometric_median(pts)
print("geometric median (robust to outlier):", gm.tolist())
updates = [{"w": torch.tensor([1.0, 2.0])}, {"w": torch.tensor([1.1, 1.9])}, {"w": torch.tensor([50.0, 50.0])}]
agg = byzantine_robust_aggregate(updates)
print("robust agg:", agg["w"].tolist())

print("ALL FULL-PACKAGE SMOKE CHECKS DONE")
