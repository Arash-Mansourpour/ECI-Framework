"""Phase 2b — consciousness adapter: Phi on the shared posterior.

Sweep numbers (2-qubit Pauli coords, N(0,I) prior, gaussian Phi,
contiguous cuts) are asserted structurally here; exact measured values
go in the phase report.
"""
import torch


def _bell_state():
    from eci.aikernel.generative_model import GenerativeState
    bell = torch.zeros(4, 4, dtype=torch.complex64)
    bell[0, 0] = bell[0, 3] = bell[3, 0] = bell[3, 3] = 0.5
    return GenerativeState.from_density(bell, 2)


def test_state_path_matches_raw_path_exactly():
    """Same covariance-core => same phi_total to 1e-9 (thin wrapper proof)."""
    from eci.aikernel.generative_model import GenerativeState
    from eci.consciousness.iit import IntegratedInformationTheory
    torch.manual_seed(0)
    iit = IntegratedInformationTheory()
    X = torch.randn(512, 4)
    mu = X.mean(0)
    ce = X - mu
    cov = (ce.T @ ce) / (X.size(0) - 1)  # unregularized; both paths add reg identically
    conn = torch.corrcoef(X.T)
    raw = iit.calculate_phi(X, connectivity=conn, method="gaussian")
    st = GenerativeState(mu.float(), cov.float())
    via = iit.calculate_phi(state=st, connectivity=conn, method="gaussian")
    assert abs(raw["phi_total"] - via["phi_total"]) < 1e-9, (raw, via)
    rawq = iit.calculate_phi(X, connectivity=conn, method="quantum")
    viaq = iit.calculate_phi(state=st, connectivity=conn, method="quantum")
    assert abs(rawq["phi_total"] - viaq["phi_total"]) < 1e-9, (rawq, viaq)
    # Bell pair through the new path only (rho-backed state)
    bell = iit.calculate_phi(state=_bell_state(), method="gaussian")
    assert bell["phi_total"] > 0.1, bell


def test_complexity_matches_kernel_term():
    """Adapter share == kernel complexity term (same math, two code paths)."""
    from eci.aikernel.free_energy import free_energy_parts
    from eci.aikernel.generative_model import Likelihood, Prior
    from eci.consciousness.aikernel_adapter import PhiContributor
    torch.manual_seed(1)
    d = 4
    mu = torch.randn(d)
    A = torch.randn(d, d)
    cov = A @ A.T + torch.eye(d)
    prior = Prior.standard(d)
    pc = PhiContributor(dim=d, prior=prior)
    pc.analyze(__import__("eci.aikernel.generative_model", fromlist=["GenerativeState"]).GenerativeState(mu, cov),
               recompute_phi=False)
    got = float(pc.free_energy_contribution().item())
    ref = float(free_energy_parts(pc.posterior(), torch.zeros(d),
                                  Likelihood(torch.eye(d), torch.eye(d)), prior)["complexity"].item())
    assert abs(got - ref) < 1e-5, (got, ref)


def test_phi_complexity_dissociation_sweep():
    """The category boundary, measured: complexity WITHOUT Phi (product),
    neither (mixed), both (Bell). No monotone link is the finding."""
    from eci.aikernel.generative_model import GenerativeState
    from eci.consciousness.aikernel_adapter import PhiContributor
    from eci.consciousness.iit import IntegratedInformationTheory
    iit = IntegratedInformationTheory()
    bell = _bell_state()
    zero = torch.zeros(4, 4, dtype=torch.complex64)
    zero[0, 0] = 1.0
    prod = GenerativeState.from_density(zero, 2)
    mixed = GenerativeState(torch.zeros(6), torch.eye(6))
    rows = {}
    for name, st in (("bell", bell), ("product", prod), ("mixed", mixed)):
        pc = PhiContributor(dim=6, method="gaussian")
        phi = iit.calculate_phi(state=st, method="gaussian")["phi_total"]
        pc.analyze(st, recompute_phi=False)
        comp = float(pc.free_energy_contribution().item())
        rows[name] = (phi, comp)
    assert rows["product"][0] < 1e-6 and rows["product"][1] > 0.5, rows
    assert rows["mixed"][0] < 1e-6 and rows["mixed"][1] < 1e-6, rows
    assert rows["bell"][0] > 0.1 and rows["bell"][1] > 1.0, rows


def test_update_lazy_phi_and_posterior():
    from eci.consciousness.aikernel_adapter import PhiContributor
    torch.manual_seed(2)
    pc = PhiContributor(dim=4)
    assert pc.last_phi is None and pc.phi_stale is True
    st = pc.update(torch.randn(64, 4))  # no Phi recompute by default
    assert pc.phi_stale is True and pc.last_phi is None
    assert st.dim == 4
    assert torch.isfinite(pc.free_energy_contribution())
    pc.update(torch.randn(64, 4), recompute_phi=True)
    assert pc.phi_stale is False and pc.last_phi is not None


def test_two_member_ledger_quantum_plus_phi():
    """VQEContributor + PhiContributor: total == sum of shares, both move."""
    from eci.aikernel.state_contract import KernelLedger, conforms
    from eci.consciousness.aikernel_adapter import PhiContributor
    from eci.quantum.aikernel_adapter import VQEContributor, tfi_hamiltonian
    torch.manual_seed(0)  # was unseeded randn: passed only via VQE dominance; now deterministic
    H = tfi_hamiltonian(2)
    vqe_c = VQEContributor(H, 2, e_target=-3.2)
    phi_c = PhiContributor(dim=6)
    from eci.aikernel.generative_model import GenerativeState as _GS
    phi_c.analyze(_GS.from_density(_bell_rho(), 2))
    assert conforms(phi_c) is True
    led = KernelLedger()
    led.register("vqe", vqe_c)
    led.register("phi", phi_c)
    totals = []
    for _ in range(5):
        vqe_c.step()
        phi_c.update(torch.randn(32, 6))
        totals.append(float(led.total_free_energy().detach().item()))
        assert abs(totals[-1] - sum(led.shares().values())) < 1e-6
    assert totals[-1] < totals[0]
    assert set(led.shares()) == {"vqe", "phi"}


def _bell_rho():
    bell = torch.zeros(4, 4, dtype=torch.complex64)
    bell[0, 0] = bell[0, 3] = bell[3, 0] = bell[3, 3] = 0.5
    return bell
