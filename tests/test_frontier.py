"""Frontier batch: ZK bands, federation, HLC merge, economy, twin, recovery."""
import time

from eci.causal import HLC, hlc_now, merge_chains
from eci.economy import Economy
from eci.federation.bridge import Bridge, TranslationMap, anchor, translate_vote
from eci.protocol0.ledger import Ledger
from eci.protocol0.zk import issue_credential, prove, verify_proof
from eci.recovery import RecoveryRequest, combine, split
from eci.twin import what_if


def test_zk_band_not_value():
    c = issue_credential("alice", {"awareness": 0.65, "obedience": 0.9, "trust": 0.9})
    p = prove(c, "awareness", 0.5)
    v = verify_proof(c.published, p)
    assert v["ok"] is True and v["disclosed"] == {"awareness": ">=0.5"}
    # 0.8 band unprovable (absence = fail proof); exact value never disclosed
    try:
        prove(c, "awareness", 0.8)
        assert False, "should not prove unpassed band"
    except LookupError:
        pass
    assert all("0.65" not in str(x) for x in [p, v])


def test_federation_anchor_and_weights():
    la, lb = Ledger(), Ledger()
    la.append("genesis", {})
    b = Bridge("east", "west", TranslationMap({"vote": 0.5}), TranslationMap({"vote": 0.25}))
    r = anchor(b, la, lb)
    assert la.verify()["ok"] and lb.verify()["ok"]
    assert translate_vote(b, "east", "vote", 2.0) == 1.0
    assert translate_vote(b, "west", "vote", 2.0) == 0.5
    assert translate_vote(b, "east", "vote", -1.0) == 0.0


def test_hlc_merge_converges():
    a = HLC(100, 0, "a")
    b = hlc_now(a, "b", now_ms=100)
    assert (b.pt, b.logical) == (100, 1)
    c1 = {"hash": "h1", "hlc": {"pt": 1, "logical": 0, "node": "a"}, "body": 1}
    c2 = {"hash": "h2", "hlc": {"pt": 1, "logical": 0, "node": "b"}, "body": 2}
    m1 = merge_chains([c1], [c2])
    m2 = merge_chains([c2], [c1])
    assert [r["body"] for r in m1] == [r["body"] for r in m2] == [1, 2]
    assert m1[0]["prev"] == "GENESIS"


def test_economy_spam_costs_and_slash_bites():
    e = Economy()
    e.fund("alice", 100.0, stake=50.0)
    e.fund("spammer", 5.0, stake=50.0)
    assert e.charge("alice", "vote")["ok"] is True
    assert e.charge("spammer", "self_modify")["ok"] is False  # priced out
    assert e.slash("spammer")["slashed"] == 25.0
    e.epoch(["alice"])
    assert e.settlement()["total_credits"] > 0


def test_twin_verdict():
    rep = what_if("tighter-vote", {"min_obedience": 0.7}, [{"x": 1}] * 10,
                  lambda pol: {"obedience": 0.9 if pol else 0.8, "resilience": 0.95})
    assert rep["verdict"] == "adopt" and rep["replayed"] == 10
    bad = what_if("lax", {"min_obedience": 0.1}, [{"x": 1}], lambda pol: {"obedience": 0.5, "resilience": 0.5}
                  if pol.get("min_obedience", 1.0) < 0.5 else {"obedience": 0.8, "resilience": 0.95})
    assert bad["verdict"] == "reject"


def test_shamir_recovery_gates():
    secret = b"attest-key-32-bytes-padded!!!!!"
    shares = split(secret, n=5, k=3)
    assert combine(shares[:3]) == secret
    assert combine(shares[1:4]) == secret
    try:
        combine(shares[:2])
        assert False
    except ValueError:
        pass
    req = RecoveryRequest("alice", unlock_at=time.time() + 1000, shares=shares[:3])
    assert req.ready() is False
    try:
        req.attempt(True)
        assert False
    except PermissionError:
        pass
    req.unlock_at = time.time() - 1
    try:
        req.attempt(False)
        assert False
    except PermissionError:
        pass
    assert req.attempt(True) == secret
