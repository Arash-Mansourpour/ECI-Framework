"""v6 OMNIVERSE hyper-architecture: one test per new subsystem + facade slice."""
import asyncio

import pytest


def test_kernel_bus_wildcard_dlq_replay():
    from eci.kernel import Event, EventBus
    bus = EventBus()
    seen = []
    bus.subscribe("workflow.*", lambda e: seen.append(e.type))
    def boom(e):
        raise ValueError("x")
    bus.subscribe("workflow.job.done", boom, name="boom")
    bus.publish(Event(type="workflow.job.done", source="t", payload={"a": 1}))
    assert seen == ["workflow.job.done"]
    assert len(bus.dead_letters) == 1
    assert bus.replay("workflow.*")[0].type == "workflow.job.done"
    assert bus.stats()["published"] == 1


def test_kernel_container_cycle():
    from eci.kernel import CircularDependencyError, Container
    c = Container()
    c.register("a", instance=1)
    assert c.resolve("a") == 1
    c.register("x", factory=lambda cont: cont.resolve("y"))
    c.register("y", factory=lambda cont: cont.resolve("x"))
    with pytest.raises(CircularDependencyError):
        c.resolve("x")


def test_kernel_lifecycle_order_and_health():
    from eci.kernel import LifecycleManager
    order = []
    class Svc:
        def __init__(self, name): self.name = name
        def start(self): order.append(self.name)
        def stop(self): order.append("stop-" + self.name)
        def health(self): return {"ok": True}
    m = LifecycleManager()
    m.register(Svc("db"))
    m.register(Svc("api"), depends_on=["db"])
    assert m.order() == ["db", "api"]
    asyncio.run(m.start_all())
    assert order == ["db", "api"]
    assert m.health()["ok"] is True
    asyncio.run(m.stop_all())


def test_observability_tracing_metrics_audit():
    from eci.observability import AuditLogger, MetricsRegistry, Tracer
    t = Tracer("t")
    with t.span("op", {"k": 1}) as s:
        s.event("step")
    assert t.stats()["spans"] == 1
    m = MetricsRegistry()
    m.counter("c").inc(2)
    m.histogram("h").observe(0.1)
    assert "c 2" in m.to_prometheus()
    a = AuditLogger()
    a.append("alice", "vote", {"x": 1})
    assert a.verify()["ok"] is True


def test_persistence_eventstore_repo_uow():
    from eci.persistence import EventStore, Repository, UnitOfWork
    es = EventStore()
    es.append("ledger", "append", {"i": 1})
    assert es.fold("ledger", lambda s, e: s + 1, 0) == 1
    repo = Repository()
    with UnitOfWork(repo) as u:
        u.save("k", {"v": 1})
    assert repo.get("k")["v"] == 1
    with pytest.raises(RuntimeError):
        with UnitOfWork(repo) as u:
            u.save("k2", {"v": 2})
            raise RuntimeError("abort")
    assert repo.get("k2") is None


def test_resilience_breaker_retry_limiter_saga():
    from eci.resilience import CircuitBreaker, CircuitOpenError, RetryPolicy, Saga, TokenBucket
    cb = CircuitBreaker(failure_threshold=2, reset_timeout_s=1000, name="t")
    def fail(): raise ValueError("bad")
    with pytest.raises(ValueError): cb.call(fail)
    with pytest.raises(ValueError): cb.call(fail)
    with pytest.raises(CircuitOpenError): cb.call(fail)
    n = {"i": 0}
    def flaky():
        n["i"] += 1
        if n["i"] < 2: raise ValueError("retry me")
        return "ok"
    assert RetryPolicy(attempts=3, base_delay_s=0.0).run(flaky) == "ok"
    tb = TokenBucket(rate_per_s=1, capacity=1)
    assert tb.allow() is True and tb.allow() is False
    async def _saga():
        log = []
        s = Saga("d")
        s.add("a", lambda ctx: log.append("a") or 1, lambda ctx: log.append("undo-a"))
        def bad(ctx): raise ValueError("step-fail")
        s.add("b", bad, lambda ctx: log.append("undo-b"))
        out = await s.run({})
        assert out["ok"] is False and log == ["a", "undo-a"]
    asyncio.run(_saga())


def test_orchestration_dag_levels_parallel_and_skip():
    from eci.orchestration import DAG
    dag = DAG("t")
    dag.add("a", lambda ctx: 1)
    dag.add("b", lambda ctx: 2)
    dag.add("c", lambda ctx: ctx["a"] + ctx["b"], depends_on=["a", "b"])
    assert dag.levels()[0] == ["a", "b"]
    run = asyncio.run(dag.run({}))
    assert run.ok and run.outputs["c"] == 3
    dag2 = DAG("t2")
    def bad(ctx): raise ValueError("x")
    dag2.add("a", bad)
    dag2.add("b", lambda ctx: 1, depends_on=["a"])
    run2 = asyncio.run(dag2.run({}))
    assert run2.ok is False and "skipped" in run2.errors["b"]


def test_scheduler_priority_and_periodic():
    from eci.orchestration import Scheduler
    s = Scheduler()
    ran = []
    s.submit("low", lambda: ran.append("low"), priority=0)
    s.submit("high", lambda: ran.append("high"), priority=10)
    asyncio.run(s.run_due())
    assert set(ran) == {"low", "high"}
    s2 = Scheduler()
    s2.every("tick", 1000.0, lambda: None)
    out = asyncio.run(s2.run_due())
    assert out["ran"] == ["tick"] and s2.pending() == 1


def test_plugins_caps_and_order():
    from eci.plugins import PluginManager, PluginManifest
    pm = PluginManager()
    with pytest.raises(PermissionError):
        pm.register(PluginManifest("evil", capabilities=["llm.call"]), lambda ctx: None)
    pm.register(PluginManifest("base", capabilities=["bus.publish"]), lambda ctx: "b")
    pm.register(PluginManifest("top", capabilities=["store.read"], depends_on=["base"]), lambda ctx: "t")
    assert pm.load_order() == ["base", "top"]
    assert pm.load_all()["top"] == {"ok": True, "result": "t"}


def test_authz_rbac_abac_deny_closed():
    from eci.authz import Permission, PolicyEngine, PolicyRule, Role
    e = PolicyEngine()
    e.rbac.add_role(Role("agent", [Permission("tool.*", "*")]))
    e.rbac.grant("alice", "agent")
    assert e.decide("alice", "tool.run", "x").allow is False  # no ABAC rule => deny
    e.add_rule(PolicyRule("allow-tools", "tool.*", "*", {}, 0.5, 0.0, 0.0))
    assert e.decide("alice", "tool.run", "x", attestation={"awareness": 0.9}).allow is True
    assert e.decide("alice", "tool.run", "x", attestation={"awareness": 0.1}).allow is False
    assert e.decide("bob", "tool.run", "x").allow is False


def test_streaming_groups_and_backpressure():
    from eci.streaming import StreamBus
    b = StreamBus(default_capacity=2)
    b.publish("t", {"i": 1}); b.publish("t", {"i": 2}); b.publish("t", {"i": 3})
    assert b.topic("t").dropped == 1
    recs = b.poll("t", group="g1", limit=10)
    assert len(recs) == 2 and b.poll("t", group="g1") == []


def test_mlops_registry_and_drift():
    from eci.mlops import ModelRegistry, drift_report
    r = ModelRegistry()
    r.register("qnn", {"l": 2}, {"acc": 0.9}, {"run": "a"})
    v2 = r.register("qnn", {"l": 4}, {"acc": 0.95}, {"run": "b"})
    r.promote("qnn", v2.version)
    assert r.latest("qnn", "production").version == 2
    rep = drift_report([0.0] * 50 + [1.0] * 50, [0.0] * 50 + [1.0] * 50)
    assert rep["level"] == "none"
    rep2 = drift_report([0.0] * 100, [1.0] * 100)
    assert rep2["level"] == "drift" and rep2["retrain"] is True


def test_provenance_lineage_explain():
    from eci.provenance import ProvenanceGraph
    g = ProvenanceGraph()
    a = g.record("authz.decision", "alice", {"act": "vote"}, {"allow": True})
    b = g.record("dao.vote", "alice", {"pid": "p"}, {"w": 3}, parent=a.id)
    assert g.lineage(b.id)[0]["id"] == a.id
    assert "dao.vote" in g.explain(b.id)


def test_api_gateway_auth_limits_audit():
    from eci.api import Gateway
    from eci.authz import Permission, PolicyEngine, PolicyRule, Role
    e = PolicyEngine()
    e.rbac.add_role(Role("agent", [Permission("workflow.run", "*")]))
    e.rbac.grant("alice", "agent")
    e.add_rule(PolicyRule("w", "workflow.run", "*", {}))
    from eci.observability import AuditLogger
    g = Gateway(authz=e, audit=AuditLogger())
    g.add("v1/job.run", lambda p, c: {"n": p["n"] * 2}, auth_action="workflow.run")
    assert g.call("v1/job.run", {"n": 21}, {"subject": "alice"}) == {"ok": True, "data": {"n": 42}}
    assert g.call("v1/job.run", {"n": 1}, {"subject": "bob"})["ok"] is False
    assert g.call("nope", {}, {})["ok"] is False


def test_secrets_and_rotation():
    from eci.security.secrets import SecretManager
    s = SecretManager(master=b"0" * 32)
    s.put("k", b"v")
    assert s.get("k") == b"v"
    s.rotate(new_master=b"1" * 32)
    assert s.get("k") == b"v"


def test_secure_channel_seal_and_socket():
    from eci.security.secure_channel import HybridSecureChannel, SecureChannelConfig
    ch = HybridSecureChannel(SecureChannelConfig(psk=b"psk"))
    async def _go():
        await ch.broadcast("a", {"x": 1})
        # register b first via drain-time auto-register is sender-skipped;
        # explicitly register then re-broadcast
        ch.register("b")
        await ch.broadcast("a", {"x": 2})
        recs = await ch.drain("b")
        assert any(r.get("sealed") for r in recs)
    asyncio.run(_go())
    assert HybridSecureChannel(SecureChannelConfig()).socket_pair_ok()["ok"] is True


def test_tenancy_quotas():
    from eci.tenancy import Quota, TenancyManager
    t = TenancyManager()
    t.create("team-a", Quota(actions_per_epoch=2))
    assert t.admit("team-a") and t.admit("team-a") and not t.admit("team-a")


def test_chaos_plan_abort():
    from eci.chaos import ChaosPlan, Fault, run_plan
    async def _go():
        def probe(f):
            if f.kind == "kill": raise RuntimeError("node down")
        plan = ChaosPlan("p", [Fault("delay"), Fault("kill"), Fault("kill")],
                         abort_on_error_rate=0.5, seed=1)
        rep = await run_plan(plan, probe)
        assert rep.injected >= 2 and rep.to_dict()["plan"] == "p"
    asyncio.run(_go())


def test_config_env_overlay_and_flags():
    import os
    from eci.config import ECIConfig
    os.environ["ECI_QUANTUM_N_QUBITS"] = "5"
    try:
        cfg = ECIConfig.from_env()
        assert cfg.quantum.n_qubits == 5
    finally:
        del os.environ["ECI_QUANTUM_N_QUBITS"]
    assert ECIConfig().feature_flags["provenance"] is True


def test_facade_system_status_and_workflow_and_gateway():
    from eci.framework import ECIFramework
    fw = ECIFramework()
    st = fw.system_status()
    for k in ("kernel", "observability", "persistence", "resilience", "orchestration",
              "plugins", "authz", "streaming", "mlops", "provenance", "gateway",
              "tenancy", "secrets", "secure_channel"):
        assert k in st, k
    wf = asyncio.run(fw.workflow_demo())
    assert wf["ok"] is True and wf["outputs"]["act"]["result"] == 9
    assert "act" in wf["explanation"]
    assert fw.gateway.call("v1/ping", {}, {"subject": "anon"})["ok"] is True
    assert "v1/system.status" in fw.gateway.paths()
