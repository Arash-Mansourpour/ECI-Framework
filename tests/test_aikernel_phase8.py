"""Phase 8 — EWCContributor: consolidated weight beliefs as contributor.

Calibrated (seeded, Linear(2,2), 32 synthetic samples): fisher_total
0.8596; share 0.0 at optimum; +0.5 perturb -> share 0.042981; posterior
variance == 1/(0.4*F+1) exactly in float32.
"""
import pytest
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset


def _setup():
    from eci.learning.aikernel_adapter import EWCContributor
    from eci.learning.continual import ElasticWeightConsolidation
    torch.manual_seed(0)
    model = nn.Linear(2, 2)
    X = torch.randn(32, 2)
    y = (X[:, 0] > 0).long()
    dl = DataLoader(TensorDataset(X, y), batch_size=8)
    ewc = ElasticWeightConsolidation(model, lambda_ewc=0.4)
    return EWCContributor(ewc), model, dl


def test_fresh_conforms_with_zero_share():
    from eci.aikernel.state_contract import conforms
    c, _, _ = _setup()
    assert conforms(c) is True
    assert float(c.free_energy_contribution().item()) == 0.0
    assert c.posterior().dim == 6  # Linear(2,2): 4 weights + 2 biases
    with pytest.raises(ValueError):
        from eci.learning.aikernel_adapter import EWCContributor
        from eci.learning.continual import ElasticWeightConsolidation
        EWCContributor(ElasticWeightConsolidation(nn.Linear(1, 1)), prior_prec=0.0)
    with pytest.raises(ValueError):
        c.update(torch.zeros(5))


def test_consolidate_then_displacement_prices():
    c, model, dl = _setup()
    rep = c.consolidate(dl)
    assert rep["fisher_total"] > 0.0
    assert float(c.free_energy_contribution().item()) == 0.0  # at optimum
    flat0 = torch.cat([p.detach().reshape(-1) for p in model.parameters()])
    with torch.no_grad():
        for p in model.parameters():
            p.add_(0.5)
    got = float(c.free_energy_contribution().item())
    assert got > 0.0
    # same engine call, second path: no drift (exact same tensor math)
    assert abs(got - float(c.ewc.ewc_loss().item())) < 1e-9, got
    with torch.no_grad():
        for p in model.parameters():
            p.add_(0.5)
    assert float(c.free_energy_contribution().item()) > got  # monotone in displacement
    # posterior tracks the snapshot (optpar still pre-perturb until update)
    st = c.update(flat0 + 0.5)
    assert torch.allclose(st.mu, flat0 + 0.5, atol=1e-6)


def test_posterior_variance_closed_form():
    c, model, dl = _setup()
    c.consolidate(dl)
    st = c.posterior()
    F = torch.cat([c.ewc.fisher_dict[k].reshape(-1) for k, _ in model.named_parameters()])
    expect = 1.0 / (0.4 * F.float() + 1.0)
    assert torch.allclose(st.cov.diag(), expect, atol=1e-6)


def test_ledger_with_ewc_member_and_bridge_schema():
    from eci.aikernel.mcp_bridge import STATE_SCHEMA, register_contributor
    from eci.aikernel.state_contract import KernelLedger
    from eci.governance.aikernel_adapter import AgentContributor
    from eci.mcp.registry import McpRegistry
    c, _, _ = _setup()
    ag = AgentContributor("gov-8", 1, obs_noise=0.5)
    led = KernelLedger()
    led.register("ewc", c)
    led.register("gov", ag)
    ag.update(torch.tensor([0.3]))
    total = float(led.total_free_energy().detach().item())
    assert abs(total - sum(led.shares().values())) < 1e-6
    reg = McpRegistry()
    register_contributor(reg, "ewc", c)
    assert reg.get("aik.ewc.update").descriptor()["inputSchema"] == STATE_SCHEMA
    out = reg.get("aik.ewc.free_energy").handler({}, {})
    assert abs(out["free_energy"] - total + float(led.shares()["gov"])) < 1e-6
