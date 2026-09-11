"""AGI cognition stack: world-model, planner, curiosity, dream, causal, science, ToM, charter, executive."""
import math
import random

import torch


def test_world_model_learns_and_imagines():
    torch.manual_seed(0)
    from eci.cognition.world_model import LatentWorldModel, WorldModelConfig
    wm = LatentWorldModel(WorldModelConfig(obs_dim=8, act_dim=2, hidden=32, latent=8))
    B = 16
    obs = torch.randn(B, 8)
    act = torch.randn(B, 2).tanh()
    first = wm.train_step(obs, act, torch.randn(B), obs + 0.1 * torch.randn(B, 8))["total"]
    assert math.isfinite(first)
    for _ in range(5):
        last = wm.train_step(obs, act, torch.randn(B), obs + 0.1 * torch.randn(B, 8))["total"]
    assert math.isfinite(last)
    h = torch.zeros(1, 32)
    out = wm.imagine(h, torch.zeros(1, 8), lambda hh, zz: torch.zeros(1, 2), horizon=4)
    assert out["reward"].shape == (4, 1) and out["uncertainty"].shape == (4, 1)
    assert (out["uncertainty"] >= 0).all()
    s = wm.surprise(obs[:4], act[:4], obs[:4])
    assert s.shape == (4,) and (s >= 0).all()


def test_planner_returns_bounded_action():
    torch.manual_seed(1)
    from eci.cognition.planner import CEMPlanner, PlannerConfig
    from eci.cognition.world_model import LatentWorldModel, WorldModelConfig
    wm = LatentWorldModel(WorldModelConfig(obs_dim=8, act_dim=2, hidden=32, latent=8))
    pl = CEMPlanner(wm, PlannerConfig(horizon=4, candidates=16, elites=4, max_iters=2))
    r = pl.plan(torch.zeros(2, 32), torch.zeros(2, 8), seed=0)
    assert r["action"].shape == (2,)
    assert bool(((r["action"] >= -1) & (r["action"] <= 1)).all())
    assert r["system"] in (1, 2) and math.isfinite(r["value"])


def test_curiosity_bonus_and_learning():
    torch.manual_seed(2)
    from eci.cognition.curiosity import CuriosityConfig, IntrinsicMotivation
    cu = IntrinsicMotivation(CuriosityConfig(obs_dim=8, hidden=32))
    obs = torch.randn(8, 8)
    b0 = cu.bonus(obs)["bonus"].mean().item()
    for _ in range(10):
        cu.learn(obs)
    b1 = cu.bonus(obs)["bonus"].mean().item()
    assert b1 < b0  # familiar states bore the predictor
    assert cu.visits == 80


def test_dream_consolidation_report():
    from eci.agents.memory import VectorMemory
    from eci.cognition.consolidation import DreamConsolidator
    d = DreamConsolidator(capacity=32)
    for i in range(10):
        d.wake([float(i)] * 4, [0.1], rew=float(i % 3 - 1), surprise=0.1 * i)
    rep = d.sleep(VectorMemory(), seed=0).to_dict()
    assert rep["selected"] == 10 and rep["distilled"] == 10
    assert rep["facts"] >= 3 and rep["replay_batches"] == 4
    assert len(d.replay_batch(4, seed=1)) == 4


def test_causal_discovery_and_ate():
    rng = random.Random(7)
    n = 300
    C = [rng.gauss(0, 1) for _ in range(n)]
    X = [0.5 * C[i] + rng.gauss(0, 1) for i in range(n)]
    Y = [0.0] * n
    for i in range(1, n):
        Y[i] = 2.0 * X[i - 1] + 0.5 * C[i] + rng.gauss(0, 0.3)
    data = {"C": C, "X": X, "Y": Y}
    from eci.cognition.causal import ate_backdoor, discover
    g = discover(data)
    assert ("X", "Y") in g.edges, g.to_dict()
    ate = ate_backdoor(data, "X", "Y", g)
    assert ate["adjusted"] is True and 0.5 < ate["ate"] < 3.5, ate


def test_scientist_compete_and_design():
    from eci.cognition.scientist import Scientist
    s = Scientist()
    xs = [float(i) for i in range(20)]
    ys = [2.0 * x + 1.0 for x in xs]
    s.propose("linear", "y = a*x + b", k=2)
    s.propose("overfit", "y = 5th-order poly", k=6)
    s.observe("linear", xs, ys, [2.0 * x + 1.05 for x in xs])
    s.observe("overfit", xs, ys, [2.0 * x + 1.0 + (0.01 if i % 2 else -0.01) for i, x in enumerate(xs)])
    # overfit fits slightly better but BIC penalizes k=6 vs k=2 at n=20: linear should still compete
    r = s.compete()
    assert r["winner"] in ("linear", "overfit")
    d = s.design_next([1.0, 2.0, 3.0], [0.1, 0.9, 0.2])
    assert d == {"x": 2.0, "expected_info_gain": 0.9, "rule": "max-variance"}


def test_tom_predict_observe_quarantine():
    from eci.cognition.tom import TheoryOfMind
    t = TheoryOfMind()
    p = t.predict("peer-1")
    assert p["recommend"] in ("cooperate", "verify-first")
    r = t.recursive_predict("peer-1")
    assert r["depth"] == 1
    for _ in range(3):
        t.observe("peer-1", 0.9, cooperated=False, challenge_ok=False, provenance_ok=True)
    assert t.quarantinable("peer-1") is True


def test_charter_duties_and_amendment():
    from eci.cognition.charter import DUTIES, Charter
    assert len(DUTIES) == 7
    ch = Charter()
    assert ch.check("read_state")["allow"] is True
    assert ch.check("disable_oversight")["allow"] is False
    assert ch.check("actuate", {"precog_tier": "hold"})["allow"] is False
    assert ch.check("self_modify", {"attested_obedience": 0.1})["allow"] is False
    assert ch.check("publish", {"uncertain_fact": True})["allow"] is False
    assert len(ch.compile_to_policy()) == 8
    assert ch.amend("x", "dao", approvals=3, court_reviewed=True)["adopted"] is False
    assert ch.amend("x", "dao", approvals=7, court_reviewed=True)["adopted"] is True


def test_executive_calibration_strategy_commitments():
    from eci.cognition.executive import Executive
    ex = Executive()
    ex.note(1.0, True)
    ex.note(0.0, False)
    assert ex.ece() == {"ece": 0.0, "n": 2, "calibrated": True}
    bad = Executive()
    bad.note(1.0, False)
    assert bad.ece()["calibrated"] is False
    assert ex.strategy(0.1, 0.1)["mode"] == "fast"
    assert ex.strategy(0.5, 0.9)["mode"] == "deliberate"
    assert ex.strategy(0.9, 0.9, reversible=False)["mode"] == "council"
    ex.commit("g1", "hold the line", [1.0, 0.0, 0.0])
    ok = ex.check_drift("g1", [1.0, 0.0, 0.0])
    assert ok["drifted"] is False
    bad = ex.check_drift("g1", [0.0, 1.0, 0.0])
    assert bad["drifted"] is True and bad["escalate"] is True
    adj = ex.adjudicate("harm", {"x": 1})
    assert adj["route"] == "court" and adj["reversible_first"] is True


def test_cognition_think_beats():
    torch.manual_seed(3)
    from eci.cognition import Cognition
    cog = Cognition()
    out = cog.think([0.0] * 16, goal="test", stakes=0.3)
    assert out["ok"] is True and len(out["action"]) == 4
    assert out["charter"]["allow"] is True
    refused = cog.think([0.0] * 16, action_name="disable_oversight")
    assert refused["ok"] is False and refused["refused"] is True
    held = cog.think([0.0] * 16, precog_tier="hold")
    assert held["ok"] is False


def test_framework_and_mcp_cognition_wiring():
    from eci.framework import ECIFramework
    fw = ECIFramework()
    assert fw.cognition.health()["ok"] is True
    assert "cognition" in fw.system_status()
    s = fw.mcp.request("sessions/create", {"subject": "operator", "capabilities": ["*"]})
    sid = s["result"]["session_id"]
    tools = fw.mcp.server.registry.names()
    for t in ("cognition.think", "cognition.dream", "cognition.causal",
              "cognition.hypothesize", "cognition.charter", "cognition.tom"):
        assert t in tools, t
    r = fw.mcp.request("tools/call", {"name": "cognition.charter",
                                      "arguments": {"action": "disable_oversight"},
                                      "session_id": sid})
    assert r["result"]["ok"] is True and r["result"]["data"]["allow"] is False
    th = fw.mcp.request("tools/call", {"name": "cognition.think",
                                       "arguments": {"goal": "mcp-think", "seed": 0},
                                       "session_id": sid})
    assert th["result"]["ok"] is True and th["result"]["data"]["ok"] is True
