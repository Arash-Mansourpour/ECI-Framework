"""Phase 2a — quantum adapter: VQE loss literally IS kernel F.

Calibrated numbers (2-qubit TFI, J=h=1, seed 42, 200 Adam steps):
  exact ground E0 = -2.2360682
  native  vqe()  -> -2.2360532   (err 1.5e-5)
  aikernel loop  -> -2.2360628   (err 5.2e-6)
  |E_nat - E_aik| ≈ 1e-5  |  F: 3.8056 -> 1.8866, monotonic 179/199 (90%)
Tolerances below are 100-1000x looser than observed (CI headroom), except
the agreement identity which is exact algebra.
"""
import torch


def test_likelihood_identity_is_exact():
    """inaccuracy == 1/2(E_t-E)^2/R_e + (eps/2)||o-m||^2, by construction."""
    from eci.aikernel.free_energy import quantum_free_energy
    from eci.aikernel.functors import pauli_string_matrix
    from eci.quantum.aikernel_adapter import tfi_hamiltonian
    from eci.quantum.aikernel_likelihood import energy_likelihood
    torch.manual_seed(0)
    H = tfi_hamiltonian(2)
    labels, o, R = energy_likelihood(H, 2, e_target=-3.0, R_e=2.0, eps=1e-3)
    X = torch.randn(4, 4, dtype=torch.complex64)
    rho = (X @ X.conj().T)
    rho = rho / torch.trace(rho).real
    E = sum(float(t.coeff) * torch.trace(
        rho @ pauli_string_matrix(lab, 2).to(torch.complex64)).real.item()
        for t, lab in zip(H.terms, labels))
    m = torch.stack([torch.trace(rho @ pauli_string_matrix(l, 2)).real for l in labels]).float()
    parts = quantum_free_energy(rho, labels, o, R)
    expect = 0.5 * (float(-3.0 - E) ** 2) / 2.0 + 0.5e-3 * float(((o - m) ** 2).sum().item())
    assert abs(float(parts["inaccuracy"].item()) - expect) < 1e-4, \
        (parts["inaccuracy"].item(), expect)


def test_vqe_native_vs_aikernel_converge_together():
    from eci.quantum.aikernel_adapter import tfi_hamiltonian, vqe_aikernel
    from eci.quantum.algorithms import vqe
    H = tfi_hamiltonian(2)
    E0 = float(torch.linalg.eigvalsh(H.to_matrix(2)).min().item())
    nat = vqe(H, 2, n_layers=2, steps=200, lr=0.05, seed=42)
    aik = vqe_aikernel(H, 2, n_layers=2, steps=200, lr=0.05, seed=42, e_target=E0 - 1.0)
    assert abs(nat["energy"] - E0) < 0.05, (nat["energy"], E0)
    assert abs(aik["energy_final"] - E0) < 0.05, (aik["energy_final"], E0)
    assert abs(nat["energy"] - aik["energy_final"]) < 0.05
    Fh = aik["F_history"]
    assert Fh[-1] < Fh[0] - 1.0, (Fh[0], Fh[-1])
    mono = sum(1 for a, b in zip(Fh, Fh[1:]) if b <= a) / (len(Fh) - 1)
    assert mono >= 0.8, mono  # Adam overshoot on ~10-20% of steps (reported, not hidden)


def test_ledger_total_tracks_adapter():
    """KernelLedger.total_free_energy() == adapter share (single member)."""
    from eci.aikernel.state_contract import KernelLedger, conforms
    from eci.quantum.aikernel_adapter import VQEContributor, tfi_hamiltonian
    H = tfi_hamiltonian(2)
    c = VQEContributor(H, 2, e_target=-3.2)
    assert conforms(c) is True
    led = KernelLedger()
    led.register("vqe", c)
    traj = []
    for _ in range(10):
        c.step()
        traj.append(float(led.total_free_energy().detach().item()))
    assert traj[-1] < traj[0]
    assert led.shares().keys() == {"vqe"}


def test_posterior_update_contract():
    from eci.aikernel.generative_model import GenerativeState
    from eci.quantum.aikernel_adapter import VQEContributor, tfi_hamiltonian
    H = tfi_hamiltonian(2)
    c = VQEContributor(H, 2, e_target=-3.2)
    st = c.posterior()
    assert isinstance(st, GenerativeState) and st.rho is not None
    assert st.dim == 6  # default_paulis(2) = X0,Y0,Z0,X1,Y1,Z1
    # Gaussian coords consistent with the density matrix they came from
    from eci.aikernel.functors import pauli_expectations
    ref = pauli_expectations(st.rho, 2, st.paulis)
    assert torch.allclose(st.mu, ref, atol=1e-5)
    st2 = c.update(torch.tensor([-2.5]))
    assert abs(c.e_target - (-2.5)) < 1e-9
    assert isinstance(st2, GenerativeState)


def test_native_vqe_api_unchanged():
    """Existing public API untouched: same signature, same return keys."""
    import inspect

    from eci.quantum.algorithms import vqe
    assert list(inspect.signature(vqe).parameters) == \
        ["hamiltonian", "n_qubits", "n_layers", "steps", "lr", "seed"]
    from eci.quantum.aikernel_adapter import tfi_hamiltonian
    out = vqe(tfi_hamiltonian(2), 2, n_layers=1, steps=5, seed=0)
    assert set(out) == {"energy", "history", "params", "state"}
