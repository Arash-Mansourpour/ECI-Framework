"""SECE — Self-Evolving Conscious Ecosystem (Phase 22) smoke + invariants."""

import numpy as np
import torch


def test_fcl_distributed_phi_quorum():
    from eci.consciousness.federated_ledger import FederatedConsciousnessLedger

    ledger = FederatedConsciousnessLedger(tolerance=1e-3)
    tpm = torch.eye(4) * 0.5 + torch.randn(4, 4) * 0.01
    tpm = (tpm + tpm.T) / 2
    claim = ledger.propose("node-a", tpm)
    assert claim.phi >= 0
    # verifier recomputes same tpm -> should sign
    assert ledger.verify(claim.id(), "node-b", tpm) is True
    assert ledger.verify(claim.id(), "node-c", tpm) is True
    # 3 nodes, need 2 -> should commit
    assert ledger.quorum_reached(claim.id(), 3) is True
    res = ledger.commit(claim.id(), 3)
    assert res["ok"] is True
    assert ledger.verify_chain()["ok"] is True


def test_fcl_reject_divergent_phi():
    from eci.consciousness.federated_ledger import FederatedConsciousnessLedger

    ledger = FederatedConsciousnessLedger(tolerance=1e-6)
    tpm_a = torch.eye(4) * 0.5
    claim = ledger.propose("node-a", tpm_a)
    tpm_b = torch.eye(4) * 5.0  # very different -> phi different
    assert ledger.verify(claim.id(), "node-b", tpm_b) is False
    assert ledger.quorum_reached(claim.id(), 3) is False


def test_can_closed_loop():
    from eci.consciousness.calibration_network import AwarenessCalibrationNetwork

    can = AwarenessCalibrationNetwork(agent_id="can-test")
    rest = [np.random.randn(64, 4) for _ in range(3)]
    cal = can.calibrate(rest)
    assert "n" in cal or isinstance(cal, dict)
    active = np.random.randn(64, 4) * 2.0
    out = can.cycle(active)
    assert "awareness_index" in out
    assert "bandpower" in out
    assert "challenge_score" in out
    assert "mapek_hint" in out
    assert out["awareness_index"] >= 0


def test_market_commons_publish_challenge():
    from eci.market_commons import MarketCommons

    mc = MarketCommons()
    fact = mc.publish("ECI is conscious at level 0.5", publisher="alice", confidence=0.8)
    assert fact is not None
    res = mc.challenge(fact.id if hasattr(fact, "id") else "fact-0", challenger="bob", counter_evidence="contradiction: ECI is not conscious")
    assert "upheld" in res or "ok" in res


def test_qn_bridge_rate_posterior_and_f():
    from eci.bridges.quantum_neuromorphic import QuantumNeuromorphicBridge

    bridge = QuantumNeuromorphicBridge(in_dim=4, hidden=6, out_dim=2, n_steps=10)
    obs = torch.randn(3, 4)
    g = bridge.update(obs)
    assert g.mu.shape[0] == 2
    f = bridge.free_energy_contribution()
    assert f.item() == f.item() and f.item() >= 0
    # second update with target
    g2 = bridge.update(torch.randn(2, 4), target=torch.zeros(2))
    assert g2.mu.shape[0] == 2


def test_genesis_evolution_lifecycle():
    from eci.protocol_vnext.genesis_evolution import MutableConstitution

    mc = MutableConstitution()
    root0 = mc.genome.root
    p = mc.propose("Preserve federated consciousness provenance", proposer="alice")
    assert p.mutation in mc.proposals[p.id()].mutation
    twin = mc.twin_test(p.id(), simulated_improvement=0.2)
    assert "verdict" in twin
    assert mc.canary(p.id(), success=True) is True
    mc.vote(p.id(), "bob", True)
    mc.vote(p.id(), "carol", True)
    res = mc.commit(p.id(), quorum=2)
    assert res["ok"] is True
    assert mc.genome.root != root0
    # rollback
    rb = mc.rollback()
    assert rb["ok"] is True
    assert mc.genome.root == root0


def test_genesis_evolution_rejects_short_mutation():
    import pytest

    from eci.protocol_vnext.genesis_evolution import MutableConstitution

    mc = MutableConstitution()
    with pytest.raises(ValueError):
        mc.propose("hi", proposer="alice")
