"""COGNISPHERE Phase 23 — LFM/MAA/KNE invariants (additive, no API breaks)."""

import numpy as np
import torch


def test_lfm_tombstone_archive_never_deletes():
    from eci.protocol_vnext.memory import LivingMemory

    m = LivingMemory(decay_rate=10.0)
    it = m.store({"task": "ephemeral"}, kind="episodic", salience=0.05)
    old_id = it.id
    removed = m.forget(threshold=0.9)
    assert removed >= 1
    assert m.stats()["archived"] >= 1
    assert any(a.id == old_id and a.tombstoned for a in m.archive)


def test_lfm_ebbinghaus_rehearsal_protects():
    import time

    from eci.protocol_vnext.memory import LivingMemory

    m = LivingMemory(decay_rate=0.001)
    weak = m.store("weak", kind="episodic", salience=0.2)
    strong = m.store("strong", kind="episodic", salience=0.2)
    for _ in range(6):
        strong.touch()
    future = time.time() + 3600.0
    assert strong.retention(m.decay_rate, now=future) > weak.retention(m.decay_rate, now=future)
    assert strong.strength() > weak.strength()


def test_lfm_dream_importance_priced():
    from eci.protocol_vnext.memory import DreamEngine, LivingMemory

    m = LivingMemory()
    m.store("same-prefix-aaa", kind="episodic", salience=0.8)
    m.store("same-prefix-aaa", kind="episodic", salience=0.7)
    out = DreamEngine().consolidate(m)
    assert out["skills"], out
    assert out["skills"][0]["importance"] > 0


def test_maa_fcl_gossip_pbft():
    from eci.consciousness.federated_ledger import FederatedConsciousnessLedger
    from eci.core.types import NetworkNode, NetworkRole
    from eci.network.consensus import PBFTConsensus

    fl = FederatedConsciousnessLedger(tolerance=1e-3)
    claim = fl.propose("node-a", torch.eye(4) * 0.5)
    nodes = {f"n{i}": NetworkNode(node_id=f"n{i}", role=NetworkRole.VALIDATOR,
                                  trust_score=1.0, reputation_score=1.0, stake=1.0)
             for i in range(3)}
    nodes["node-a"] = NetworkNode(node_id="node-a", role=NetworkRole.VALIDATOR,
                                  trust_score=1.0, reputation_score=1.0, stake=1.0)
    res = fl.gossip_round(claim.id(), nodes, PBFTConsensus(n_nodes=len(nodes), byzantine_rate=0.0))
    assert res["ok"] is True and res["achieved"] is True
    assert res["quorum"] is True
    assert fl.to_dict()["gossip_rounds"] == 1


def test_maa_can_file_loop(tmp_path):
    from eci.consciousness.calibration_network import AwarenessCalibrationNetwork

    arr = (np.random.randn(128, 2) * 2.0).astype(np.float64)
    p = tmp_path / "eeg.npy"
    np.save(str(p), arr)
    can = AwarenessCalibrationNetwork(agent_id="can-file-test")
    can.calibrate([np.random.randn(64, 2)])
    out = can.cycle_from_file(str(p))
    assert out["ok"] is True
    assert out["awareness_index"] >= 0
    assert out["source"] == str(p)
    assert "mne" in can.to_dict()
    missing = can.cycle_from_file(str(tmp_path / "nope.npy"))
    assert missing["ok"] is False


def test_kne_executable_economy():
    from eci.market_commons import MarketCommons

    mc = MarketCommons()
    fact = mc.publish("rivers flow uphill", publisher="alice", confidence=0.8)
    assert fact.fid in mc.envelopes and fact.fid in mc.proposals
    res = mc.challenge(fact.fid, challenger="bob", counter_evidence="rivers flow downhill")
    assert res["upheld"] is True
    assert res["payout"] == mc.challenge_stake
    assert res["economy_slashed"] == "alice"
    assert "tally" in res and "court" in res
    assert res["court"]["verdict"] in ("acquit", "downgrade", "extend_hold", "quarantine")
    assert mc.to_dict()["envelopes"] >= 1


def test_kne_brier_when_wired():
    from eci.market_commons import MarketCommons
    from eci.redteam import ForecasterRegistry

    mc = MarketCommons()
    mc.forecasters = ForecasterRegistry()
    fact = mc.publish("moon is cheese", publisher="alice", confidence=0.8)
    res = mc.challenge(fact.fid, challenger="bob", counter_evidence="moon is rock")
    assert "brier" in res
    assert 0.0 <= res["brier"]["brier"] <= 1.0
