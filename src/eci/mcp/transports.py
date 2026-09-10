"""Transports: stdio (classic MCP) + HTTP/SSE (stdlib) + in-process.

All transports speak the same JSON-RPC surface via McpServer.handle():
stdio for Claude Desktop-style hosts, HTTP POST /mcp for services, SSE
GET /mcp/events for bus-bridged notifications, in-process for tests and
the agent loop. No third-party web framework required.
"""

from __future__ import annotations

import asyncio
import json
import queue
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable, Dict, Optional

__all__ = ["InProcessTransport", "StdioTransport", "HttpTransport"]


class InProcessTransport:
    """Direct handle() calls — fastest path for tests/agents."""

    def __init__(self, handler: Callable[[Dict[str, Any]], Any]) -> None:
        self._h = handler

    def request(self, method: str, params: Dict[str, Any] | None = None, _id: Any = 1) -> Dict[str, Any]:
        res = self._h({"id": _id, "method": method, "params": params or {}})
        if asyncio.iscoroutine(res):
            res = asyncio.run(res)
        return res


class StdioTransport:
    def __init__(self, handler: Callable[[Dict[str, Any]], Any]) -> None:
        self._h = handler

    def serve_forever(self) -> None:
        import sys
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except Exception as exc:  # noqa: BLE001
                print(json.dumps({"id": None, "error": f"bad json: {exc}"}), flush=True)
                continue
            try:
                res = self._h(msg)
                if asyncio.iscoroutine(res):
                    res = asyncio.run(res)
                print(json.dumps(res, default=str), flush=True)
            except Exception as exc:  # noqa: BLE001
                print(json.dumps({"id": msg.get("id"), "error": repr(exc)}), flush=True)


class HttpTransport:
    """POST /mcp (JSON-RPC), GET /mcp/tools, GET /mcp/events (SSE)."""

    def __init__(self, handler: Callable[[Dict[str, Any]], Any], host: str = "127.0.0.1", port: int = 8899) -> None:
        self.handler = handler
        self.host = host
        self.port = port
        self._subs: "queue.Queue[str]" = queue.Queue()
        self._httpd: Optional[HTTPServer] = None

    def notify(self, event: Dict[str, Any]) -> None:
        try:
            self._subs.put_nowait(json.dumps(event, default=str))
        except queue.Full:
            pass

    def serve_forever(self) -> None:
        handler_fn = self.handler
        subs = self._subs

        class _H(BaseHTTPRequestHandler):
            def log_message(self, *a: Any) -> None:
                pass

            def _send(self, body: bytes, ctype: str = "application/json") -> None:
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self) -> None:  # noqa: N802
                if self.path != "/mcp":
                    self.send_response(404); self.end_headers(); return
                ln = int(self.headers.get("Content-Length", 0))
                try:
                    msg = json.loads(self.rfile.read(ln) or b"{}")
                except Exception as exc:  # noqa: BLE001
                    self._send(json.dumps({"error": f"bad json: {exc}"}).encode()); return
                res = handler_fn(msg)
                if asyncio.iscoroutine(res):
                    res = asyncio.run(res)
                self._send(json.dumps(res, default=str).encode())

            def do_GET(self) -> None:  # noqa: N802
                if self.path == "/mcp/tools":
                    res = handler_fn({"id": 1, "method": "tools/list", "params": {}})
                    if asyncio.iscoroutine(res):
                        res = asyncio.run(res)
                    self._send(json.dumps(res, default=str).encode()); return
                if self.path == "/mcp/events":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.end_headers()
                    try:
                        while True:
                            data = subs.get(timeout=25)
                            self.wfile.write(f"data: {data}\n\n".encode())
                            self.wfile.flush()
                    except Exception:  # noqa: BLE001
                        pass
                    return
                self.send_response(404); self.end_headers()

        self._httpd = HTTPServer((self.host, self.port), _H)
        self.port = self._httpd.server_address[1]
        print(f"eci-mcp http on {self.host}:{self.port} (POST /mcp, GET /mcp/tools, GET /mcp/events)", flush=True)
        self._httpd.serve_forever()
