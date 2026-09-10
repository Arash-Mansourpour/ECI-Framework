"""Phase 7 — FEPContributor: the native FEP agent as a contributor.

Calibrated (seeded, n_hidden=n_obs=4): pre-evidence share exactly 0.0;
after one perceive() on a random obs: share 2.599016 == recomputed
free_energy(obs) to 1e-12; posterior cov == (ΠAᵀA+I)⁻¹ to 1e-9.
"""
import torch


def test_fep_conforms_and_pre_evidence_share():
    from eci.aikernel.state_contract import conforms
    from eci.consciousness.aikernel_adapter import FEPContributor
    c = FEPContributor(4, 4)
    assert conforms(c) is True
    assert float(c.free_energy_contribution().item()) == 0.0
    assert c.posterior().dim == 4


def test_fep_share_is_its_own_objective():
    from eci.consciousness.aikernel_adapter import FEPContributor
    torch.manual_seed(0)
    c = FEPContributor(4, 4)
    obs = torch.randn(4, dtype=torch.float64)
    st = c.update(obs)
    share = float(c.free_energy_contribution().item())
    assert share > 0.0
    # same computation, second call path: must agree up to the float32
    # share convention (recompute is float64; 9.5e-8 measured, not drift)
    assert abs(share - float(c.agent.free_energy(obs).item())) < 1e-6, share
    # Laplace posterior covariance: exact closed form for its model
    A, P = c.agent.A.double(), c.agent.precision
    expect = torch.linalg.inv(P * (A.T @ A) + torch.eye(4, dtype=torch.float64))
    assert torch.allclose(st.cov.double(), expect, atol=1e-9)
    # perception descends residual toward least squares
    assert float(((obs - A @ c.agent.mu.double()) ** 2).sum().item()) < \
        float((obs ** 2).sum().item())
    import pytest
    with pytest.raises(ValueError):
        c.update(torch.zeros(3))  # wrong width


def test_fep_posterior_flows_through_mcp_schema():
    """The new adapter is wire-compatible with the Phase 5 schema."""
    from eci.aikernel.generative_model import GenerativeState
    from eci.aikernel.mcp_bridge import STATE_SCHEMA, register_contributor
    from eci.consciousness.aikernel_adapter import FEPContributor
    from eci.mcp.registry import McpRegistry
    reg = McpRegistry()
    register_contributor(reg, "fep", FEPContributor(2, 2))
    assert reg.get("aik.fep.update").descriptor()["inputSchema"] == STATE_SCHEMA
    out = reg.get("aik.fep.update").handler({"observation": [0.5, -0.5]}, {})
    assert GenerativeState.from_dict(out).dim == 2
