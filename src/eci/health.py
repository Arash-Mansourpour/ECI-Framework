"""Health + metrics: /health (JSON) and /metrics (Prometheus text), stdlib only.

Status = {version, profile, ledger_height, ledger_ok, peers, collective_gate,
uptime_s}. Any orchestrator (Docker, k8s, systemd) can gate restarts and
rollouts on it. `eci health --once` prints JSON; `--serve` binds HTTP.
"""

from __future__ import annotations

import asyncio
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

__all__ = ["status", "metrics_text", "serve"]

_STARTED = time.time()


def status(ledger=None, peers: int | None = None, collective_gate: str = "unknown") -> dict[str, Any]:
    from eci.version import FRAMEWORK_VERSION

    height, ok = 0, True
    if ledger is not None:
        try:
            height = len(ledger.records)
            ok = bool(ledger.verify()["ok"])
        except Exception:  # noqa: BLE001
            ok = False
    if peers is None:
        peers = _peer_count()
    return {
        "ok": ok, "version": FRAMEWORK_VERSION,
        "profile": os.environ.get("ECI_PROFILE", "server"),
        "node": os.environ.get("ECI_NODE_ID", "local"),
        "ledger_height": height, "ledger_ok": ok,
        "peers": peers, "collective_gate": collective_gate,
        "uptime_s": round(time.time() - _STARTED, 1),
    }


def metrics_text(st: dict[str, Any]) -> str:
    rows = [
        ("eci_up", 1 if st["ok"] else 0), ("eci_ledger_height", st["ledger_height"]),
        ("eci_ledger_ok", 1 if st["ledger_ok"] else 0), ("eci_peers", st["peers"]),
        ("eci_uptime_s", st["uptime_s"]),
    ]
    return "".join(f"# TYPE {k} gauge\n{k} {v}\n" for k, v in rows)


class _Handler(BaseHTTPRequestHandler):
    state: dict[str, Any] = {}

    def log_message(self, *a: Any) -> None:  # quiet
        pass

    def do_GET(self) -> None:  # noqa: N802
        st = status()
        if self.path == "/metrics":
            body, ctype = metrics_text(st).encode(), "text/plain"
        elif self.path == "/gossip":
            body, ctype = json.dumps(gossip_status()).encode(), "application/json"
        else:
            body, ctype = json.dumps(st).encode(), "application/json"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def serve(port: int | None = None) -> None:
    if port is None:
        port = int(os.environ.get("ECI_PORT", "8777"))
    bootstrap_gossip(port=port)
    srv = HTTPServer(("0.0.0.0", port), _Handler)
    print(f"eci health on :{port} (/health /metrics /gossip)", flush=True)
    try:
        srv.serve_forever()
    finally:
        stop_gossip()


_GOSSIP_TRANSPORT = None
_GOSSIP_NODE = None
_GOSSIP_THREAD = None
_GOSSIP_LOOP = None
_GOSSIP_SERVER = None


def _parse_bootstrap(value: str) -> list[tuple[str, int]]:
    peers: list[tuple[str, int]] = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        if ":" in item:
            host, raw_port = item.rsplit(":", 1)
            peers.append((host.strip(), int(raw_port)))
        else:
            peers.append((item, 8777))
    return peers


def _peer_count() -> int:
    global _GOSSIP_TRANSPORT
    transport = _GOSSIP_TRANSPORT
    if transport is None:
        return 0
    peers = getattr(transport, "peers", {})
    try:
        return len(peers)
    except Exception:  # noqa: BLE001
        return 0


def gossip_status() -> dict[str, Any]:
    global _GOSSIP_TRANSPORT, _GOSSIP_NODE
    transport_health: dict[str, Any] = {}
    if _GOSSIP_TRANSPORT is not None and hasattr(_GOSSIP_TRANSPORT, "health"):
        try:
            transport_health = _GOSSIP_TRANSPORT.health()
        except Exception as exc:  # noqa: BLE001
            transport_health = {"ok": False, "error": repr(exc)}
    node_health: dict[str, Any] = {}
    if _GOSSIP_NODE is not None and hasattr(_GOSSIP_NODE, "to_dict"):
        try:
            node_health = _GOSSIP_NODE.to_dict()
        except Exception as exc:  # noqa: BLE001
            node_health = {"ok": False, "error": repr(exc)}
    return {
        "ok": True,
        "transport": transport_health,
        "node": node_health,
        "bootstrap": os.environ.get("ECI_BOOTSTRAP", ""),
    }


def bootstrap_gossip(node_id: str | None = None, port: int | None = None,
                     bootstrap: str | None = None) -> dict[str, Any]:
    global _GOSSIP_TRANSPORT, _GOSSIP_NODE, _GOSSIP_THREAD, _GOSSIP_LOOP, _GOSSIP_SERVER
    if _GOSSIP_TRANSPORT is not None:
        return {"ok": True, "already": True, "peers": _peer_count()}
    resolved_node_id = node_id or os.environ.get("ECI_NODE_ID", "local")
    resolved_node_id = str(resolved_node_id)
    if port is None:
        port = int(os.environ.get("ECI_PORT", "8777"))
    if bootstrap is None:
        bootstrap = os.environ.get("ECI_BOOTSTRAP", "")
    if not bootstrap:
        return {"ok": True, "enabled": False, "peers": 0}
    try:
        from eci.network.tcp import FramedTcpTransport
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": repr(exc)}
    transport = FramedTcpTransport(node_id=resolved_node_id, host="0.0.0.0", port=port)
    for host, peer_port in _parse_bootstrap(bootstrap):
        transport.add_peer(f"{host}:{peer_port}", host, peer_port)
    loop = asyncio.new_event_loop()

    def runner() -> None:
        global _GOSSIP_SERVER
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(transport.start())
            server = transport._server
            _GOSSIP_SERVER = server
            if server is not None:
                loop.run_until_complete(server.serve_forever())
        except (asyncio.CancelledError, RuntimeError, OSError):
            pass
        finally:
            try:
                loop.close()
            except Exception:  # noqa: BLE001
                pass

    thread = threading.Thread(target=runner, name=f"eci-gossip-{resolved_node_id}", daemon=True)
    thread.start()
    # Wait briefly for the listener to be ready.
    deadline = time.time() + 2.0
    while time.time() < deadline:
        if getattr(transport, "_server", None) is not None:
            break
        time.sleep(0.05)
    try:
        asyncio.run_coroutine_threadsafe(
            transport.broadcast(resolved_node_id, {"kind": "hello", "node": resolved_node_id, "port": port}),
            loop,
        )
    except Exception:  # noqa: BLE001
        pass
    _GOSSIP_TRANSPORT = transport
    _GOSSIP_NODE = None
    _GOSSIP_THREAD = thread
    _GOSSIP_LOOP = loop
    return {"ok": True, "enabled": True, "node": resolved_node_id, "port": port,
            "peers": len(transport.peers)}


def stop_gossip() -> None:
    global _GOSSIP_TRANSPORT, _GOSSIP_NODE, _GOSSIP_THREAD, _GOSSIP_LOOP, _GOSSIP_SERVER
    server = _GOSSIP_SERVER
    loop = _GOSSIP_LOOP
    if server is not None and loop is not None:
        try:
            loop.call_soon_threadsafe(server.close)
        except Exception:  # noqa: BLE001
            try:
                server.close()
            except Exception:  # noqa: BLE001
                pass
    thread = _GOSSIP_THREAD
    if thread is not None and thread.is_alive():
        thread.join(timeout=2.0)
    _GOSSIP_TRANSPORT = None
    _GOSSIP_NODE = None
    _GOSSIP_THREAD = None
    _GOSSIP_LOOP = None
    _GOSSIP_SERVER = None
