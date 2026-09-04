"""Debug QFT vs DFT matrix and QPE."""
import sys

sys.path.insert(0, "src")
import numpy as np
import torch

from eci.quantum.statevector import StatevectorSimulator
from eci.quantum import gates as qg
from eci.quantum.algorithms import qft
from eci.framework import _rz_matrix

# Build my qft as a matrix by applying to each basis state
n = 3
sim = StatevectorSimulator(n)
N = 2 ** n
cols = []
for x in range(N):
    state = sim.basis_state(x)
    out = qft(state, sim)
    cols.append(out[0])
mine = torch.stack(cols, dim=1)  # column j = QFT|j>

dft = torch.zeros(N, N, dtype=torch.complex64)
for i in range(N):
    for j in range(N):
        dft[i, j] = torch.exp(torch.tensor(2j * np.pi * i * j / N)) / np.sqrt(N)

print("my qft vs DFT max err:", float(torch.abs(mine - dft).max()))

# Check inverse
inv_cols = []
for x in range(N):
    state = sim.basis_state(x)
    out = qft(state, sim, inverse=True)
    inv_cols.append(out[0])
mine_inv = torch.stack(inv_cols, dim=1)
print("my qft^-1 vs DFT^-1 max err:", float(torch.abs(mine_inv - dft.conj().T).max()))

# QPE manual trace: n_counting=3, U=RZ(pi/2), phi=1/8
nc = 3
simq = StatevectorSimulator(nc + 1)
state = simq.zero_state()
state = simq.apply_1q(state, qg.X, nc)  # eigenstate |1>
for c in range(nc):
    state = simq.apply_1q(state, qg.H, c)
for k in range(nc):
    control = nc - 1 - k
    gate = _rz_matrix(0.5 * np.pi * (2 ** k))
    state = simq.apply_controlled(state, gate, control, nc)
probs = simq.probabilities(state)[0]
counting = probs.view(-1, 2).sum(dim=1)
print("counting probs after controlled-U:", [round(float(p), 4) for p in counting])
expected = torch.zeros(N, dtype=torch.float64)
for y in range(N):
    expected[y] = abs(np.exp(2j * np.pi * (1 / 8) * y) / np.sqrt(N)) ** 2
print("expected kickback probs:          ", [round(float(p), 4) for p in expected])
state2 = qft(state, simq, inverse=True, qubits=[0, 1, 2])
probs2 = simq.probabilities(state2)[0].view(-1, 2).sum(dim=1)
print("post-IQFT counting probs:", [round(float(p), 4) for p in probs2])
print("peak:", int(torch.argmax(probs2).item()))

# Library QPE
from eci.quantum.algorithms import quantum_phase_estimation
res = quantum_phase_estimation(
    StatevectorSimulator(4),
    gate_fn=lambda e: _rz_matrix(0.5 * np.pi * e),
    n_counting=3,
)
print("library QPE phase (expect 0.125):", res["phase"])
