"""A4 coverage: OTel real-export path (mocked, no backend) + p2p TCP/gossip/recovery."""

from __future__ import annotations

import asyncio
import sys
import types


def _fake_otel_module(fail_attr: bool = False, fail_span: bool = False):
    calls: dict = {"attrs": [], "spans": 0}

    class FakeSpan:
        def set_attribute(self, k, v):
            if fail_attr:
                raise RuntimeError("collector down")
            calls["attrs"].append((k, v))

    class FakeCtx:
        def __enter__(self):
            calls["spans"] += 1
            if fail_span:
                raise RuntimeError("no collector")
            return FakeSpan()

        def __exit__(self, *a):
            return False

    class FakeTracer:
        def start_as_current_span(self, name):
            calls["last_name"] = name
            return FakeCtx()

    stub = types.ModuleType("opentelemetry")
    trace_mod = types.ModuleType("opentelemetry.trace")
    trace_mod.get_tracer = lambda service: FakeTracer()
    stub.trace = trace_mod
    sys.modules["opentelemetry"] = stub
    sys.modules["opentelemetry.trace"] = trace_mod
    return calls


def test_otel_real_export_path_mocked(monkeypatch):
    from eci.observability.otel import OtelBridge

    monkeypatch.delitem(sys.modules, "opentelemetry", raising=False)
    monkeypatch.delitem(sys.modules, "opentelemetry.trace", raising=False)
    calls = _fake_otel_module()
    br = OtelBridge(service="test")
    assert br.available is True
    with br.span("demo", {"k": "v"}) as span:
        assert hasattr(span, "set_attribute")
    assert calls["spans"] == 1
    assert calls["attrs"] == [("k", "v")]
    assert calls["last_name"] == "demo"
    assert br.health() == {"otel_available": True, "service": "test"}


def test_otel_noop_when_sdk_absent(monkeypatch):
    from eci.observability.otel import OtelBridge

    monkeypatch.setitem(sys.modules, "opentelemetry", None)
    monkeypatch.delitem(sys.modules, "opentelemetry.trace", raising=False)
    br = OtelBridge()
    assert br.available is False
    with br.span("x", {"a": 1}) as out:
        assert out == {"name": "x", "noop": True, "attributes": {"a": 1}}


def test_otel_attribute_error_still_yields_span(monkeypatch):
    from eci.observability.otel import OtelBridge

    monkeypatch.delitem(sys.modules, "opentelemetry", raising=False)
    monkeypatch.delitem(sys.modules, "opentelemetry.trace", raising=False)
    _fake_otel_module(fail_attr=True)
    br = OtelBridge()
    with br.span("s", {"k": "v"}) as span:
        assert hasattr(span, "set_attribute")  # yielded despite collector error


def test_otel_outer_exception_falls_back(monkeypatch):
    from eci.observability.otel import OtelBridge

    monkeypatch.delitem(sys.modules, "opentelemetry", raising=False)
    monkeypatch.delitem(sys.modules, "opentelemetry.trace", raising=False)
    _fake_otel_module(fail_span=True)
    br = OtelBridge()
    with br.span("s") as out:
        assert out == {"name": "s", "noop": True, "fallback": True}


def test_p2p_partition_heal_recovery():
    from eci.federation.p2p import build_mesh

    nodes, transport = build_mesh(4)
    primary = nodes[0]
    primary.propose({"op": "a"})
    assert sum(n.commit_count() for n in nodes) == 4
    assert transport.health()["partitioned"] is False
    transport.partition({primary.node_id})
    assert transport.health()["partitioned"] is True
    primary.propose({"op": "b"})
    dropped_after = transport.dropped
    assert dropped_after > 0
    stalled = sum(n.commit_count() for n in nodes)
    assert stalled == 4  # no new commits reach a quorum while isolated
    transport.heal()
    assert transport.health()["partitioned"] is False
    primary.propose({"op": "c"})
    assert sum(n.commit_count() for n in nodes) == 8
    assert transport.delivered > dropped_after


def test_p2p_multinode_gossip_propagation():
    from eci.federation.p2p import build_mesh

    nodes, _t = build_mesh(7)
    for i, proposer in enumerate((nodes[0], nodes[3], nodes[6])):
        proposer.propose({"op": f"m{i}"})
    counts = [n.commit_count() for n in nodes]
    assert counts == [3] * 7  # every node committed all three proposals
    assert nodes[0].to_dict() == {"node_id": "node-0", "view": 0, "seq": 1,
                                  "committed": 3, "peers": 6}


def test_p2p_tcp_roundtrip_and_malformed_frame():
    import socket

    from eci.federation.p2p import TCPTransport

    async def main():
        got: list = []
        a = TCPTransport("a", 18771)
        b = TCPTransport("b", 18772)
        a.register("a", got.append)
        b.register("b", got.append)
        a.add_peer("b", "127.0.0.1", 18772)
        b.add_peer("a", "127.0.0.1", 18771)
        await a.start()
        await b.start()
        a.send("ghost", {"x": 1})  # unknown peer: early return, no crash
        a.send("b", {"kind": "ping", "from": "a", "n": 1})
        b.broadcast({"kind": "pong", "from": "b"})
        await asyncio.sleep(0.5)
        # malformed frame -> _on_conn except + finally paths
        s = socket.socket()
        s.connect(("127.0.0.1", 18771))
        s.sendall(b"\x00\x01")
        s.close()
        await asyncio.sleep(0.3)
        a._server.close()
        b._server.close()
        return got, a, b

    got, a, b = asyncio.run(main())
    kinds = sorted(m.get("kind") for m in got)
    assert kinds == ["ping", "pong"], got
    assert a.health() == {"backend": "tcp", "node": "a", "port": 18771,
                          "peers": 1, "sent": 1}
    assert b.health()["sent"] == 1


def test_p2p_send_from_sync_context_uses_asyncio_run():
    """No running loop -> the asyncio.run fallback branch (p2p.py send)."""
    import threading

    from eci.federation.p2p import TCPTransport

    got: list = []
    ready = threading.Event()

    def serve():
        async def main():
            b = TCPTransport("b", 18781)
            b.register("b", got.append)
            await b.start()
            ready.set()
            await asyncio.sleep(3.0)
            b._server.close()

        asyncio.run(main())

    t = threading.Thread(target=serve, daemon=True)
    t.start()
    assert ready.wait(timeout=10)
    a = TCPTransport("a", 18780)
    a.add_peer("b", "127.0.0.1", 18781)
    a.send("b", {"kind": "hello", "from": "a"})
    t.join(timeout=10)
    assert [m.get("kind") for m in got] == ["hello"]
    assert a.sent == 1
