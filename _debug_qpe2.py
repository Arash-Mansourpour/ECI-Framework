"""Print QPE kickback amplitudes directly."""
import sys

sys.path.insert(0, "src")
import numpy as np
import torch

from eci.quantum.statevector import StatevectorSimulator
from eci.quantum import gates as qg
from eci.framework import _rz_matrix

nc = 3
simq = StatevectorSimulator(nc + 1)
state = simq.zero_state()
state = simq.apply_1q(state, qg.X, nc)
for c in range(nc):
    state = simq.apply_1q(state, qg.H, c)
for k in range(nc):
    control = nc - 1 - k
    gate = _rz_matrix(0.5 * np.pi * (2 ** k))
    print(f"applying U^{2 ** k} with control qubit {control}")
    state = simq.apply_controlled(state, gate, control, nc)

amps = state[0]
print("kickback amplitudes (counting, eigen):")
for y in range(8):
    a0 = amps[2 * y].item()
    a1 = amps[2 * y + 1].item()
    print(f"  y={y:03b}: |y,0>={a0:.4f}  |y,1>={a1:.4f}  expected phase e^(2pi i y/8)={np.exp(2j * np.pi * y / 8):.4f}")
