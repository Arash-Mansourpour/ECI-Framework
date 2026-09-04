"""Artificial immune system: tolerance, detection, quarantine, memory, appeal."""
import random

from eci.immune import ImmuneMemory, Quarantine, breed, quarantine_flow
from eci.network.reputation import ReputationBoard
from eci.protocol0.ledger import Ledger


def _self(seed=7, n=60):
    rng = random.Random(seed)
    return [(0.6 + rng.uniform(-0.1, 0.1), 0.8 + rng.uniform(-0.1, 0.1), 0.9,
             0.3 + rng.uniform(-0.1, 0.1), 0.85 + rng.uniform(-0.1, 0.1)) for _ in range(n)]


ROGUE = (0.05, 0.0, 0.1, 0.95, 0.0)


def test_negative_selection_tolerates_self():
    s = _self()
    rep = breed(s, n_detectors=32, radius=0.35, seed=7)
    assert len(rep.detectors) == 32
    assert rep.false_positive_rate(s) == 0.0


def test_rogue_quarantined_and_remembered():
    s = _self()
    rep = breed(s, n_detectors=32, radius=0.35, seed=7)
    mem, ledger, board = ImmuneMemory(), Ledger(), ReputationBoard()
    board.observe("mallory", trust=0.9, obedience=0.8)
    r1 = quarantine_flow("mallory", ROGUE, rep, mem, s, lambda: False, ledger, board)
    assert r1["verdict"] == "quarantined" and r1["promoted"] >= 1
    r2 = quarantine_flow("mallory", ROGUE, rep, mem, s, lambda: False, ledger, board)
    assert r2["verdict"] == "memory_quarantined" and r2["memory_hit"] is True
    assert board.weights()["mallory"] == 0.0
    assert ledger.verify()["ok"] is True


def test_honest_cleared_and_quarantine_appeal():
    s = _self()
    rep = breed(s, n_detectors=32, radius=0.35, seed=7)
    mem, ledger = ImmuneMemory(), Ledger()
    r = quarantine_flow("alice", s[0], rep, mem, s, lambda: True, ledger, None)
    assert r["verdict"] == "clear"
    q = Quarantine()
    q.hold("mallory", "test")
    assert q.is_held("mallory") is True
    assert q.appeal("mallory", False) is False  # failed challenge stays held
    assert q.appeal("mallory", True) is True  # fresh pass releases
