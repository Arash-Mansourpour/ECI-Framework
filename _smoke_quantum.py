"""Smoke test for the quantum core (temporary development script)."""
import sys

sys.path.insert(0, "src")
import torch

from eci.quantum.statevector import StatevectorSimulator
from eci.quantum import gates as qg
from eci.quantum import density as qd
from eci.quantum import entanglement as qe
from eci.quantum.hamiltonian import PauliSum, PauliTerm

sim = StatevectorSimulator(2)
s = sim.zero_state()
s = sim.apply_1q(s, qg.H, 0)
s = sim.apply_2q(s, qg.CNOT, 0, 1)
print("bell norm:", sim.norm(s))
print("Z0Z1 (expect -1):", sim.expectation_pauli(s, {0: "Z", 1: "Z"}))
print("Z0 (expect 0):", sim.expectation_pauli(s, {0: "Z"}))
print("X0X1 (expect 1):", sim.expectation_pauli(s, {0: "X", 1: "X"}))
print("Y0Y1 (expect -1):", sim.expectation_pauli(s, {0: "Y", 1: "Y"}))

rho = qd.from_statevector(s)
print("purity (expect 1):", qd.purity(rho))
print("vn entropy rho (expect 0):", qd.von_neumann_entropy(rho))
print("concurrence (expect 1):", qe.concurrence(rho))
print("negativity (expect .5):", qe.negativity(rho, 2, [1]))
print("ent entropy (expect 1):", qe.entanglement_entropy(s, 2, [0]))
red = qd.partial_trace(s, 2, [0])
print("reduced entropy (expect 1 bit):", qd.von_neumann_entropy(red))
print("fidelity same (expect 1):", qd.fidelity(rho, rho))

prod = sim.basis_state(0)
rp = qd.from_statevector(prod)
print("prod concurrence (expect 0):", qe.concurrence(rp))

# Trotter evolution check: e^{-i t ZZ} via ladder vs dense matrix exp
h = PauliSum([PauliTerm(1.0, {0: "Z", 1: "Z"})])
t = 0.7
s2 = sim.uniform_superposition()
s_ev = h.evolve(s2, sim, t)
hmat = h.to_matrix(2)
evals, evecs = torch.linalg.eigh(hmat)
expected = evecs @ torch.diag(torch.exp(-1j * t * evals)) @ evecs.conj().T
direct = (expected @ s2[0].to(expected.dtype))
print("trotter vs exact max err:", float(torch.abs(s_ev[0] - direct.to(s_ev.dtype)).max()))

# Y-rotation identity check: e^{-i t Y/2} == S H e^{-i t Z/2} H S^dag (time order: S^dag, H, RZ(t), H, S)
th = 0.9
s3 = sim.random_state(1)
y_ev = sim.apply_1q(s3, qg.RY(th), 0)
z_path = sim.apply_ops(s3, [("1q", qg.S.conj(), 0), ("1q", qg.H, 0), ("1q", qg.RZ(th), 0), ("1q", qg.H, 0), ("1q", qg.S, 0)])
print("Y identity max err:", float(torch.abs(y_ev[0] - z_path[0]).max()))

# QFT roundtrip
from eci.quantum.algorithms import qft
sim3 = StatevectorSimulator(3)
s4 = sim3.basis_state(5)
fwd = qft(s4, sim3)
back = qft(fwd, sim3, inverse=True)
print("QFT roundtrip err:", float(torch.abs(back - s4).max()))

print("ALL QUANTUM SMOKE CHECKS DONE")
