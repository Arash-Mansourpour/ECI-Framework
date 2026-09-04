"""Network: Krum/Bulyan robustness + equivocate mode + async channel."""
import asyncio

import torch

from eci.core.types import NetworkNode, NetworkRole
from eci.network.aggregation import bulyan, byzantine_robust_aggregate, krum
from eci.network.consensus import PBFTConsensus
from eci.network.transport import AsyncMemoryChannel


def _updates():
    base = {"w": torch.zeros(4)}
    ups = [{**{"w": torch.zeros(4)}} for _ in range(6)]
    ups.append({"w": torch.full((4,), 100.0)})
    return ups


def test_krum_ignores_outlier():
    ups = _updates()
    agg = byzantine_robust_aggregate(ups, method="krum")
    assert float(agg["w"].abs().max()) < 1.0
    assert float(krum(ups, f=1)["w"].abs().max()) < 1.0
    assert float(bulyan(ups, f=1)["w"].abs().max()) < 1.0


def _nodes(n=4):
    return {
        f"n{i}": NetworkNode(node_id=f"n{i}", role=NetworkRole.VALIDATOR, trust_score=1.0, reputation_score=1.0, stake=1.0)
        for i in range(n)
    }


def test_equivocate_mode_runs():
    c = PBFTConsensus(n_nodes=4, byzantine_rate=0.0, byzantine_mode="equivocate")
    r = c.achieve_consensus(_nodes(), {"x": 1})
    assert r.achieved is True


def test_async_channel_fanout():
    async def go():
        ch = AsyncMemoryChannel()
        ch.register("a"); ch.register("b"); ch.register("c")
        n = await ch.broadcast("a", {"vote": 1})
        assert n == 2
        got = await ch.drain("b")
        assert len(got) == 1

    asyncio.run(go())
