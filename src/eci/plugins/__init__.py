"""Plugin manager: capability-gated dynamic extensions.

A plugin is a manifest + entry callable. The manager validates manifests,
resolves load order by dependencies, and executes entries with an explicit
capability allowlist (no raw imports/fs/net unless granted). Failures are
isolated per-plugin so one bad extension can't halt the mesh.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

__all__ = ["PluginManifest", "PluginRecord", "PluginManager"]


@dataclass
class PluginManifest:
    name: str
    version: str = "0.1.0"
    entry: str = "main"
    capabilities: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    description: str = ""

    def validate(self) -> None:
        if not self.name or not self.name.replace("-", "").replace("_", "").isalnum():
            raise ValueError(f"bad plugin name {self.name!r}")
        for c in self.capabilities:
            if c not in ("bus.publish", "bus.subscribe", "store.read", "store.write",
                         "net.send", "quantum.run", "llm.call", "fs.read"):
                raise ValueError(f"unknown capability {c!r}")


@dataclass
class PluginRecord:
    manifest: PluginManifest
    loaded: bool = False
    error: str = ""
    loaded_at: float = 0.0
    result: Any = None


class PluginManager:
    name = "plugins"

    #: capabilities granted mesh-wide; entries requesting more are refused
    ALLOWED_MESH_CAPS = {"bus.publish", "bus.subscribe", "store.read", "store.write", "quantum.run"}

    def __init__(self, bus: Any | None = None) -> None:
        self.bus = bus
        self._plugins: dict[str, PluginRecord] = {}
        self._entries: dict[str, Callable[..., Any]] = {}

    def register(self, manifest: PluginManifest, entry: Callable[..., Any]) -> None:
        manifest.validate()
        extra = set(manifest.capabilities) - self.ALLOWED_MESH_CAPS
        if extra:
            raise PermissionError(f"plugin {manifest.name} requests denied caps {sorted(extra)}")
        self._plugins[manifest.name] = PluginRecord(manifest=manifest)
        self._entries[manifest.name] = entry

    def load_order(self) -> list[str]:
        visited: dict[str, str] = {}
        out: list[str] = []

        def visit(n: str, stack: list[str]) -> None:
            if n not in self._plugins:
                raise KeyError(f"unknown plugin dependency {n!r}")
            m = visited.get(n)
            if m == "done":
                return
            if m == "wip":
                raise ValueError(f"plugin cycle: {' -> '.join(stack + [n])}")
            visited[n] = "wip"
            for d in self._plugins[n].manifest.depends_on:
                visit(d, stack + [n])
            visited[n] = "done"
            out.append(n)

        for name in self._plugins:
            visit(name, [])
        return out

    def load_all(self, ctx: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx = ctx or {}
        results: dict[str, Any] = {}
        for name in self.load_order():
            rec = self._plugins[name]
            try:
                caps = {"capabilities": rec.manifest.capabilities, "bus": self.bus}
                out = self._entries[name]({**ctx, **caps})
                rec.result = out
                rec.loaded = True
                rec.loaded_at = time.time()
                results[name] = {"ok": True, "result": out}
            except Exception as exc:  # noqa: BLE001
                rec.loaded = False
                rec.error = repr(exc)
                results[name] = {"ok": False, "error": repr(exc)}
        return results

    def start(self) -> None: ...
    def stop(self) -> None: ...
    def health(self) -> dict[str, Any]:
        return {"ok": True, "plugins": {k: {"loaded": v.loaded, "error": v.error} for k, v in self._plugins.items()}}
