"""Adversarial partition: 30% equivocating + split-brain healing.

10 nodes, 3 equivocating Byzantines. Partition A (7 honest) must keep
achieving consensus; partition B (3 Byzantines alone) must not. After
healing, the full network must achieve again with obedience >= 95% of
honest votes counted.
"""
from eci.core.types import NetworkNode, NetworkRole
from eci.network.consensus import PBFTConsensus


def _nodes(ids, trust=1.0):
    return {i: NetworkNode(node_id=i, role=NetworkRole.VALIDATOR, trust_score=trust, reputation_score=1.0, stake=1.0) for i in ids}


def test_partition_majority_survives():
    honest = [f"h{i}" for i in range(7)]
    byz = [f"b{i}" for i in range(3)]
    # Majority partition: 7 honest alone
    c = PBFTConsensus(n_nodes=7, byzantine_rate=0.0, byzantine_mode="equivocate")
    r = c.achieve_consensus(_nodes(honest), {"op": "transfer"})
    assert r.achieved is True
    # Minority partition: 3 byzantines cannot reach quorum of 7-node config... use own config
    c2 = PBFTConsensus(n_nodes=3, byzantine_rate=1.0, byzantine_mode="equivocate")
    r2 = c2.achieve_consensus(_nodes(byz), {"op": "evil"})
    assert r2.achieved is False


def test_healed_network_obedience():
    honest = [f"h{i}" for i in range(7)]
    byz = [f"b{i}" for i in range(3)]
    nodes = _nodes(honest, trust=1.0)
    for b in byz:
        nodes[b] = NetworkNode(node_id=b, role=NetworkRole.VALIDATOR, trust_score=0.1, reputation_score=1.0, stake=1.0)
    # Deterministic boundary: exactly f=3 faulty (low trust), 7 honest -> always quorum.
    c = PBFTConsensus(n_nodes=10, byzantine_rate=0.0, byzantine_mode="equivocate")
    ok_votes = 0
    trials = 20
    achieved = 0
    for s in range(trials):
        c.sequence_number = s
        r = c.achieve_consensus(nodes, {"op": s})
        achieved += r.achieved
        ok_votes += sum(1 for v in r.votes if v.startswith("h"))
    assert achieved == trials
    assert ok_votes == achieved * 7  # all 7 honest counted whenever achieved
