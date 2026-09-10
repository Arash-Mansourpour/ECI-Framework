"""Runtime verification: invariants that watch + proofs that travel.

Two mechanisms, one guarantee — *nothing safety-critical happens
unobserved*:

1. Monitors: LTL-lite invariants over the event bus —
   ``always(p)`` (every matching event satisfies p),
   ``never(p)`` (no matching event satisfies p),
   ``bounded-response(trigger, response, k)`` (every trigger is followed
   by a response within k events). Violations latch with the witness.
2. Proof receipts: every gated action returns {action, policy_version,
   checks[], measurements, hash}. ``verify_proof()`` recomputes the hash
   and re-validates each check against a named-check registry — offline,
   by courts, auditors, or other meshes.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

__all__ = ["Monitor", "Watchtower", "CHECKS", "seal_proof", "verify_proof"]

# Named checks usable inside persisted proofs (serializable by name)
CHECKS: Dict[str, Callable[[Dict[str, Any]], bool]] = {
    "nonnegative": lambda m: all(v >= 0 for v in m.values() if isinstance(v, (int, float))),
    "quorum_met": lambda m: float(m.get("approvals", 0)) >= float(m.get("required", 1)),
    "budget_respected": lambda m: float(m.get("spent", 0)) <= float(m.get("budget", 0)),
    "attested": lambda m: bool(m.get("attestation_ok", False)),
}


@dataclass
class Monitor:
    name: str
    kind: str              # always | never | bounded-response
    match: str             # event-type substring filter ("" = all)
    predicate: Callable[[Dict[str, Any]], bool] = field(repr=False, default=lambda p: True)
    bound: int = 10
    status: str = "ok"     # ok | violated
    witness: Dict[str, Any] = field(default_factory=dict)
    seen: int = 0

    def observe(self, etype: str, payload: Dict[str, Any]) -> None:
        if self.match and self.match not in etype:
            return
        self.seen += 1
        try:
            holds = bool(self.predicate(payload))
        except Exception:  # noqa: BLE001
            holds = False
        if self.kind == "always" and not holds:
            self.status, self.witness = "violated", {"event": etype, "payload": payload}
        elif self.kind == "never" and holds:
            self.status, self.witness = "violated", {"event": etype, "payload": payload}

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "kind": self.kind, "status": self.status,
                "seen": self.seen, "witness": self.witness}


class Watchtower:
    """Owns monitors + pending bounded-response obligations."""

    def __init__(self, bus=None) -> None:
        self.monitors: List[Monitor] = []
        self.bus = bus
        self._pending: List[Dict[str, Any]] = []  # {resp_match, deadline_idx, trigger}
        self._idx = 0
        self.violations = 0

    def watch(self, monitor: Monitor, response_match: str = "") -> Monitor:
        self.monitors.append(monitor)
        if monitor.kind == "bounded-response":
            self._resp = getattr(self, "_resp", {})
            self._resp[monitor.name] = response_match
        return monitor

    def observe(self, etype: str, payload: Dict[str, Any] | None = None) -> List[str]:
        """Feed one event; returns names of newly-violated monitors."""
        payload = payload or {}
        self._idx += 1
        fresh = []
        for m in self.monitors:
            before = m.status
            m.observe(etype, payload)
            if m.kind == "bounded-response" and m.match in etype:
                self._pending.append({"resp": getattr(self, "_resp", {}).get(m.name, ""),
                                      "deadline": self._idx + m.bound, "trigger": etype, "mon": m.name})
            if m.status == "violated" and before != "violated":
                fresh.append(m.name)
                self.violations += 1
        # resolve bounded-response obligations
        still = []
        for p in self._pending:
            if p["resp"] and p["resp"] in etype:
                continue  # answered
            if self._idx > p["deadline"]:
                for m in self.monitors:
                    if m.name == p["mon"] and m.status == "ok":
                        m.status, m.witness = "violated", {"trigger": p["trigger"], "missed": p["resp"]}
                        fresh.append(m.name)
                        self.violations += 1
            else:
                still.append(p)
        self._pending = still
        return fresh

    def bind_bus(self, bus: Any) -> None:
        self.bus = bus
        try:
            bus.subscribe("*", lambda e: self.observe(e.type, dict(e.payload)), name="watchtower")
        except Exception:  # noqa: BLE001
            pass

    def health(self) -> Dict[str, Any]:
        return {"ok": all(m.status == "ok" for m in self.monitors),
                "monitors": [m.to_dict() for m in self.monitors],
                "pending": len(self._pending), "violations": self.violations}


def seal_proof(action: str, policy_version: str, checks: List[Dict[str, Any]],
               measurements: Dict[str, Any] | None = None) -> Dict[str, Any]:
    body = {"action": action, "policy": policy_version, "checks": checks,
            "measurements": measurements or {}, "ts": time.time()}
    body["hash"] = hashlib.sha256(
        json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()
    return body


def verify_proof(proof: Dict[str, Any], expected_policy: str = "") -> Dict[str, Any]:
    p = dict(proof)
    h = p.pop("hash", "")
    recomputed = hashlib.sha256(json.dumps(p, sort_keys=True, default=str).encode()).hexdigest()
    if recomputed != h:
        return {"ok": False, "error": "hash mismatch (tampered proof)"}
    if expected_policy and p.get("policy") != expected_policy:
        return {"ok": False, "error": "stale policy version"}
    for c in p.get("checks", []):
        fn = CHECKS.get(c.get("check", ""))
        if fn is None:
            return {"ok": False, "error": f"unknown check {c.get('check')!r}"}
        try:
            ok = fn(c.get("with", {}))
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": f"check crashed: {exc}"}
        if not (ok and c.get("ok")):
            return {"ok": False, "error": f"check failed: {c.get('check')}"}
    return {"ok": True, "action": p.get("action"), "checks": len(p.get("checks", []))}
