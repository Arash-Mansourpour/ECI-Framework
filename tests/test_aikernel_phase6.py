"""Phase 6 — cognition adapters: imagination + science as contributors.

Measured calibration (seeded): world share 0.5393 (init) -> 1.075 after
one transition (recon 0.4479 / reward 0.1835 / kl 0.0369 / ens 0.8796);
scientist after ys=[1,3],pred=[0,0]: mean 0.571429, prec 1.4, share 0.188644.
"""
import pytest
import torch


def test_world_model_posterior_share_and_validation():
    from eci.aikernel.state_contract import conforms
    from eci.cognition.aikernel_adapter import WorldModelContributor
    from eci.cognition.world_model import WorldModelConfig
    torch.manual_seed(0)
    cfg = WorldModelConfig(obs_dim=4, act_dim=2, hidden=16, latent=4)
    w = WorldModelContributor(cfg)
    assert conforms(w) is True
    assert w.posterior().dim == 4
    with pytest.raises(ValueError):
        w.update(torch.zeros(5))  # wrong transition length
    tr = torch.cat([torch.randn(4), torch.randn(2).tanh(), torch.tensor([0.5]), torch.randn(4)])
    st = w.update(tr)
    assert st.dim == 4
    assert abs(float(w.free_energy_contribution().item()) - w.last_parts()["total"]) < 1e-9
    assert set(w.last_parts()) == {"total", "recon", "reward", "kl", "ensemble"}
    assert all(v == v and abs(v) < 1e6 for v in w.last_parts().values())


def test_scientist_hand_computed_belief():
    """ys=[1,3], pred=[0,0]: rss=10, m=2, lik_prec=0.4 -> mean 4/7, prec 1.4."""
    from eci.aikernel.state_contract import conforms
    from eci.cognition.aikernel_adapter import ScientistContributor
    s = ScientistContributor("h", "y=a*x+b", 2)
    assert conforms(s) is True
    assert float(s.free_energy_contribution().item()) == 0.0  # N(0,1) vs itself
    s.update(torch.tensor([1.0, 3.0, 0.0, 0.0]))
    h = s.scientist.hypos["h"]
    assert abs(h.mean - 4 / 7) < 1e-6 and abs(h.prec - 1.4) < 1e-6, (h.mean, h.prec)
    import math
    expect = 0.5 * (1 / 1.4 + (4 / 7) ** 2 - 1.0 + math.log(1.4))
    assert abs(float(s.free_energy_contribution().item()) - expect) < 1e-6
    assert abs(expect - 0.188644) < 1e-5
    st = s.posterior()
    assert st.dim == 1 and abs(float(st.cov[0, 0].item()) - 1 / 1.4) < 1e-6
    with pytest.raises(ValueError):
        s.update(torch.zeros(3))  # odd length cannot split into ys/pred


def test_five_member_ledger_mixed_cadence():
    """quantum + phi + agent + world + scientist: total == sum, no lockstep."""
    from eci.aikernel.state_contract import KernelLedger
    from eci.cognition.aikernel_adapter import ScientistContributor, WorldModelContributor
    from eci.cognition.world_model import WorldModelConfig
    from eci.consciousness.aikernel_adapter import PhiContributor
    from eci.governance.aikernel_adapter import AgentContributor
    from eci.quantum.aikernel_adapter import VQEContributor, tfi_hamiltonian
    torch.manual_seed(0)
    vqe_c = VQEContributor(tfi_hamiltonian(2), 2, e_target=-3.2)
    phi_c = PhiContributor(dim=2)
    gov_c = AgentContributor("gov-6", 1, obs_noise=0.5)
    world_c = WorldModelContributor(WorldModelConfig(obs_dim=4, act_dim=2, hidden=16, latent=4))
    sci_c = ScientistContributor("h6", "y=a*x+b", 2)
    led = KernelLedger()
    for name, m in (("vqe", vqe_c), ("phi", phi_c), ("gov", gov_c),
                    ("world", world_c), ("sci", sci_c)):
        led.register(name, m)
    assert set(led.shares()) == {"vqe", "phi", "gov", "world", "sci"}
    tr = torch.cat([torch.randn(4), torch.zeros(2), torch.tensor([0.2]), torch.randn(4)])
    for step in range(4):
        vqe_c.step()                                        # every step
        if step % 2 == 0:
            phi_c.update(torch.randn(8, 2))                 # medium cadence
            world_c.update(tr)                              # medium cadence
        if step % 3 == 0:
            gov_c.update(torch.tensor([0.3]))               # slow cadence
            sci_c.update(torch.tensor([0.5, -0.5, 0.0, 0.0]))
        total = float(led.total_free_energy().detach().item())
        assert abs(total - sum(led.shares().values())) < 1e-4, (total, led.shares())


def test_bridge_accepts_new_adapters_with_shared_schema():
    """Phase-5 bridge is generic: new adapters register with one schema."""
    from eci.aikernel.mcp_bridge import STATE_SCHEMA, build_unification, register_contributor
    from eci.cognition.aikernel_adapter import ScientistContributor, WorldModelContributor
    from eci.cognition.world_model import WorldModelConfig
    from eci.mcp.registry import McpRegistry
    reg = McpRegistry()
    register_contributor(reg, "world", WorldModelContributor(WorldModelConfig(4, 2, 16, 4)))
    register_contributor(reg, "sci", ScientistContributor("hb", "y=a*x+b", 2))
    assert reg.get("aik.world.update").descriptor()["inputSchema"] == STATE_SCHEMA
    assert reg.get("aik.sci.update").descriptor()["inputSchema"] == STATE_SCHEMA
    assert "aik.world.free_energy" in reg.names()
    built = build_unification()
    assert set(built["ledger"].members()) >= {"quantum", "phi", "agent"}


def test_world_cold_start_share_is_deterministic():
    """Regression (Phase 7 calibration): pre-update share read twice must
    agree exactly — an unseeded forward sample drifted 0.24 -> 0.94."""
    import torch
    from eci.cognition.aikernel_adapter import WorldModelContributor
    from eci.cognition.world_model import WorldModelConfig
    torch.manual_seed(0)
    w = WorldModelContributor(WorldModelConfig(4, 2, 16, 4))
    a = float(w.free_energy_contribution().item())
    b = float(w.free_energy_contribution().item())
    assert a == b and a == a and abs(a) < 1e6, (a, b)
