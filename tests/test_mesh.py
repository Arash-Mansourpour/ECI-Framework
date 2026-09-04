"""Global mesh: DHT discovery, dynamic membership, ledger sync, rollout, health."""
from eci.health import metrics_text, status
from eci.network.dht import DHTNode, lookup
from eci.network.membership import Membership
from eci.protocol0.ledger import Ledger
from eci.rollout import RolloutPlan, staged_rollout


def test_dht_finds_anyone_without_bootstrap():
    net = {f"n{i}": DHTNode(f"n{i}") for i in range(12)}
    # Only ring-neighbor knowledge at start
    ids = list(net)
    for i, nid in enumerate(ids):
        net[nid].learn(ids[(i + 1) % len(ids)])
    holders = net["n0"].store("config", {"v": 1}, net)
    assert len(holders) >= 1
    ok, val = net["n11"].find_value("config", net)
    assert ok and val == {"v": 1}
    assert lookup(net, "n11", "n0")


def test_membership_eviction_and_quorum():
    m = Membership(timeout_s=100.0, clock=1000.0)
    assert m.join("a", attestation_ok=False) is False
    assert m.join("a", attestation_ok=True) is True
    for i in range(6):
        m.join(f"n{i}", attestation_ok=True)
        m.clock += 1
    assert m.fault_bound() == 2  # 7 voters
    m.clock += 500  # everyone times out
    assert m.sweep() and m.voters() == []


def test_ledger_snapshot_and_sync():
    a, b = Ledger(), Ledger()
    for i in range(5):
        a.append("note", {"i": i})
    snap = a.snapshot()
    assert snap["height"] == 5 and snap["verify"] is True
    r = b.sync_from(a.export_range(0))
    assert r["adopted"] == 5 and b.verify()["ok"] is True
    # Tampered suffix is refused
    evil = a.export_range(0)
    evil[-1] = dict(evil[-1], payload={"forged": True})
    c = Ledger()
    assert c.sync_from(evil)["adopted"] == 0


def test_rollout_halts_and_rolls_back():
    plan = RolloutPlan(version="9.9.9", batches=[["a"], ["b"], ["c"]])
    calls = {"gate": [{"gate": "open"}, {"gate": "closed"}]}
    applied, rolled = [], []

    def gate_fn(upgraded):
        return calls["gate"].pop(0) if calls["gate"] else {"gate": "open"}

    rep = staged_rollout(plan, gate_fn, lambda n: applied.append(n) or True,
                         lambda n: rolled.append(n) or True)
    assert rep["done"] is False and rep["halted_at_batch"] == 1
    assert set(rep["rolled_back"]) == {"a", "b"}


def test_health_status_and_metrics():
    st = status()
    assert st["ok"] is True and "version" in st
    txt = metrics_text(st)
    assert "eci_ledger_height" in txt and "eci_up 1" in txt
