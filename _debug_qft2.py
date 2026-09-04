"""Diff n=3 QFT entries."""
import sys

sys.path.insert(0, "src")
import numpy as np
import torch

from eci.quantum.statevector import StatevectorSimulator
from eci.quantum import gates as qg


def cphase(theta):
    m = torch.eye(4, dtype=torch.complex64)
    m[3, 3] = torch.exp(torch.tensor(1j * theta))
    return m


n = 3
sim = StatevectorSimulator(n)
N = 2 ** n
cols = []
for x in range(N):
    state = sim.basis_state(x)
    for j in range(n):
        state = sim.apply_1q(state, qg.H, j)
        for k in range(j + 1, n):
            state = sim.apply_2q(state, cphase(np.pi / 2 ** (k - j)), k, j)
    for q in range(n // 2):
        state = sim.apply_2q(state, qg.SWAP, q, n - 1 - q)
    cols.append(state[0])
mine = torch.stack(cols, dim=1)

dft = torch.zeros(N, N, dtype=torch.complex64)
for i in range(N):
    for j in range(N):
        dft[i, j] = torch.exp(torch.tensor(2j * np.pi * i * j / N)) / np.sqrt(N)

diff = (mine - dft).abs()
idx = (diff > 1e-5).nonzero()
print("differing entries (row, col):", idx.tolist()[:20])
print("total differing:", len(idx))
r, c = idx[0].tolist()
print(f"mine[{r},{c}] =", mine[r, c].item(), " dft =", dft[r, c].item())
