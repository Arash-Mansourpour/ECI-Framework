"""Phase 9 — complete default mesh: 8 adapters, one ledger, full describe."""
import torch

EXPECTED = {"quantum", "noisy", "phi", "agent", "world", "sci", "fep", "ewc"}


def test_default_mesh_has_all_eight():
    from eci.aikernel.mcp_bridge import build_unification
    built = build_unification()
    assert set(built["ledger"].members()) == EXPECTED
    tools = set(built["tools"])
    for ns in EXPECTED:
        assert {f"aik.{ns}.posterior", f"aik.{ns}.update", f"aik.{ns}.free_energy"} <= tools, ns
    assert {"aik.ledger.shares", "aik.ledger.total", "aik.ledger.describe"} <= tools
    total = float(built["ledger"].total_free_energy().detach().item())
    assert abs(total - sum(built["ledger"].shares().values())) < 1e-6


def test_describe_covers_all_members():
    from eci.aikernel.mcp_bridge import build_unification, register_ledger
    from eci.mcp.registry import McpRegistry
    built = build_unification()
    reg = McpRegistry()
    register_ledger(reg, built["ledger"])
    out = reg.get("aik.ledger.describe").handler({}, {})["members"]
    assert set(out) == EXPECTED
    assert all(m["category"] in ("good-fit", "adaptable") for m in out.values()), out
    assert all(m["note"] for m in out.values())
    assert out["phi"]["category"] == "adaptable"


def test_new_members_drive_and_ledger_stays_exact():
    from eci.aikernel.mcp_bridge import build_unification
    torch.manual_seed(0)
    built = build_unification()
    led, c = built["ledger"], built["contributors"]
    c["world"].update(torch.cat([torch.randn(4), torch.zeros(2),
                                 torch.tensor([0.2]), torch.randn(4)]))
    c["sci"].update(torch.tensor([0.5, -0.5, 0.0, 0.0]))
    c["fep"].update(torch.zeros(2, dtype=torch.float64))
    flat = torch.cat([p.detach().reshape(-1) for p in
                      c["ewc"].ewc.model.parameters()])
    c["ewc"].update(flat)
    total = float(led.total_free_energy().detach().item())
    assert abs(total - sum(led.shares().values())) < 1e-4, (total, led.shares())


def test_fabric_mesh_complete_end_to_end():
    """Full McpFabric carries the 8-member mesh; one MCP-driven update lands."""
    from eci.framework import ECIFramework
    fw = ECIFramework()
    names = set(fw.mcp.server.registry.names())
    for ns in EXPECTED:
        assert f"aik.{ns}.free_energy" in names, ns
    s = fw.mcp.request("sessions/create", {"subject": "operator", "capabilities": ["*"]})
    sid = s["result"]["session_id"]
    r = fw.mcp.request("tools/call", {"name": "aik.sci.update",
                                      "arguments": {"observation": [0.5, -0.5, 0.0, 0.0]},
                                      "session_id": sid})
    assert r["result"]["ok"] is True, r["result"]
    tot = fw.mcp.request("tools/call", {"name": "aik.ledger.total",
                                        "arguments": {}, "session_id": sid})["result"]["data"]
    direct = float(fw._aik["ledger"].total_free_energy().detach().item())
    assert abs(tot["total_free_energy"] - direct) < 1e-9, (tot, direct)
    assert set(tot["members"]) == EXPECTED
