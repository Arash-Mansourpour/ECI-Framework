"""Phase 5 — MCP as the faithful transport for the unification layer.

Proves, with numbers: (1) GenerativeState survives the wire exactly
(rho included); (2) all aik.* tools share one schema; (3) driving
observations through MCP tools moves the SAME contributor instances the
direct path reads, so ledger totals via MCP == via direct calls exactly.
"""
import pytest
import torch


@pytest.fixture(scope="module")
def live():
    from eci.framework import ECIFramework
    fw = ECIFramework()
    mcp = fw.mcp
    s = mcp.request("sessions/create", {"subject": "operator", "capabilities": ["*"],
                                        "budget": 500.0})
    return {"fw": fw, "mcp": mcp, "sid": s["result"]["session_id"],
            "aik": fw._aik}


def _call(mcp, sid, name, args):
    r = mcp.request("tools/call", {"name": name, "arguments": args, "session_id": sid})
    assert r["result"]["ok"] is True, (name, r["result"])
    return r["result"]["data"]


def test_wire_roundtrip_preserves_rho():
    """to_dict -> JSON -> from_dict: mu/cov/rho/paulis/meta all survive."""
    import json

    from eci.aikernel.generative_model import GenerativeState
    torch.manual_seed(0)
    rho = torch.randn(4, 4, dtype=torch.complex64)
    rho = rho @ rho.conj().T
    rho = rho / torch.trace(rho).real
    st = GenerativeState.from_density(rho, 2)
    st.meta["probe"] = "wire"
    d = json.loads(json.dumps(st.to_dict()))  # the actual wire: JSON numbers
    assert set(d) >= {"dim", "mu", "cov", "n_qubits", "paulis", "meta",
                      "rho_real", "rho_imag"}
    back = GenerativeState.from_dict(d)
    assert torch.allclose(back.mu, st.mu) and torch.allclose(back.cov, st.cov)
    assert torch.allclose(back.rho, st.rho) and back.n_qubits == 2
    assert back.paulis == st.paulis and back.meta == {"probe": "wire"}
    # Gaussian-only states + legacy dicts (no rho_* keys) still load
    g = GenerativeState(torch.zeros(3), torch.eye(3))
    assert GenerativeState.from_dict(g.to_dict()).rho is None
    assert GenerativeState.from_dict({"mu": [0.0], "cov": [[1.0]]}).dim == 1
    with pytest.raises(ValueError):
        GenerativeState.from_dict({"mu": [0.0], "cov": [[1.0]],
                                   "rho_real": [[1.0, 0.0], [0.0, 1.0]],
                                   "rho_imag": [[0.0]],
                                   "n_qubits": 1})


def test_one_schema_across_namespaces(live):
    reg = live["mcp"].server.registry
    updates = [reg.get(f"aik.{ns}.update").descriptor() for ns in
               ("quantum", "phi", "agent", "noisy")]
    assert all(u["inputSchema"] == updates[0]["inputSchema"] for u in updates)
    assert set(updates[0]["inputSchema"]["properties"]) == {"observation", "options"}
    posts = [reg.get(f"aik.{ns}.posterior").descriptor() for ns in
             ("quantum", "phi", "agent", "noisy")]
    assert all(p["inputSchema"] == posts[0]["inputSchema"] for p in posts)
    assert all(u["annotations"]["readOnlyHint"] is False for u in updates)
    assert all(p["annotations"]["readOnlyHint"] is True for p in posts)


def test_end_to_end_mcp_matches_direct(live):
    """Same instances, same math: MCP total == direct total after MCP-driven updates."""
    import random
    mcp, sid, aik = live["mcp"], live["sid"], live["aik"]
    ledger = aik["ledger"]
    assert set(ledger.members()) >= {"quantum", "phi", "agent"}
    rng = random.Random(7)
    # drive one observation per subsystem THROUGH the MCP transport
    _call(mcp, sid, "aik.quantum.update", {"observation": [-2.5]})
    window = [[rng.gauss(0, 1), rng.gauss(0, 1)] for _ in range(8)]
    _call(mcp, sid, "aik.phi.update", {"observation": window})
    _call(mcp, sid, "aik.agent.update", {"observation": [0.4]})
    via_mcp = _call(mcp, sid, "aik.ledger.total", {})
    direct = float(ledger.total_free_energy().detach().item())
    assert abs(via_mcp["total_free_energy"] - direct) < 1e-9, (via_mcp, direct)
    assert set(via_mcp["members"]) >= {"quantum", "phi", "agent"}
    shares_mcp = _call(mcp, sid, "aik.ledger.shares", {})["shares"]
    shares_direct = {k: float(v) for k, v in ledger.shares().items()}
    assert set(shares_mcp) == set(shares_direct)
    for k in shares_direct:
        assert abs(shares_mcp[k] - shares_direct[k]) < 1e-9, (k, shares_mcp, shares_direct)
    assert abs(sum(shares_direct.values()) - direct) < 1e-6


def test_posterior_over_wire_matches_direct(live):
    """Quantum-backed posterior through MCP carries rho and matches direct."""
    import json

    from eci.aikernel.generative_model import GenerativeState
    mcp, sid, aik = live["mcp"], live["sid"], live["aik"]
    wire = _call(mcp, sid, "aik.quantum.posterior", {})
    wire = json.loads(json.dumps(wire))  # force real JSON Fidelity
    back = GenerativeState.from_dict(wire)
    assert back.rho is not None and back.n_qubits == 2
    direct = aik["contributors"]["quantum"].posterior().to_dict()
    assert torch.allclose(back.mu, torch.as_tensor(direct["mu"]), atol=1e-6)
    assert torch.allclose(back.cov, torch.as_tensor(direct["cov"]), atol=1e-5)


def test_update_rejects_missing_observation(live):
    mcp, sid = live["mcp"], live["sid"]
    r = mcp.request("tools/call", {"name": "aik.agent.update",
                                   "arguments": {}, "session_id": sid})
    assert r["result"]["ok"] is False and r["result"]["stage"] == "execute"
