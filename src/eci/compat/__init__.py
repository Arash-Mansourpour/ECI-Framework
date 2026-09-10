"""Interface evolution: versioned contracts with fail-closed compat.

Every subsystem publishes versioned interfaces {name, version, schema}.
Rules (the anti-ossification core):
  - major mismatch -> refuse (fail closed, like Protocol-0 semver)
  - minor provided < required -> refuse (missing fields possible)
  - patch differs -> allow (backwards-compatible by contract)
Adapters chain old->new migrations; deprecations carry sunset epochs and
twin-tested migration receipts. The future can change anything — it just
can't silently break the past.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

__all__ = ["Interface", "CompatRegistry"]


def _parse(v: str) -> Tuple[int, int, int]:
    parts = (v.split(".") + ["0", "0"])[:3]
    return int(parts[0]), int(parts[1]), int(parts[2])


@dataclass
class Interface:
    name: str
    version: str = "1.0.0"
    schema: Dict[str, Any] = field(default_factory=dict)
    status: str = "stable"       # stable | deprecated | retired
    sunset_epoch: int = 0
    receipt: str = ""            # twin migration-test reference


class CompatRegistry:
    name = "compat"

    def __init__(self) -> None:
        self.ifaces: Dict[str, Interface] = {}
        self.adapters: Dict[Tuple[str, str, str], Callable[[Any], Any]] = {}

    def publish(self, iface: Interface) -> None:
        self.ifaces[iface.name] = iface

    def check(self, name: str, required: str, epoch: int = 0) -> Dict[str, Any]:
        """Fail-closed compatibility verdict for (interface, required version)."""
        cur = self.ifaces.get(name)
        if cur is None:
            return {"ok": False, "error": f"unknown interface {name}"}
        if cur.status == "retired" or (cur.status == "deprecated" and cur.sunset_epoch and epoch > cur.sunset_epoch):
            return {"ok": False, "error": f"{name} retired (sunset epoch {cur.sunset_epoch})"}
        rmaj, rmin, _ = _parse(required)
        cmaj, cmin, _ = _parse(cur.version)
        if cmaj != rmaj:
            return {"ok": False, "error": f"major {cmaj} != {rmaj} (fail-closed)"}
        if cmin < rmin:
            return {"ok": False, "error": f"minor {cmin} < required {rmin}"}
        return {"ok": True, "provided": cur.version, "status": cur.status,
                "warn": "deprecated — migrate" if cur.status == "deprecated" else ""}

    def adapt(self, name: str, from_ver: str, fn: Callable[[Any], Any]) -> None:
        cur = self.ifaces.get(name)
        to_ver = cur.version if cur else from_ver
        self.adapters[(name, from_ver, to_ver)] = fn

    def migrate(self, name: str, data: Any, from_ver: str) -> Dict[str, Any]:
        cur = self.ifaces.get(name)
        if cur is None:
            return {"ok": False, "error": "unknown interface"}
        fn = self.adapters.get((name, from_ver, cur.version))
        if fn is None:
            return {"ok": from_ver == cur.version, "data": data,
                    "error": "" if from_ver == cur.version else "no adapter path"}
        try:
            return {"ok": True, "data": fn(data), "from": from_ver, "to": cur.version}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": repr(exc)}

    def deprecate(self, name: str, sunset_epoch: int, receipt: str = "") -> None:
        if name in self.ifaces:
            self.ifaces[name].status = "deprecated"
            self.ifaces[name].sunset_epoch = sunset_epoch
            self.ifaces[name].receipt = receipt

    def start(self) -> None: ...
    def stop(self) -> None: ...
    def health(self) -> Dict[str, Any]:
        return {"ok": True, "interfaces": len(self.ifaces), "adapters": len(self.adapters)}
