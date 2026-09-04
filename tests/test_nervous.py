"""Nervous system: precog forecasting/holds + neural cortex advise."""
import torch

from eci.neural.cortex import Cortex, advise
from eci.neural.graph import build_graph, gnn_step
from eci.neural.world import WorldModel, rollout
from eci.precog.hold import ProvisionalHold
from eci.precog.risk import RiskEngine, RiskTier, forecast
from eci.protocol0.ledger import Ledger


def _risky():
    return [0.9, 0.9, 0.9, 0.8, 0.9]  # inverted: low health, high anomaly


def _healthy():
    return [0.1, 0.1, 0.0, 0.1, 0.0]


def test_precog_learns_and_calibrates():
    eng = RiskEngine()
    assert forecast(eng, _healthy())["tier"] == "clear"  # rare-event prior
    for _ in range(30):
        eng.observe(_risky(), True)
        eng.observe(_healthy(), False)
    assert forecast(eng, _risky())["tier"] == "hold"
    assert forecast(eng, _healthy())["tier"] in ("clear", "watch")
    assert 0.0 <= eng.ece() <= 0.5
    assert RiskTier(0.6) == "watch" and RiskTier(0.75) == "escalate"


def test_provisional_hold_reversible():
    h = ProvisionalHold(ttl_s=600.0)
    ledger = Ledger()
    h.place("mallory", 0.93, ledger)
    assert h.is_held("mallory") is True
    assert h.check("mallory", "vote") is not None
    assert h.check("mallory", "challenge_respond") is None  # always a way back
    assert h.release("mallory", False) is False
    assert h.release("mallory", True, ledger) is True
    assert ledger.verify()["ok"] is True


def test_cortex_advise_and_fit():
    torch.manual_seed(0)
    states = {
        "alice": {"awareness": 0.8, "obedience": 0.9, "trust": 0.9, "precog_p": 0.1},
        "bob": {"awareness": 0.7, "obedience": 0.8, "trust": 0.8, "precog_p": 0.2},
        "mallory": {"awareness": 0.05, "obedience": 0.0, "trust": 0.1, "anomaly": 0.95, "precog_p": 0.9},
    }
    edges = [("alice", "bob", 0.9), ("bob", "alice", 0.9), ("mallory", "alice", 0.1)]
    hist = torch.randn(12, 8) * 0.2 + 0.5
    g = build_graph(states, edges)
    assert g.n == 3 and g.x.shape == (3, 8)
    emb = gnn_step(g, rounds=2, seed=0)
    assert emb.shape == (3, 8) and torch.isfinite(emb).all()
    assert len(rollout(WorldModel(), hist, 0.0, horizon=3)) == 3
    out = advise(states, edges, hist, seed=0)
    assert set(out["agents"]) == {"alice", "bob", "mallory"}
    assert 0.0 <= out["mesh_health"] <= 1.0
    # Supervised fit separates the rogue
    model = Cortex()
    loss = model.fit(g, hist, torch.tensor([0.0, 0.0, 1.0]), steps=80)
    assert loss < 0.5
    out2 = advise(states, edges, hist, model=model)
    assert out2["agents"]["mallory"]["risk"] > out2["agents"]["alice"]["risk"]
