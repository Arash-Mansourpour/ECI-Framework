"""ECI Protocol-0 MCP server (stdio JSON-RPC, zero extra deps).

Exposes attest / policy-check / ledger tools to any MCP-capable agent so
non-Python frameworks comply without installing ECI. Minimal JSON-RPC over
stdio: {"id","method","params"} <-> {"id","result"|"error"}.

Methods:
  tools/list
  tools/call {name, arguments} where name in:
    p0_attest {agent_id, awareness, obedience, trust}
    p0_check {action, awareness, obedience, trust}
    p0_ledger_append {kind, payload} / p0_ledger_verify
"""

from __future__ import annotations

import json
import sys

sys.path.insert(0, "src")

from eci.protocol0.attest import ReplayWindow, issue_attestation, verify_attestation
from eci.protocol0.ledger import Ledger
from eci.protocol0.policy import check
from eci.protocol0.spec import load_spec

SPEC = load_spec()
REPLAY = ReplayWindow(SPEC.replay_window)
LEDGER = Ledger()
KEYS: dict = {}


def _attest(p: dict) -> dict:
    import hashlib
    import hmac

    from eci.security.pqc import derive_key

    agent = str(p["agent_id"])
    key = KEYS.setdefault(agent, derive_key(b"mcp|" + agent.encode(), info=b"mcp-attest", length=32).hex())
    a = issue_attestation(agent, SPEC.version, float(p.get("awareness", 0)), float(p.get("obedience", 0)), float(p.get("trust", 0)))
    LEDGER.append("attest", {"agent": agent, "nonce": a.nonce})
    d = a.to_dict()
    d["agent_key_hint"] = "server-held (demo)"
    return d


def _check(p: dict) -> dict:
    d = check(SPEC, str(p["action"]), float(p.get("awareness", 0)), float(p.get("obedience", 0)), float(p.get("trust", 0)))
    return {"allow": d.allow, "reason": d.reason}


TOOLS = {
    "p0_attest": (_attest, "Issue a Protocol-0 attestation"),
    "p0_check": (_check, "Policy-gate an action"),
    "p0_ledger_append": (lambda p: LEDGER.append(str(p.get("kind", "note")), dict(p.get("payload", {}))), "Append ledger record"),
    "p0_ledger_verify": (lambda p: LEDGER.verify(), "Verify ledger chain"),
    "p0_spec": (lambda p: {"version": SPEC.version, "actions": sorted(SPEC.actions)}, "Spec version + actions"),
}


def handle(msg: dict) -> dict:
    mid, method, params = msg.get("id"), msg.get("method"), msg.get("params", {})
    try:
        if method == "initialize":
            return {"id": mid, "result": {"protocolVersion": "2024-11-05", "serverInfo": {"name": "eci-protocol0", "version": "0.1.0"}}}
        if method == "tools/list":
            return {"id": mid, "result": {"tools": [{"name": n, "description": f[1]} for n, f in TOOLS.items()]}}
        if method == "tools/call":
            name, args = params["name"], params.get("arguments", {})
            if name not in TOOLS:
                return {"id": mid, "error": f"unknown tool {name}"}
            return {"id": mid, "result": TOOLS[name][0](args)}
        return {"id": mid, "error": f"unknown method {method}"}
    except Exception as e:  # noqa: BLE001
        return {"id": mid, "error": f"{type(e).__name__}: {e}"}


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            print(json.dumps(handle(json.loads(line))), flush=True)
        except Exception as e:  # noqa: BLE001
            print(json.dumps({"id": None, "error": str(e)}), flush=True)


if __name__ == "__main__":
    main()
