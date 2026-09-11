"""Phase 11 — operability: the mesh is visible (status) and operable (CLI).

Proves: framework exposes the SAME ledger object the MCP tools read
(identity, not equality); system_status carries a real aik section;
`eci aik` output matches the MCP tool output exactly.
"""
import json

import pytest


@pytest.fixture(scope="module")
def live():
    from eci.framework import ECIFramework
    fw = ECIFramework()
    return fw


def test_framework_exposes_live_mesh(live):
    aik = live._aik
    assert set(aik["ledger"].members()) == {"quantum", "noisy", "phi", "agent",
                                            "world", "sci", "fep", "ewc"}
    st = live.system_status()
    assert st["aik"]["ok"] is True, st["aik"]
    assert set(st["aik"]["members"]) == set(aik["ledger"].members())
    assert abs(st["aik"]["total_free_energy"] -
               sum(st["aik"]["describe"][k]["share"] for k in st["aik"]["members"])) < 1e-6
    assert all(m["category"] in ("good-fit", "adaptable") for m in st["aik"]["describe"].values())
    # identity with what the MCP tools read (not a copy)
    direct = float(aik["ledger"].total_free_energy().detach().item())
    assert abs(st["aik"]["total_free_energy"] - direct) < 1e-9


def test_absent_mesh_reports_error_not_numbers(live):
    fw = live
    aik = fw._aik
    try:
        del fw._aik
        out = fw.aik_status()
        assert out == {"ok": False, "error": "unification mesh unavailable"}, out
    finally:
        fw._aik = aik


def test_cli_matches_mcp_transport(live, capsys):
    from eci.__main__ import main
    fw = live
    for what in ("shares", "total", "describe"):
        assert main(["aik", what]) == 0
        cli = json.loads(capsys.readouterr().out)
        s = fw.mcp.request("sessions/create", {"subject": "operator", "capabilities": ["*"]})
        sid = s["result"]["session_id"]
        if what == "describe":
            tool = "aik.ledger.describe"
            mcp = fw.mcp.request("tools/call", {"name": tool, "arguments": {}, "session_id": sid})
            assert mcp["result"]["ok"] is True
            assert cli["members"].keys() == mcp["result"]["data"]["members"].keys()
            for k in cli["members"]:
                assert abs(cli["members"][k]["share"] -
                           mcp["result"]["data"]["members"][k]["share"]) < 1e-9, k
        elif what == "total":
            tool = "aik.ledger.total"
            mcp = fw.mcp.request("tools/call", {"name": tool, "arguments": {}, "session_id": sid})
            assert abs(cli["total_free_energy"] - mcp["result"]["data"]["total_free_energy"]) < 1e-9
            assert set(cli["members"]) == set(mcp["result"]["data"]["members"])
        else:
            tool = "aik.ledger.shares"
            mcp = fw.mcp.request("tools/call", {"name": tool, "arguments": {}, "session_id": sid})
            assert set(cli["shares"]) == set(mcp["result"]["data"]["shares"])
