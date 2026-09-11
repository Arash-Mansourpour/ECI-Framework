"""Built-in MCP resources: live framework state as addressable URIs.

Resources are read-only snapshots (resources/list, resources/read) plus
subscriptions (resources/subscribe -> SSE/bus events). URIs:

  eci://info, eci://system.status, eci://metrics, eci://ledger/head,
  eci://treasury, eci://governance/proposals, eci://eval/gates,
  eci://sbom, eci://gateway/schema
"""

from __future__ import annotations

from typing import Any

__all__ = ["RESOURCES", "read_resource"]


def _r(uri: str, name: str, mime: str = "application/json") -> dict[str, Any]:
    return {"uri": uri, "name": name, "mimeType": mime}


RESOURCES: list[dict[str, Any]] = [
    _r("eci://info", "framework info"),
    _r("eci://system.status", "hyper-architecture status"),
    _r("eci://metrics", "prometheus metrics", "text/plain"),
    _r("eci://gateway/schema", "api + tool schema"),
    _r("eci://treasury", "treasury status"),
    _r("eci://eval/gates", "regression gates"),
    _r("eci://sbom", "supply-chain SBOM"),
]


def read_resource(uri: str, framework: Any) -> dict[str, Any]:
    try:
        if uri == "eci://info":
            return {"ok": True, "data": framework.info()}
        if uri == "eci://system.status":
            return {"ok": True, "data": framework.system_status()}
        if uri == "eci://metrics":
            return {"ok": True, "data": framework.observability.metrics.to_prometheus(), "mime": "text/plain"}
        if uri == "eci://gateway/schema":
            return {"ok": True, "data": framework.gateway.schema()}
        if uri == "eci://treasury":
            t = getattr(framework, "treasury", None)
            return {"ok": True, "data": t.status() if t else {"treasury": "absent"}}
        if uri == "eci://eval/gates":
            from eci.eval import run_gates
            return {"ok": True, "data": run_gates().to_dict()}
        if uri == "eci://sbom":
            from eci.supply import sbom
            return {"ok": True, "data": sbom()}
        return {"ok": False, "error": f"unknown resource {uri}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": repr(exc)}
