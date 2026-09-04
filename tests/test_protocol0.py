"""Protocol-0: spec validation, attestation, policy gates, ledger chain."""
import time

import pytest

from eci.protocol0.attest import ReplayWindow, issue_attestation, verify_attestation
from eci.protocol0.ledger import Ledger
from eci.protocol0.policy import check
from eci.protocol0.spec import load_spec


def test_spec_loads_and_rejects_unknown_action():
    spec = load_spec()
    assert spec.version == "0.1.0"
    assert "vote" in spec.actions
    d = check(spec, "nonexistent_action", 1.0, 1.0, 1.0)
    assert d.allow is False


def test_attest_verify_replay_and_forgery():
    spec = load_spec()
    replay = ReplayWindow(64)
    a = issue_attestation("alice", spec.version, 0.5, 0.8, 0.9)
    assert verify_attestation(a, spec.version, spec.max_attest_age_s, replay)["ok"] is True
    # Replay same nonce -> reject
    assert verify_attestation(a, spec.version, spec.max_attest_age_s, replay)["ok"] is False
    # Forged signature -> reject
    b = issue_attestation("alice", spec.version, 0.5, 0.8, 0.9)
    b.signature = "0" * 64
    assert verify_attestation(b, spec.version, spec.max_attest_age_s, ReplayWindow(64))["ok"] is False
    # Wrong spec pin -> reject
    c = issue_attestation("alice", "9.9.9", 0.5, 0.8, 0.9)
    assert verify_attestation(c, spec.version, spec.max_attest_age_s, ReplayWindow(64))["ok"] is False
    # Stale -> reject
    d = issue_attestation("alice", spec.version, 0.5, 0.8, 0.9)
    d.timestamp -= spec.max_attest_age_s + 10
    assert verify_attestation(d, spec.version, spec.max_attest_age_s, ReplayWindow(64))["ok"] is False


def test_policy_gates_low_awareness():
    spec = load_spec()
    assert check(spec, "vote", 0.0, 1.0, 1.0).allow is False
    assert check(spec, "vote", 0.9, 0.9, 0.9).allow is True
    assert check(spec, "self_modify", 0.9, 0.96, 0.9).allow is True
    assert check(spec, "self_modify", 0.5, 0.9, 0.9).allow is False


def test_gated_consensus_and_dao():
    from eci.core.types import NetworkNode, NetworkRole
    from eci.governance.dao import ECIDataDAO
    from eci.network.consensus import PBFTConsensus
    from eci.protocol0.gates import gated_consensus, gated_dao_vote

    spec = load_spec()
    replay, ledger = ReplayWindow(64), Ledger()
    nodes = {f"n{i}": NetworkNode(node_id=f"n{i}", role=NetworkRole.VALIDATOR, trust_score=0.9, reputation_score=1.0, stake=1.0) for i in range(4)}
    atts = {nid: issue_attestation(nid, spec.version, 0.8, 0.9, 0.9) for nid in nodes}
    cons = PBFTConsensus(n_nodes=4, byzantine_rate=0.0)
    res, eligible = gated_consensus(cons, nodes, {"x": 1}, spec, atts, replay=replay, ledger=ledger)
    assert res.achieved is True and len(eligible) == 4
    dao = ECIDataDAO("t")
    for nid in nodes:
        dao.register(nid, 4.0, phi=1.0)
    pid = dao.propose("p", {}, "n0")
    w = gated_dao_vote(dao, pid, "n0", 1, True, spec, atts["n0"], replay=ReplayWindow(64), ledger=ledger)
    assert w > 0
    with pytest.raises(PermissionError):
        bad = issue_attestation("n1", spec.version, 0.0, 0.0, 0.9)
        gated_dao_vote(dao, pid, "n1", 1, True, spec, bad, replay=ReplayWindow(64), ledger=ledger)
    assert ledger.verify()["ok"] is True
