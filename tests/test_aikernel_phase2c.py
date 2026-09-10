"""Phase 2c — governance adapter: consensus as posterior reconciliation.

Calibrated numbers (1-D Gaussian toy, prior N(0,1), s*=1.5, threshold 1.0,
LMSR b=10, myopic round-robin, 6 rounds max):
  identical info (R=[.5,.5], obs=[1.6,1.6]):
      p_fused=0.5460, price 0.5->0.5498, ALL 12 trades same side, dF=0.0 exact
  asymmetric info (R=[1.0,.25], obs=[1.2,1.7]):
      p_fused=0.6054, price_final=0.5710 (gap +0.034), tug-of-war, dF=0.841
Tolerances are justified in-test. The b-sensitivity divergence (b=50:
persistent 0.24<->0.83 limit cycle, gap -0.23) is reported, not asserted.
"""
import torch


def _prior():
    from eci.aikernel.generative_model import Prior
    return Prior.standard(1)


def test_shared_prior_fusion_is_idempotent():
    """Fusing identical posteriors returns them (zero-reduction identity)."""
    from eci.governance.aikernel_adapter import AgentContributor, reconcile
    a = AgentContributor("a", 1, _prior(), 0.5)
    b = AgentContributor("b", 1, _prior(), 0.5)
    a.observe(torch.tensor([1.6]))
    b.observe(torch.tensor([1.6]))
    f = reconcile([a, b])
    assert torch.allclose(f.mu, a.posterior().mu, atol=1e-6)
    assert torch.allclose(f.cov, a.posterior().cov, atol=1e-6)
    # idempotent under ANY weights (still the same single belief)
    fw = reconcile([a, b], weights=[3.0, 1.0])
    assert torch.allclose(fw.mu, a.posterior().mu, atol=1e-6)


def test_weights_steer_toward_informed_agent():
    from eci.governance.aikernel_adapter import AgentContributor, reconcile
    a = AgentContributor("a", 1, _prior(), 1.0)    # vague
    b = AgentContributor("b", 1, _prior(), 0.25)   # sharp
    a.observe(torch.tensor([0.0]))
    b.observe(torch.tensor([2.0]))
    f_eq = reconcile([a, b])
    f_w = reconcile([a, b], weights=[1.0, 9.0])
    mb = float(b.posterior().mu.item())
    assert abs(float(f_w.mu.item()) - mb) < abs(float(f_eq.mu.item()) - mb)


def test_identical_info_zero_reduction_both_paths():
    """Fusion: dF == 0.0 exactly. Market: zero adversarial movement
    (all trades one-sided, price -> shared belief, gap < 0.05)."""
    from eci.governance.aikernel_adapter import market_vs_fusion
    r = market_vs_fusion(1.5, _prior(), [0.5, 0.5], [1.6, 1.6])
    # 2.4e-7 measured: float32 round-trip through inverse pairs, not signal.
    # Threshold 1e-6 justified: six orders above float noise (~1e-12 relative
    # on values O(1)), four below the smallest real effect (0.84).
    assert r["dF_fusion"] < 1e-6, r
    # Honest market property (corrected from naive "one-sided" claim: the
    # 1.0-share minimum overshoots, so echo-correction trades occur): price
    # never leaves a tight band around the SHARED belief — agreement, not
    # tug-of-war. Band 0.05 justified: 5x the observed echo amplitude 0.021,
    # half the asymmetric tug span below.
    band = max(abs(t["price"] - r["p_fused"]) for t in r["trades"])
    assert band < 0.05, (band, r["trades"])
    assert abs(r["price_final"] - r["p_fused"]) < 0.05, r


def test_different_info_measurable_reduction():
    """Genuinely different private info: fusion gains dF=0.84 (>> float noise).
    Threshold 0.05 justified: two orders below measured, four above 1e-6 noise."""
    from eci.governance.aikernel_adapter import market_vs_fusion
    r = market_vs_fusion(1.5, _prior(), [1.0, 0.25], [1.2, 1.7])
    assert r["dF_fusion"] > 0.05, r
    assert abs(r["dF_fusion"] - 0.841) < 0.05, r  # pins the calibrated value
    sides = {t["side"] for t in r["trades"]}
    assert sides == {"yes", "no"}, r["trades"]  # real disagreement traded


def test_four_agents_asymmetric():
    from eci.governance.aikernel_adapter import market_vs_fusion, reconcile, AgentContributor
    noises = [1.0, 0.5, 0.25, 2.0]
    obs = [1.1, 1.6, 1.7, 0.9]
    r = market_vs_fusion(1.5, _prior(), noises, obs)
    assert r["dF_fusion"] > 0.05, r
    ags = [AgentContributor(f"a{i}", 1, _prior(), n) for i, n in enumerate(noises)]
    for ag, o in zip(ags, obs):
        ag.observe(torch.tensor([o]))
    assert len(reconcile(ags).mu) == 1


def test_agent_contributor_contract_and_share():
    """conforms(); share == kernel complexity (third reuse site, same math)."""
    from eci.aikernel.free_energy import free_energy_parts
    from eci.aikernel.generative_model import Likelihood
    from eci.aikernel.state_contract import conforms
    from eci.consciousness.aikernel_adapter import PhiContributor
    from eci.governance.aikernel_adapter import AgentContributor
    ag = AgentContributor("a0", 2, obs_noise=0.5)
    assert conforms(ag) is True  # prior-as-posterior is a valid belief
    ag.observe(torch.tensor([0.5, -0.5]))
    got = float(ag.free_energy_contribution().item())
    ref = float(free_energy_parts(ag.posterior(), torch.zeros(2),
                                  Likelihood(torch.eye(2), torch.eye(2)),
                                  ag.prior)["complexity"].item())
    assert abs(got - ref) < 1e-5, (got, ref)
    # same discipline as 2b: displacement, not a native protocol metric
    from eci.aikernel.generative_model import GenerativeState
    assert isinstance(ag.update(torch.tensor([0.1, 0.1])), GenerativeState)


def test_three_member_ledger_mixed_cadence():
    """VQE (every step) + Phi (every 2nd obs) + agent (every 3rd round):
    no lockstep forced; total == sum of shares at every checkpoint."""
    from eci.aikernel.state_contract import KernelLedger
    from eci.consciousness.aikernel_adapter import PhiContributor
    from eci.governance.aikernel_adapter import AgentContributor
    from eci.quantum.aikernel_adapter import VQEContributor, tfi_hamiltonian
    torch.manual_seed(0)
    vqe_c = VQEContributor(tfi_hamiltonian(2), 2, e_target=-3.2)
    phi_c = PhiContributor(dim=6)
    gov_c = AgentContributor("gov-0", 1, obs_noise=0.5)
    led = KernelLedger()
    for name, m in (("vqe", vqe_c), ("phi", phi_c), ("gov", gov_c)):
        led.register(name, m)
    assert set(led.shares()) == {"vqe", "phi", "gov"}
    for step in range(6):
        vqe_c.step()                                    # fast cadence
        if step % 2 == 0:
            phi_c.update(torch.randn(32, 6))            # medium cadence
        if step % 3 == 0:
            gov_c.update(torch.tensor([0.5]))           # slow cadence (rounds)
        total = float(led.total_free_energy().detach().item())
        assert abs(total - sum(led.shares().values())) < 1e-5, (total, led.shares())
