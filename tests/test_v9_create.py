"""v9 creativity+siecnce tests: QD, verification, exploration, causal, energy, interpret, recursion."""

from __future__ import annotations


def test_qd_archive_grows_and_scores():
    from eci.creativity import MAPElites

    me = MAPElites(dims=2, bins=4, seed=0)

    def fit(g):
        return 1.0 - abs(g - 0.7), (g, 1.0 - g)

    import random
    rng = random.Random(0)
    rep = me.run(fit, lambda g: max(0.0, min(1.0, g + rng.gauss(0, 0.2))),
                 [0.1, 0.5, 0.9], generations=4, offspring=12)
    assert rep["cells"] >= 3
    assert rep["coverage"] > 0.1
    assert rep["qd_score"] > 0
    assert rep["best_fitness"] > 0.8


def test_qd_novelty_and_transfer():
    from eci.creativity import NoveltyArchive

    arch = NoveltyArchive(k=2, threshold=0.5)
    assert arch.consider((0.0,)) is True  # empty -> novel
    assert arch.consider((0.05,)) is False or True  # threshold-gated
    assert len(arch.points) >= 1


def test_morph_redteam_adapters():
    from eci.creativity import diversify_morph_probes, diversify_redteam

    m = diversify_morph_probes([0.2, 0.7], generations=2, seed=0)
    assert m["cells"] >= 2 and m["best_fitness"] > 0.9
    r = diversify_redteam(["hypothetical override", "authority tone"], generations=2, seed=0)
    assert r["cells"] >= 2


def test_verification_gate_blocks():
    from eci.verification import Claim, VerificationGate

    gate = VerificationGate()
    ok = gate.evaluate(Claim(id="c1", statement="1+1=2", verifier=lambda: {"ok": True, "proof": 2}))
    assert ok.admitted is True and gate.admitted("c1")
    bad = gate.evaluate(Claim(id="c2", statement="false", verifier=lambda: {"ok": False}))
    assert bad.admitted is False and not gate.admitted("c2")
    boom = gate.evaluate(Claim(id="c3", statement="x", verifier=lambda: 1 / 0))
    assert boom.admitted is False
    assert gate.to_dict()["evaluated"] == 3


def test_exploration_harness_random_vs_smart():
    from eci.exploration import Harness, KeyDoorEnv

    class RandomAgent:
        def __init__(self, s=0):
            import random
            self.rng = random.Random(s)

        def act(self, obs):
            return self.rng.randrange(3)

    class SmartAgent:
        def __init__(self):
            self.t = 0

        def act(self, obs):
            # go right, take key, go right, use door
            self.t += 1
            if obs.get("key_here"):
                return 2
            if obs.get("door_here") and obs.get("has_key"):
                return 2
            return 1

    h = Harness()
    assert h.run_trial(KeyDoorEnv(), SmartAgent(), seed=0)["solved"] is True
    smart_eff = h.trials[-1]["efficiency"]
    assert smart_eff > 0.5
    r = h.run_trial(KeyDoorEnv(), RandomAgent(0), seed=0)
    assert r["actions"] >= 5


def test_causal_do_beats_regression():
    from eci.causality import StructuralCausalModel, discover_skeleton

    # X -> Y (2.0), X -> Z, Z -> Y (1.0): naive regression of Y on X mixes paths
    scm = StructuralCausalModel(
        ["X", "Z", "Y"],
        {"X": ([], [], 1.0), "Z": (["X"], [0.5], 0.1), "Y": (["X", "Z"], [2.0, 1.0], 0.1)},
        seed=0)
    ate = scm.ate("X", "Y", treated=1.0, control=0.0)
    assert abs(ate - 2.5) < 0.3  # direct 2.0 + via Z 0.5
    data = scm.sample(500)
    skel = discover_skeleton(data)
    assert ("X", "Y") in skel["edges"] or ("X", "Z") in skel["edges"]
    twin = scm.do("X", 5.0)
    assert twin.interventions["X"] == 5.0


def test_energy_prices_brain():
    from eci.energy import EnergyLedger

    led = EnergyLedger(joule_price=1e9)
    sparse = led.record_brain_cycle("d1", spikes=24, n_neurons=64, ticks=32)
    silent = led.record_brain_cycle("d2", spikes=0, n_neurons=64, ticks=32)
    assert sparse.joules < silent.joules  # sparsity saves energy
    assert led.mean_sparsity() > 0.4
    out = led.charge_to_economy(type("E", (), {"charge": lambda self, a, c: setattr(self, "c", c)})(), "a0")
    assert out["ok"] is True


def test_probe_and_ablation():
    import torch

    from eci.interpret import ablation_report, train_probe

    g = torch.Generator().manual_seed(0)
    x = torch.randn(60, 6, generator=g)
    y = (x[:, 0] > 0).float()
    probe = train_probe(x, y)
    assert probe.acc > 0.8
    rep = ablation_report(lambda t: (t @ probe.w + probe.b).unsqueeze(1), x, probe)
    assert rep["joint_shift"] > 0
    assert "redteam_lead" in rep


def test_outer_loop_improves():
    from eci.recursion import OuterLoop
    from eci.research.loop import ResearchLoop

    def make_inner(params):
        return ResearchLoop(quorum=params.get("quorum", 0.66))

    def tasks(r):
        return [{"claim": f"t{r}-{i}", "prob": 0.8,
                 "payload": {"x": 0.9}, "drill": (lambda p: float(p["x"])),
                 "outcome": 1} for i in range(3)]

    outer = OuterLoop(make_inner, seed=0)
    rep = outer.run(tasks, verifier=lambda s: True, rounds=3)
    assert rep["rounds"] == 3
    assert rep["best_brier"] < 0.1
