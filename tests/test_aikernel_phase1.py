"""Phase 1 — kernel contract: numbers proving the integration is real.

Every test below checks an EXACT mathematical identity (closed forms,
analytic gradients, round-trips), not mere plumbing. Tolerances are
float32-appropriate; seeds fixed.
"""
import math

import torch


def _model(d=3, m=2, seed=0):
    from eci.aikernel.generative_model import Likelihood, Prior
    g = torch.Generator().manual_seed(seed)
    A = torch.randn(m, d, generator=g)
    R = torch.eye(m) * 0.5 + 0.1 * torch.randn(m, m, generator=g)
    R = R @ R.T + 0.2 * torch.eye(m)
    mu0 = torch.randn(d, generator=g)
    S0 = torch.randn(d, d, generator=g)
    S0 = S0 @ S0.T + torch.eye(d)
    return Likelihood(A, R), Prior(mu0, S0)


def test_vfe_matches_monte_carlo():
    """Closed-form F == E_Q[-log p(o,s) + log q(s)] by sampling (seeded)."""
    from eci.aikernel.free_energy import free_energy
    from eci.aikernel.generative_model import GenerativeState
    torch.manual_seed(0)
    L, P = _model()
    mu = torch.tensor([0.5, -0.3, 0.2])
    S = torch.tensor([[1.0, 0.2, 0.0], [0.2, 1.5, 0.1], [0.0, 0.1, 0.8]])
    st = GenerativeState(mu, S)
    obs = torch.tensor([1.0, -0.5])
    F = float(free_energy(st, obs, L, P).item())
    N = 200_000
    dist = torch.distributions.MultivariateNormal(mu, S)
    s = dist.sample((N,))
    logp_o = torch.distributions.MultivariateNormal(s @ L.A.T, L.R).log_prob(obs.expand(N, -1))
    logp_s = torch.distributions.MultivariateNormal(P.mu0, P.Sigma0).log_prob(s)
    mc = float((-logp_o - logp_s + dist.log_prob(s)).mean().item())
    assert abs(F - mc) < 0.05, (F, mc)


def test_vfe_autograd_matches_analytic_gradient():
    """dF/dmu has a closed form; autograd must reproduce it exactly."""
    from eci.aikernel.free_energy import free_energy
    from eci.aikernel.generative_model import GenerativeState
    L, P = _model()
    mu = torch.tensor([0.5, -0.3, 0.2], requires_grad=True)
    S = torch.tensor([[1.0, 0.2, 0.0], [0.2, 1.5, 0.1], [0.0, 0.1, 0.8]])
    obs = torch.tensor([1.0, -0.5])
    F = free_energy(GenerativeState(mu, S), obs, L, P)
    g = torch.autograd.grad(F, mu)[0]
    S0inv = torch.linalg.inv(P.Sigma0)
    Rinv = torch.linalg.inv(L.R)
    analytic = S0inv @ (mu.detach() - P.mu0) - L.A.T @ Rinv @ (obs - L.A @ mu.detach())
    assert torch.allclose(g, analytic, atol=1e-4), (g, analytic)


def test_vfe_at_exact_posterior_equals_neg_log_evidence():
    """Q = exact Bayes posterior  =>  F = -log p(o). The identity that makes F *the* objective."""
    from eci.aikernel.free_energy import free_energy, neg_log_evidence
    from eci.aikernel.generative_model import GenerativeState
    L, P = _model()
    obs = torch.tensor([1.0, -0.5])
    S0inv = torch.linalg.inv(P.Sigma0)
    Lam = S0inv + L.A.T @ torch.linalg.inv(L.R) @ L.A
    Sp = torch.linalg.inv(Lam)
    mup = Sp @ (S0inv @ P.mu0 + L.A.T @ torch.linalg.inv(L.R) @ obs)
    F = float(free_energy(GenerativeState(mup, Sp), obs, L, P).item())
    NLE = float(neg_log_evidence(obs, L, P).item())
    assert abs(F - NLE) < 1e-4, (F, NLE)


def _rand_rho(D, seed):
    g = torch.Generator().manual_seed(seed)
    X = torch.randn(D, D, dtype=torch.complex64, generator=g)
    rho = X @ X.conj().T + 1e-3 * torch.eye(D, dtype=torch.complex64)
    return rho / torch.trace(rho).real


def test_quantum_complexity_matches_density_relative_entropy():
    """Independent code paths, same math — including NON-commuting pairs."""
    from eci.aikernel.free_energy import quantum_free_energy
    from eci.quantum.density import relative_entropy
    for seed in range(5):
        rho = _rand_rho(4, seed)
        sig = _rand_rho(4, 100 + seed)
        got = float(quantum_free_energy(rho, ["ZZ"], [0.0], torch.eye(1), rho_prior=sig)["complexity"].item())
        ref = float(relative_entropy(rho.unsqueeze(0), sig.unsqueeze(0))[0].item())
        assert abs(got - ref) < 1e-3, (seed, got, ref)


def test_density_to_cov_exact_known_states():
    """|0>: mu=(0,0,1), Var(Z)=0. Maximally mixed: mu=0, cov=I."""
    from eci.aikernel.functors import density_to_cov
    zero = torch.zeros(2, 2, dtype=torch.complex64)
    zero[0, 0] = 1.0
    mu, cov = density_to_cov(zero, 1, ["X", "Y", "Z"])
    assert torch.allclose(mu, torch.tensor([0.0, 0.0, 1.0]), atol=1e-5), mu
    assert torch.allclose(cov, torch.diag(torch.tensor([1.0, 1.0, 0.0])), atol=1e-5), cov
    mixed = torch.eye(2, dtype=torch.complex64) / 2
    mu2, cov2 = density_to_cov(mixed, 1, ["X", "Y", "Z"])
    assert torch.allclose(mu2, torch.zeros(3), atol=1e-5), mu2
    assert torch.allclose(cov2, torch.eye(3), atol=1e-5), cov2
    # Bell |Phi+>: <ZZ>=1 with zero variance; <X0>=0 with unit variance
    bell = torch.zeros(4, 4, dtype=torch.complex64)
    bell[0, 0] = bell[0, 3] = bell[3, 0] = bell[3, 3] = 0.5
    mu3, cov3 = density_to_cov(bell, 2, ["ZZ", "X0"])
    assert abs(float(mu3[0]) - 1.0) < 1e-5 and float(cov3[0, 0]) < 1e-5, (mu3, cov3)
    assert abs(float(mu3[1])) < 1e-5 and abs(float(cov3[1, 1]) - 1.0) < 1e-5


def test_split_fuse_roundtrip_and_composition():
    """fuse(split(Q)) == Q and split_v(split_w(Q)) == split_{vw}(Q): the diagram commutes."""
    from eci.aikernel.functors import fuse_beliefs, split_belief
    torch.manual_seed(0)
    mu = torch.randn(4)
    A = torch.randn(4, 4)
    cov = A @ A.T + torch.eye(4)
    parts = split_belief(mu, cov, [0.5, 0.3, 0.2])
    mu_r, cov_r = fuse_beliefs(parts)
    assert torch.allclose(mu_r, mu, atol=1e-5)
    assert torch.allclose(cov_r, cov, atol=1e-5)
    # composition law: sub-splitting branch w_i by v refines the partition
    # into weights (w_i·v, w_i·(1-v)) — compare against the matching slices
    inner = split_belief(mu, cov, [0.4, 0.6])
    left = split_belief(inner[0][0], inner[0][1], [0.25, 0.75])
    assert torch.allclose(left[0][1], split_belief(mu, cov, [0.1, 0.9])[0][1], atol=1e-5)
    assert torch.allclose(left[1][1], split_belief(mu, cov, [0.3, 0.7])[0][1], atol=1e-5)
    # bad weights rejected loudly
    import pytest
    with pytest.raises(ValueError):
        split_belief(mu, cov, [0.5, 0.5, 0.5])


def test_cross_representation_roundtrip():
    """rho -> Q -> agents -> Q reproduces the Pauli-coordinate Gaussian."""
    from eci.aikernel.functors import density_to_cov, fuse_beliefs, split_belief
    from eci.aikernel.generative_model import GenerativeState
    rho = _rand_rho(2, 3)
    st = GenerativeState.from_density(rho, 1, ["X", "Y", "Z"])
    assert st.rho is not None and st.n_qubits == 1
    mu_r, cov_r = fuse_beliefs(split_belief(st.mu, st.cov, [0.6, 0.4]))
    assert torch.allclose(mu_r, st.mu, atol=1e-5)
    assert torch.allclose(cov_r, st.cov, atol=1e-5)


def test_contract_ledger_and_conformance():
    """KernelLedger sums shares; non-conformants and NaN shares rejected."""
    import pytest
    import torch
    from eci.aikernel.generative_model import GenerativeState
    from eci.aikernel.state_contract import KernelLedger, StateContributor, conforms

    class Good:
        def __init__(self, v):
            self.v = v
        def posterior(self):
            return GenerativeState(torch.zeros(2), torch.eye(2))
        def update(self, observation):
            return self.posterior()
        def free_energy_contribution(self):
            return torch.tensor(self.v)

    class Bad:
        def posterior(self):
            return "not-a-state"

    class NaN:
        def posterior(self):
            return GenerativeState(torch.zeros(2), torch.eye(2))
        def update(self, observation):
            return self.posterior()
        def free_energy_contribution(self):
            return torch.tensor(float("nan"))

    assert conforms(Good(1.0)) is True
    assert conforms(Bad()) is False
    assert conforms(NaN()) is False
    assert conforms(object()) is False
    led = KernelLedger()
    led.register("a", Good(1.5))
    led.register("b", Good(2.5))
    assert led.shares() == {"a": 1.5, "b": 2.5}
    assert abs(float(led.total_free_energy().item()) - 4.0) < 1e-6
    with pytest.raises(TypeError):
        led.register("bad", Bad())
    with pytest.raises(TypeError):
        led.register("nan", NaN())
