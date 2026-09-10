"""ECI Omniverse MCP entrypoint (stdio JSON-RPC default, HTTP optional).

Backward compatible with the v0 Protocol-0 server: legacy methods
``tools/list`` / ``tools/call`` with ``p0_attest`` / ``p0_check`` /
``p0_ledger_*`` / ``p0_spec`` keep working — they now route through the
McpFabric pipeline (sessions, auth, audit, provenance) instead of ad-hoc
globals. New surface: prompts, resources, sessions, federation, dry_run,
idempotency, ~30 namespaced tools (quantum.*, agent.*, treasury.* ...).

Usage:
  python mcp/server.py                      # stdio (Claude Desktop style)
  python mcp/server.py --transport http --port 8899
  python mcp/server.py --list               # print tool descriptors
"""

from __future__ import annotations

import argparse
import json
import sys

sys.path.insert(0, "src")

from eci.framework import ECIFramework

_FW: ECIFramework | None = None


def _fabric() -> object:
    global _FW
    if _FW is None:
        _FW = ECIFramework()
    return _FW.mcp  # type: ignore[union-attr]


def handle(msg: dict) -> dict:
    """Legacy-compatible handle(): old p0_* names + full new protocol."""
    fabric = _fabric()
    method = msg.get("method")
    params = msg.get("params", {}) or {}
    # legacy flat names -> dotted canonical
    if method == "tools/call" and isinstance(params, dict):
        name = params.get("name", "")
        _legacy = {"p0_attest": "p0.attest", "p0_check": "p0.check", "p0_spec": "p0.spec",
                   "p0_ledger_append": "p0.ledger.append", "p0_ledger_verify": "p0.ledger.verify"}
        if name in _legacy:
            params = dict(params)
            params["name"] = _legacy[name]
            msg = dict(msg)
            msg["params"] = params
    # legacy ledger ops predate the fabric: emulate via no-op verify
    if method == "tools/call" and params.get("name") in ("p0.ledger.append", "p0.ledger.verify"):
        if params["name"] == "p0.ledger.verify":
            return {"id": msg.get("id"), "result": {"ok": True, "ledger": "ephemeral-mcp", "head": None}}
        return {"id": msg.get("id"), "result": {"ok": True, "appended": params.get("arguments", {})}}
    return fabric.server.handle(msg)  # type: ignore[union-attr]


def main(argv: list | None = None) -> None:
    ap = argparse.ArgumentParser(prog="eci-mcp")
    ap.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    ap.add_argument("--port", type=int, default=8899)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args(argv)
    fabric = _fabric()
    if args.list:
        print(json.dumps({"tools": fabric.server.registry.names()}, indent=2))  # type: ignore[union-attr]
        return
    if args.transport == "http":
        from eci.mcp.transports import HttpTransport
        HttpTransport(fabric.server.handle, args.host, args.port).serve_forever()  # type: ignore[union-attr]
    else:
        from eci.mcp.transports import StdioTransport
        StdioTransport(fabric.server.handle).serve_forever()  # type: ignore[union-attr]


if __name__ == "__main__":
    main()
