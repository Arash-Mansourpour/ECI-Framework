"""Find the exact QFT circuit discrepancy."""
import sys

sys.path.insert(0, "src")
import numpy as np
import torch

from eci.quantum.statevector import StatevectorSimulator
from eci.quantum import gates as qg


def build_matrix(circuit_fn, n):
    sim = StatevectorSimulator(n)
    N = 2 ** n
    cols = []
    for x in range(N):
        cols.append(circuit_fn(sim, sim.basis_state(x), n)[0])
    return torch.stack(cols, dim=1)


def dft_matrix(n):
    N = 2 ** n
    m = torch.zeros(N, N, dtype=torch.complex64)
    for i in range(N):
        for j in range(N):
            m[i, j] = torch.exp(torch.tensor(2j * np.pi * i * j / N)) / np.sqrt(N)
    return m


def cphase(theta):
    m = torch.eye(4, dtype=torch.complex64)
    m[3, 3] = torch.exp(torch.tensor(1j * theta))
    return m


def circuit_A(sim, state, n):  # H then CP(k>j, angle pi/2^(k-j)), swaps at end
    for j in range(n):
        state = sim.apply_1q(state, qg.H, j)
        for k in range(j + 1, n):
            state = sim.apply_2q(state, cphase(np.pi / 2 ** (k - j)), k, j)
    for q in range(n // 2):
        state = sim.apply_2q(state, qg.SWAP, q, n - 1 - q)
    return state


def circuit_B(sim, state, n):  # CP with angle pi/2^(k-j) where k-j counted from 1: same as A
    return circuit_A(sim, state, n)


def circuit_C(sim, state, n):  # H first on all, then CPs descending
    for j in range(n):
        state = sim.apply_1q(state, qg.H, j)
    for j in range(n):
        for k in range(j + 1, n):
            state = sim.apply_2q(state, cphase(np.pi / 2 ** (k - j)), k, j)
    for q in range(n // 2):
        state = sim.apply_2q(state, qg.SWAP, q, n - 1 - q)
    return state


for n in (1, 2, 3):
    dft = dft_matrix(n)
    for name, fn in [("A(H,CP interleaved)", circuit_A), ("C(H all, then CP)", circuit_C)]:
        m = build_matrix(fn, n)
        err = float(torch.abs(m - dft).max())
        print(f"n={n} {name}: err={err:.6f}")
        if err > 1e-5 and n == 2:
            print("  mine col2:", m[:, 2].tolist())
            print("  dft  col2:", dft[:, 2].tolist())
