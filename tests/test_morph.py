"""Morphogenesis: living self-evolving graphs and networks."""
import math


def _path3():
    from eci.morph.graph import MorphGraph
    g = MorphGraph()
    g.add_edge("a", "b", w=1.0)
    g.add_edge("b", "c", w=1.0)
    return g


def test_spectral_health_exact():
    g = _path3()
    assert abs(g.algebraic_connectivity() - 1.0) < 1e-4  # path-3 Fiedler value
    assert abs(g.effective_resistance() - 4.0) < 1e-3
    assert len(g.components()) == 1
    assert -0.5 <= g.modularity() <= 1.0
    h = g.health()
    assert h["nodes"] == 3 and h["edges"] == 2 and h["scars"] == 0


def test_triad_census_and_scars():
    from eci.morph.graph import MorphGraph
    g = MorphGraph()
    g.add_edge("a", "b")
    g.add_edge("b", "c")
    g.add_edge("c", "a")
    assert g.triad_census().get("triads_L3") == 1
    assert g.del_edge("a", "b", reason="t") is True
    assert len(g.scars) == 1 and g.scars[0]["reason"] == "t"
    g2 = MorphGraph.from_dict(g.to_dict())
    assert len(g2.nodes) == 3 and len(g2.edges) == 2 and len(g2.scars) == 1


def test_grammar_rewrites_and_learns():
    from eci.morph.grammar import GraphGrammar
    g = _path3()
    g.edges[("a", "b")].causal_support = 0.9
    gr = GraphGrammar()
    gr.defaults()
    r = gr.fire(g, surprise=0.8, energy_budget=5.0)
    assert g.edges[("a", "b")].w > 1.0  # hebb-strengthen fired
    assert r["lambda2_after"] >= 0 and r["spent"] >= 1.0
    mined = gr.mine_rules([("x", "y", 0.9), ("p", "q", 0.1)])
    assert len(mined) == 1 and mined[0].name == "mined-x-y"
    # rot-prune removes ancient weak edges
    g.edges[("b", "c")].age = 99
    g.edges[("b", "c")].w = 0.05
    gr.fire(g, energy_budget=5.0)
    assert ("b", "c") not in g.edges


def test_darwin_triage_and_shapley():
    from eci.morph.selection import DarwinSelector
    g = _path3()
    g.nodes["a"].utility = 5.0
    g.nodes["b"].utility = 5.0
    g.nodes["c"].utility = -5.0
    sel = DarwinSelector()
    sel.credit(g, 2.0, active=["a"])
    assert sel.energy_pool == 12.0
    assert g.nodes["a"].utility > 5.0
    before = len(g.edges)
    rep = sel.triage(g, seed=0)
    assert len(g.edges) == before - len(rep["pruned"])
    assert rep["pool"] < 12.0  # metabolic tax collected
    phi = sel.shapley_module(g, ["a", "b"], lambda S: float(len(S)), seed=0)
    assert abs(sum(phi.values()) - 2.0) < 1e-9  # efficiency axiom


def test_motif_genome_ops():
    from eci.morph.graph import MorphGraph
    from eci.morph.motifs import MOTIFS, MotifGenome
    assert set(MOTIFS) >= {"chain", "ffl", "diamond", "feedback"}
    mg = MotifGenome().random(motifs=3, seed=0)
    g = mg.compile(MorphGraph())
    assert len(g.nodes) > 0 and len(g.edges) >= 4
    h0 = mg.to_dict()
    mg.mutate(seed=1)
    assert mg.generation == h0["generation"] + 1
    for gene in mg.genes:
        assert gene.motif in MOTIFS
    kid = mg.crossover(MotifGenome().random(3, seed=9), seed=2)
    assert kid.generation == mg.generation + 1
    assert sum(mg.motif_histogram().values()) == len(mg.genes)


def test_self_repair_heals_cuts():
    from eci.morph.repair import SelfRepair
    g = _path3()
    g.nodes["a"].utility = 3.0
    rp = SelfRepair()
    base = rp.calibrate(g)
    assert base > 0
    g.del_edge("a", "b", reason="cut")
    g.del_edge("b", "c", reason="cut")
    d = rp.diagnose(g)
    assert d["damaged"] is True and len(d["orphans"]) >= 1
    h = rp.heal(g)
    assert h["healed"] is True and h["heal_fraction"] > 0
    assert len(g.components()) == 1


def test_coevolution_generations():
    from eci.morph.coevolve import Coevolver
    cv = Coevolver(pop=4)
    cv.seed(0)
    cv.evaluate([lambda g: float(len(g.edges))])
    assert all(c.fitness > 0 for c in cv.candidates)
    r = cv.evolve(seed=1)
    assert r["generation"] == 1 and r["enthroned"] is True
    assert len(cv.candidates) == 4 and len(cv.lineage) == 8  # 4 seeds + 4 kids (fossil record)
    # strict voter rejects the challenger handover
    cv.evaluate([lambda g: 1.0])
    r2 = cv.evolve(voter=lambda a, b: False, seed=2)
    assert r2["enthroned"] is False and r2["votes"] == 0


def test_facade_evolve_step_and_health():
    from eci.morph import Morphogenesis
    from eci.provenance import ProvenanceGraph
    m = Morphogenesis(seed=0)
    rep = m.evolve_step([lambda g: 1.0], reward=2.0, surprise=0.7, seed=0)
    assert rep["step"] == 1 and "health" in rep
    assert "provenance_id" not in rep  # standalone: hooks optional
    m2 = Morphogenesis(seed=0, provenance=ProvenanceGraph())
    rep2 = m2.evolve_step([lambda g: 1.0], reward=2.0, surprise=0.7, seed=0)
    assert "provenance_id" in rep2  # wired: every edit accountable
    h = m.health()
    assert h["ok"] is True and h["lambda2"] >= 0 and h["rules"] >= 5


def test_framework_and_mcp_morph_wiring():
    from eci.framework import ECIFramework
    fw = ECIFramework()
    assert fw.morph.health()["ok"] is True
    assert "morph" in fw.system_status()
    s = fw.mcp.request("sessions/create", {"subject": "operator", "capabilities": ["*"]})
    sid = s["result"]["session_id"]
    for t in ("morph.evolve", "morph.health", "morph.motifs", "morph.repair", "morph.coevolve"):
        assert t in fw.mcp.server.registry.names(), t
    r = fw.mcp.request("tools/call", {"name": "morph.health", "arguments": {}, "session_id": sid})
    assert r["result"]["ok"] is True and r["result"]["data"]["nodes"] >= 3
    e = fw.mcp.request("tools/call", {"name": "morph.evolve",
                                      "arguments": {"reward": 1.0, "surprise": 0.6, "seed": 0},
                                      "session_id": sid})
    assert e["result"]["ok"] is True and e["result"]["data"]["step"] >= 1
