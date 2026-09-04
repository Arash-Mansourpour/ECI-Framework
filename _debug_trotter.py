"""Compare smoke's exact path vs debug path line by line."""
import sys

sys.path.insert(0, "src")
import torch

from eci.quantum.statevector import StatevectorSimulator
from eci.quantum import gates as qg
from eci.quantum.hamiltonian import PauliSum, PauliTerm

torch.manual_seed(0)
sim = StatevectorSimulator(2)
h = PauliSum([PauliTerm(1.0, {0: "Z", 1: "Z"})])
t = 0.7

for name, s2 in [
    ("uniform", sim.uniform_superposition()),
    ("random", sim.random_state(1)),
    ("basis", sim.basis_state(1)),
]:
    s_ev = h.evolve(s2, sim, t)
    hmat = h.to_matrix(2)
    evals, evecs = torch.linalg.eigh(hmat)
    expected = evecs @ torch.diag(torch.exp(-1j * t * evals)) @ evecs.conj().T
    direct = (expected @ s2[0].to(expected.dtype))
    err = torch.abs(s_ev[0].double() - direct)
    print(name, "err:", float(err.max()), "dtype s_ev:", s_ev.dtype, "dtype direct:", direct.dtype)
    if err.max() > 1e-5:
        print("  s_ev:", s_ev[0])
        print("  direct:", direct)
        print("  hmat:", hmat)
