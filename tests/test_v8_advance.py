"""v8 OMNISCIENCE advance tests (deterministic, no network/hardware)."""

from __future__ import annotations


def test_arch_fitness_green():
    from eci.arch import run_fitness

    rep = run_fitness()
    assert rep["total"] == 6
    assert rep["ok"], rep


def test_adr_registry():
    from eci.arch import ADR_REGISTRY, get_adr, list_adrs

    assert len(ADR_REGISTRY) >= 6
    assert get_adr("ADR-001")["status"] == "accepted"
    assert any(a["id"] == "ADR-006" for a in list_adrs())


def test_quantum_router_defaults_to_sim():
    from eci.quantum.hardware import BackendRouter

    r = BackendRouter()
    assert r.route(2) == "sim"
    assert r.route(10_000) == "none"
    b = r.get("sim")
    assert b is not None and b.available()
    res = b.run([0.5, 0.5])
    assert res.shots > 0 and abs(sum(res.counts.values()) - res.shots) == 0


def test_quantum_hardware_fail_closed():
    from eci.quantum.hardware import BraketBackend, QiskitBackend

    for cls in (QiskitBackend, BraketBackend):
        b = cls()
        res = b.run([1.0, 0.0])
        if not b.available():
            assert res.meta.get("ok") is False
            assert res.counts == {}
        else:
            assert res.shots > 0


def test_p2p_mesh_commits_and_partition_stalls():
    from eci.federation.p2p import build_mesh, run_partition_test

    nodes, _t = build_mesh(4)
    d = nodes[0].propose({"op": "test"})
    assert isinstance(d, str) and len(d) == 16
    assert sum(n.commit_count() for n in nodes) >= 1
    rep = run_partition_test(n=4, proposals=1)
    assert rep["partition_stalled"] is True
    assert rep["committed_healed"] >= 1


def test_economy_whale_flagged_not_profitable():
    from eci.economy_attack import evaluate_slash, simulate_whale_attack

    w = simulate_whale_attack(whale_stake=500.0)
    assert 0.0 < w.price_before < 1.0
    assert w.price_after > w.price_before
    assert w.cost > 0
    # LMSR makes single-sided whale push expensive
    assert w.profitable is False
    s = evaluate_slash(w.price_shift, 0.0, 0.0)
    assert isinstance(s.slash, bool)


def test_economy_collusion_flip_and_detect():
    from eci.economy_attack import evaluate_slash, simulate_collusion

    votes = {"a": "yes", "b": "yes", "c": "no", "d": "no", "e": "no"}
    col = simulate_collusion(votes, ring={"d", "e"}, ring_target="yes")
    assert col.flipped is True
    assert col.detection_score > 0.5
    s = evaluate_slash(0.0, col.detection_score, 0.0)
    assert s.slash is True and s.amount > 0


def test_brier_exact():
    from eci.economy_attack import brier_score

    assert brier_score([1.0, 0.0], [1, 0]) == 0.0
    assert abs(brier_score([0.5], [1]) - 0.25) < 1e-12


def test_otel_noop_offline():
    from eci.observability.otel import OtelBridge

    b = OtelBridge()
    assert isinstance(b.available, bool)
    with b.span("test", {"k": "v"}) as _s:
        pass
    assert "otel_available" in b.health()


def test_research_loop_cycle():
    from eci.research.loop import ResearchLoop

    loop = ResearchLoop()
    hyp = loop.propose("twin doubles score", 0.8, {"x": 0.9})
    res = loop.run_cycle(hyp, drill=lambda p: float(p["x"]), outcome=1)
    assert res.twin_score == 0.9
    assert res.approved is True
    assert abs(res.brier - 0.04) < 1e-12
    assert loop.mean_brier() == res.brier


def test_framework_v8_wired():
    from eci.framework import ECIFramework

    fw = ECIFramework()
    st = fw.v8_status()
    assert st["wired"] is True
    assert st["fitness"]["ok"], st["fitness"]
    assert "quantum_router" in st and "research" in st
    sys_status = fw.system_status()
    assert "v8" in sys_status


def test_prometheus_exposition_nonempty():
    from eci.framework import ECIFramework

    fw = ECIFramework()
    fw.observability.metrics.counter("v8_test_total").inc()
    text = fw.observability.metrics.to_prometheus()
    assert "v8_test_total" in text
