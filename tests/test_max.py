"""Max-tech batch: challenge, egress, gossip, reputation, bench-v2, qrng, key-memory."""
import pytest

from eci.benchmarking.obedience import BENCH_SUITE_V2, run_bench_v2
from eci.consciousness.challenge import grade, issue, to_dict
from eci.network.gossip import GossipNode, anti_entropy
from eci.network.reputation import Reputation, ReputationBoard
from eci.protocol0.egress import EgressFilter, scrub
from eci.protocol0.ledger import Ledger
from eci.protocol0.middleware import Middleware
from eci.protocol0.spec import load_spec
from eci.quantum.key_memory import distance_for_target, memory_cost
from eci.quantum.qrng import health_check, mix


def test_challenge_evidence():
    ch = issue(8, seed=0)
    t = grade(ch, lambda c: c.target)  # perfect agent
    assert t.score() == 1.0
    t2 = grade(ch, lambda c: 1.0 - c.target)  # adversarial mirror
    assert t2.score() < 0.5
    assert to_dict(t)["n"] == 8


def test_egress_scrub_and_floor():
    spec = load_spec()
    gate = Middleware(spec, mode="enforce", ledger=Ledger())
    gate.bind("a", awareness=0.9, obedience=0.9, trust=0.9)
    f = EgressFilter(gate, challenge_floor=0.5)
    r = f.inspect("a", "execute_tool", "token ghp_abc123XYZ4567890 done", challenge_score=0.9)
    assert r["redacted"] >= 1 and "ghp_" not in r["payload"]
    with pytest.raises(PermissionError):
        f.inspect("a", "execute_tool", "hi", challenge_score=0.1)


def test_gossip_heals_partition():
    nodes = {f"n{i}": GossipNode(f"n{i}", ({s: f"r{s}" for s in range(6)} if i < 2 else {})) for i in range(4)}
    rep = anti_entropy(nodes, rounds=8, seed=0)
    assert rep["converged"] is True and rep["records"] == 6


def test_reputation_forgets():
    b = ReputationBoard()
    b.observe("good", trust=1.0, obedience=1.0)
    b.observe("bad", trust=0.1, obedience=0.0)
    w = b.weights()
    assert w["good"] > w["bad"]
    for _ in range(200):
        b.tick()
    assert b.weights()["good"] < w["good"]  # freshness decayed
    assert Reputation(stake=2.0, trust=1.0, obedience=1.0).weight() > Reputation(stake=1.0, trust=1.0, obedience=1.0).weight()


def test_bench_v2_200():
    assert len(BENCH_SUITE_V2) == 200
    rep = run_bench_v2("saint", "0.1.0", lambda p: not p.must_refuse)
    assert rep.n == 200 and rep.accuracy > 0.99
    rogue = run_bench_v2("rogue", "0.1.0", lambda p: True)
    assert rogue.accuracy < rep.accuracy


def test_qrng_and_key_memory():
    assert health_check(mix(64))["ok"] is True
    r = distance_for_target(0.001)
    assert r["feasible"] and r["distance"] % 2 == 1
    assert distance_for_target(0.99)["feasible"] is False
    m = memory_cost(0.001)
    assert m["bb_qubits"] < m["surface_qubits"]
