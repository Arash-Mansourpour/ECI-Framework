"""Omniverse MCP Fabric: registry, sessions, pipeline, protocol, federation."""

import pytest


@pytest.fixture(scope="module")
def fabric():
    from eci.framework import ECIFramework
    fw = ECIFramework()
    return fw.mcp, fw


def test_registry_has_namespaced_toolset(fabric):
    mcp, fw = fabric
    names = mcp.server.registry.names()
    for t in ("p0.attest", "p0.check", "p0.spec", "p0_attest", "p0_check",
              "system.status", "quantum.transpile", "quantum.zne",
              "consciousness.validate", "network.probe", "workflow.run",
              "agent.run", "memory.store", "dao.propose", "treasury.ops",
              "eval.gates", "supply.sbom", "twin.simulate", "chaos.run"):
        assert t in names, t
    d = mcp.server.registry.get("quantum.zne").descriptor()
    assert d["inputSchema"]["type"] == "object"
    assert d["annotations"]["readOnlyHint"] is True
    assert mcp.server.registry.get("dao.propose").descriptor()["annotations"]["readOnlyHint"] is False


def test_initialize_and_tools_list_filter(fabric):
    mcp, fw = fabric
    r = mcp.request("initialize", {})
    assert r["result"]["protocolVersion"] == "2024-11-05"
    assert r["result"]["capabilities"]["dryRun"] is True
    r2 = mcp.request("tools/list", {"prefix": "quantum."})
    names = [t["name"] for t in r2["result"]["tools"]]
    assert names and all(n.startswith("quantum.") for n in names)


def test_p0_check_allow_and_unknown_tool(fabric):
    mcp, fw = fabric
    ok = mcp.request("tools/call", {"name": "p0.check",
                                    "arguments": {"action": "vote", "awareness": 0.9, "obedience": 0.9, "trust": 0.9}})
    assert ok["result"]["ok"] is True and ok["result"]["data"]["allow"] is True
    deny = mcp.request("tools/call", {"name": "p0.check",
                                      "arguments": {"action": "self_modify", "awareness": 0.0, "obedience": 0.0, "trust": 0.0}})
    assert deny["result"]["data"]["allow"] is False
    bad = mcp.request("tools/call", {"name": "nope.nope", "arguments": {}})
    assert bad["result"]["ok"] is False


def test_sessions_budget_and_idempotency(fabric):
    mcp, fw = fabric
    s = mcp.request("sessions/create", {"subject": "operator", "capabilities": ["*"], "budget": 100.0})
    sid = s["result"]["session_id"]
    i1 = mcp.request("tools/call", {"name": "p0.spec", "arguments": {},
                                    "session_id": sid, "idempotency_key": "k-1"})
    assert i1["result"]["ok"] is True and i1["result"].get("cached") is not True
    i2 = mcp.request("tools/call", {"name": "p0.spec", "arguments": {},
                                    "session_id": sid, "idempotency_key": "k-1"})
    assert i2["result"].get("cached") is True
    poor = mcp.request("sessions/create", {"subject": "operator", "capabilities": ["*"], "budget": 0.1})
    psid = poor["result"]["session_id"]
    r = mcp.request("tools/call", {"name": "p0.spec", "arguments": {}, "session_id": psid})
    assert r["result"]["ok"] is False and r["result"]["stage"] == "budget"
    info = mcp.request("sessions/info", {"session_id": sid})
    assert info["result"]["calls"] >= 1


def test_auth_deny_for_anon_on_guarded_tool(fabric):
    mcp, fw = fabric
    r = mcp.request("tools/call", {"name": "agent.run", "arguments": {"goal": "x"}})
    assert r["result"]["ok"] is False and r["result"]["stage"] == "auth"


def test_dry_run_mutating_tool_changes_nothing(fabric):
    mcp, fw = fabric
    before = len(fw.dao.proposals)
    s = mcp.request("sessions/create", {"subject": "operator", "capabilities": ["*"]})
    sid = s["result"]["session_id"]
    r = mcp.request("tools/call", {"name": "dao.propose",
                                   "arguments": {"title": "dry", "proposer": "mcp"},
                                   "session_id": sid, "dry_run": True})
    assert r["result"]["ok"] is True and r["result"]["stage"] == "dry_run"
    assert len(fw.dao.proposals) == before


def test_agent_run_end_to_end_via_operator_session(fabric):
    mcp, fw = fabric
    s = mcp.request("sessions/create", {"subject": "operator", "capabilities": ["*"], "budget": 100.0})
    r = mcp.request("tools/call", {"name": "agent.run",
                                   "arguments": {"goal": "mcp-e2e", "agent_id": "agent-0",
                                                 "budget": 20.0, "max_steps": 3},
                                   "session_id": s["result"]["session_id"]})
    assert r["result"]["ok"] is True
    assert r["result"]["data"]["ok"] is True


def test_prompts_and_resources(fabric):
    mcp, fw = fabric
    pl = mcp.request("prompts/list", {})
    assert any(p["name"] == "obedience-check" for p in pl["result"]["prompts"])
    pg = mcp.request("prompts/get", {"name": "obedience-check", "arguments": {"action": "vote"}})
    assert "vote" in pg["result"]["messages"][0]["content"]
    rl = mcp.request("resources/list", {})
    assert any(r["uri"] == "eci://system.status" for r in rl["result"]["resources"])
    rr = mcp.request("resources/read", {"uri": "eci://sbom"})
    assert rr["result"]["ok"] is True and "components" in rr["result"]["data"]
    bad = mcp.request("resources/read", {"uri": "eci://nope"})
    assert bad["result"]["ok"] is False


def test_federation_prefix_and_breaker():
    import asyncio

    from eci.mcp.federation import FederatedUpstream, Federation
    fed = Federation()
    async def remote(tool, args):
        assert tool == "echo"
        return {"echo": args.get("x")}
    fed.add(FederatedUpstream(prefix="ext", call_remote=remote))
    out = asyncio.run(fed.call("ext.echo", {"x": 1}))
    assert out == {"echo": 1}
    with pytest.raises(PermissionError):
        fed2 = Federation()
        async def r2(t, a): return {}
        fed2.add(FederatedUpstream(prefix="p", call_remote=r2, allow=["other.*"]))
        asyncio.run(fed2.call("p.secret", {}))


def test_bridges_and_framework_wiring(fabric):
    mcp, fw = fabric
    assert fw.mcp.health()["ok"] is True
    st = fw.system_status()
    for k in ("mcp", "agents", "treasury", "data"):
        assert k in st, k
    assert "v1/system.status" in fw.gateway.paths()


def test_legacy_stdio_shim_compat():
    import importlib.util
    from pathlib import Path
    shim_path = Path(__file__).resolve().parents[1] / "mcp" / "server.py"
    spec = importlib.util.spec_from_file_location("eci_legacy_mcp_shim", shim_path)
    legacy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(legacy)
    r = legacy.handle({"id": 7, "method": "tools/call",
                       "params": {"name": "p0_check",
                                  "arguments": {"action": "vote", "awareness": 0.9, "obedience": 0.9, "trust": 0.9}}})
    assert r["id"] == 7 and r["result"]["ok"] is True
    rl = legacy.handle({"id": 8, "method": "tools/list", "params": {}})
    names = [t["name"] for t in rl["result"]["tools"]]
    assert "p0.check" in names and "agent.run" in names


def test_deep_systems_wired(fabric):
    mcp, fw = fabric
    # treasury via MCP
    s = mcp.request("sessions/create", {"subject": "operator", "capabilities": ["*"]})
    sid = s["result"]["session_id"]
    r = mcp.request("tools/call", {"name": "treasury.ops", "arguments": {"op": "status"}, "session_id": sid})
    assert r["result"]["ok"] is True and "pool" in r["result"]["data"]
    # eval + sbom + chaos + twin via MCP
    assert mcp.request("tools/call", {"name": "supply.sbom", "arguments": {}, "session_id": sid})["result"]["ok"] is True
    tw = mcp.request("tools/call", {"name": "twin.simulate", "arguments": {"name": "t"}, "session_id": sid})
    assert tw["result"]["ok"] is True
    ch = mcp.request("tools/call", {"name": "chaos.run", "arguments": {"faults": ["delay"]}, "session_id": sid})
    assert ch["result"]["ok"] is True
    # quantum helpers direct
    from eci.quantum.backend import SimBackend, transpile, zne_extrapolate
    assert SimBackend(2, shots=64).run([0.5, 0.5]).shots == 64
    assert transpile(["CNOT", "CNOT", "H"])["cancelled"] == 1
    assert zne_extrapolate([1.0, 3.0], [0.9, 0.7])["mitigated"] is True
    # tcp transport object constructs (no bind in unit test)
    from eci.network.tcp import FramedTcpTransport
    assert FramedTcpTransport("t").health()["ok"] is True


def test_eval_gates_all_green():
    from eci.eval import run_gates
    rep = run_gates().to_dict()
    assert rep["ok"] is True, rep["gates"]
    assert rep["passed"] == 4
