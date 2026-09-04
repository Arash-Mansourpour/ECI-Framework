"""Health + metrics: /health (JSON) and /metrics (Prometheus text), stdlib only.

Status = {version, profile, ledger_height, ledger_ok, peers, collective_gate,
uptime_s}. Any orchestrator (Docker, k8s, systemd) can gate restarts and
rollouts on it. `eci health --once` prints JSON; `--serve` binds HTTP.
"""

from __future__ import annotations

import json
import os
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, Optional

__all__ = ["status", "metrics_text", "serve"]

_STARTED = time.time()


def status(ledger=None, peers: int = 0, collective_gate: str = "unknown") -> Dict[str, Any]:
    from eci.version import FRAMEWORK_VERSION

    height, ok = 0, True
    if ledger is not None:
        try:
            height = len(ledger.records)
            ok = bool(ledger.verify()["ok"])
        except Exception:  # noqa: BLE001
            ok = False
    return {
        "ok": ok, "version": FRAMEWORK_VERSION,
        "profile": os.environ.get("ECI_PROFILE", "server"),
        "node": os.environ.get("ECI_NODE_ID", "local"),
        "ledger_height": height, "ledger_ok": ok,
        "peers": peers, "collective_gate": collective_gate,
        "uptime_s": round(time.time() - _STARTED, 1),
    }


def metrics_text(st: Dict[str, Any]) -> str:
    rows = [
        ("eci_up", 1 if st["ok"] else 0), ("eci_ledger_height", st["ledger_height"]),
        ("eci_ledger_ok", 1 if st["ledger_ok"] else 0), ("eci_peers", st["peers"]),
        ("eci_uptime_s", st["uptime_s"]),
    ]
    return "".join(f"# TYPE {k} gauge\n{k} {v}\n" for k, v in rows)


class _Handler(BaseHTTPRequestHandler):
    state: Dict[str, Any] = {}

    def log_message(self, *a: Any) -> None:  # quiet
        pass

    def do_GET(self) -> None:  # noqa: N802
        st = status()
        if self.path == "/metrics":
            body, ctype = metrics_text(st).encode(), "text/plain"
        else:
            body, ctype = json.dumps(st).encode(), "application/json"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def serve(port: int = 8777) -> None:
    srv = HTTPServer(("0.0.0.0", port), _Handler)
    print(f"eci health on :{port} (/health /metrics)", flush=True)
    srv.serve_forever()
