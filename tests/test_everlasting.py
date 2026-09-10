"""Everlasting v7: capability security, proofs, continuum, MAPE-K, compat, futura, redteam."""
import asyncio
import time


def test_caps_attenuate_only_narrows():
    from eci.caps import CapToken, Issuer
    iss = Issuer()
    tok, ser = iss.mint("root", "ns:mesh/*", "act:tool.*")
    assert iss.verify(ser, action="tool.vote", namespace="mesh/a")["ok"] is True
    # attenuation: narrow to read-only + expiry
    child = tok.attenuate(iss._roots["root"], "act:tool.read", f"exp:{time.time() + 60}")
    cser = child.serialize()
    assert iss.verify(cser, action="tool.read", namespace="mesh/a")["ok"] is True
    denied = iss.verify(cser, action="tool.vote", namespace="mesh/a")
    assert denied["ok"] is False and "outside" in denied["error"]
    # forgery: flip a caveat without re-chaining
    evil = CapToken(child.tid, child.issuer, ["act:*"], child.sig)
    assert iss.verify(evil.serialize(), action="tool.vote")["ok"] is False
    # budget + epoch + expiry enforced
    _, bser = iss.mint("r2", "budget:5.0")
    assert iss.verify(bser, spend=9.0)["ok"] is False
    _, eser = iss.mint("r3", f"exp:{time.time() - 1}")
    assert iss.verify(eser)["ok"] is False
    assert iss.verify("!!!not-base64!!!")["ok"] is False


def test_watchtower_invariants_and_response():
    from eci.verify import Monitor, Watchtower, seal_proof, verify_proof
    w = Watchtower()
    w.watch(Monitor("no-harm", "never", "harm", lambda p: p.get("bad", False)))
    w.watch(Monitor("attest-then-vote", "bounded-response", "attest", lambda p: True, bound=3),
            response_match="vote")
    assert w.observe("harm", {"bad": False}) == []
    assert w.observe("harm", {"bad": True}) == ["no-harm"]
    w.observe("attest", {})
    assert w.observe("vote", {}) == []  # answered in time
    w.observe("attest", {})
    w.observe("nop", {})
    w.observe("nop", {})
    w.observe("nop", {})
    assert w.observe("nop", {}) == ["attest-then-vote"]  # deadline missed
    assert w.health()["violations"] == 2
    # proof receipts round-trip offline
    pr = seal_proof("vote", "p0/0.1.0",
                    [{"check": "quorum_met", "with": {"approvals": 3, "required": 3}, "ok": True},
                     {"check": "attested", "with": {"attestation_ok": True}, "ok": True}])
    assert verify_proof(pr, "p0/0.1.0")["ok"] is True
    assert verify_proof(pr, "p0/9.9.9")["ok"] is False
    tampered = dict(pr)
    tampered["action"] = "self_modify"
    assert verify_proof(tampered)["ok"] is False


def test_continuum_chain_and_replay():
    from eci.continuum import Continuum
    c = Continuum()
    c.snapshot({"ledger": [1, 2]}, note="genesis-epoch")
    c.snapshot({"ledger": [1, 2, 3]}, note="second")
    assert c.verify_chain()["ok"] is True
    assert len(c.autobiography()) == 2
    evs = [{"d": 1}, {"d": 2}, {"d": 3}]
    import hashlib
    import json
    expect = hashlib.sha256(json.dumps({"n": 3, "total": 6}, sort_keys=True).encode()).hexdigest()
    r = c.replay_check(evs, lambda s, e: {"n": s["n"] + 1, "total": s["total"] + e["d"]},
                       {"n": 0, "total": 0}, expect)
    assert r["ok"] is True and r["events"] == 3
    bad = c.replay_check(evs, lambda s, e: s, {}, "0" * 64)
    assert bad["ok"] is False
    # tamper evident
    c._chain[0].digests["ledger"] = "x"
    assert c.verify_chain()["ok"] is False


def test_mapek_cycle_ladder_and_compensation():
    from eci.mapek import MAPEK
    m = MAPEK()
    m.defaults()
    calm = asyncio.run(m.cycle({"errors": 0.0, "dlq": 0.0}))
    assert calm["breaches"] == [] and calm["rung"] == "normal"
    storm = asyncio.run(m.cycle({"errors": 99.0, "dlq": 99.0}))
    assert "error-rate" in storm["breaches"] and storm["applied"]
    assert storm["rung"] in ("throttled", "safe-mode")
    # failing strategy triggers compensation path without crashing the cycle
    from eci.mapek import Strategy
    m2 = MAPEK()
    from eci.mapek import SLO
    m2.add_slo(SLO("x", "x", 1.0))
    m2.add_strategy(Strategy("boom", lambda n: True, lambda: {},
                             lambda: 1 / 0, lambda: None))
    r = asyncio.run(m2.cycle({"x": 5.0}))
    assert r["plans"][0]["strategy"] == "boom" and "error" in r["plans"][0]


def test_compat_fail_closed_and_migrate():
    from eci.compat import CompatRegistry, Interface
    c = CompatRegistry()
    c.publish(Interface("eci.mcp", "1.4.0"))
    assert c.check("eci.mcp", "1.0.0")["ok"] is True
    assert "major" in c.check("eci.mcp", "2.0.0")["error"]
    assert "minor" in c.check("eci.mcp", "1.9.0")["error"]
    assert c.check("eci.nope", "1.0.0")["ok"] is False
    c.adapt("eci.mcp", "1.0.0", lambda d: {**d, "migrated": True})
    assert c.migrate("eci.mcp", {"a": 1}, "1.0.0")["data"]["migrated"] is True
    c.deprecate("eci.mcp", sunset_epoch=3, receipt="twin-1")
    assert "deprecated" in c.check("eci.mcp", "1.0.0")["warn"]
    assert c.check("eci.mcp", "1.0.0", epoch=9)["ok"] is False  # sunset enforced


def test_futura_markets_sortition_sunset():
    from eci.futura import EmergencyPowers, Futarchy, Sortition
    f = Futarchy(threshold=0.6)
    f.propose("p1", "mesh stays healthy")
    f.bet("alice", "p1", "yes", 10.0)
    out = f.close("p1")
    assert out["enacted"] == (out["prob"] >= 0.6)
    s = Sortition()
    d = s.draw(["a", "b", "c", "d", "e"], 2, seed="epoch-9")
    assert len(d["panel"]) == 2 and d["verify"] is True
    assert Sortition.verify(["a", "b", "c", "d", "e"], 2, "epoch-9", d["panel"]) is True
    assert Sortition.verify(["a", "b", "c", "d", "e"], 2, "other-seed", d["panel"]) is False
    ep = EmergencyPowers(epoch_fn=lambda: 10)
    ep.grant("egress", "ops", ttl_epochs=2, reason="drill")
    assert len(ep.alive(holder="ops")) == 1
    ep2 = EmergencyPowers(epoch_fn=lambda: 99)
    ep2.grants = ep.grants
    assert ep2.sweep()["owed_postmortems"] == [{"holder": "ops", "scope": "egress"}]
    assert ep2.postmortem("ops", "egress", "all clear") is True


def test_redteam_falsify_forecast_contradict():
    from eci.redteam import Challenger, ForecasterRegistry, contradiction_scan
    ch = Challenger(seed=0)
    probes = ch.falsify("markets always calm", context="epoch-3")
    assert [p.kind for p in probes] == ["negation", "boundary", "cross-source"]
    fr = ForecasterRegistry()
    a = fr.predict("alice", "rain", 0.8)
    b = fr.predict("bob", "rain", 0.2)
    assert fr.resolve(a, True)["brier"] < fr.resolve(b, True)["brier"]
    assert fr.leaderboard()[0]["forecaster"] == "alice"
    disputes = contradiction_scan([
        {"subject": "x", "predicate": "is", "object": "safe", "confidence": 0.9, "fid": "1"},
        {"subject": "x", "predicate": "is", "object": "hostile", "confidence": 0.8, "fid": "2"},
        {"subject": "y", "predicate": "is", "object": "safe", "confidence": 0.2},
    ])
    assert len(disputes) == 1 and set(disputes[0]["rivals"]) == {"safe", "hostile"}


def test_framework_and_mcp_ever_wiring():
    from eci.framework import ECIFramework
    fw = ECIFramework()
    st = fw.system_status()
    for k in ("caps", "watchtower", "continuum", "mapek", "compat", "futarchy"):
        assert k in st, k
    s = fw.mcp.request("sessions/create", {"subject": "operator", "capabilities": ["*"]})
    sid = s["result"]["session_id"]
    for t in ("ever.caps", "ever.proof", "ever.mapek", "ever.continuum",
              "ever.compat", "ever.futura", "ever.redteam"):
        assert t in fw.mcp.server.registry.names(), t
    r = fw.mcp.request("tools/call", {"name": "ever.compat",
                                      "arguments": {"interface": "eci.mcp", "required": "1.0.0"},
                                      "session_id": sid})
    assert r["result"]["ok"] is True and r["result"]["data"]["ok"] is True
    m = fw.mcp.request("tools/call", {"name": "ever.mapek",
                                      "arguments": {"metrics": {"errors": 0.0}},
                                      "session_id": sid})
    assert m["result"]["ok"] is True and m["result"]["data"]["rung"] == "normal"
