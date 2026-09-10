"""Dependency-injection container with cycle detection and test overrides."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

__all__ = ["Container", "CircularDependencyError"]


class CircularDependencyError(RuntimeError):
    pass


@dataclass
class _Binding:
    factory: Callable[..., Any] | None = None
    instance: Any = None
    singleton: bool = True
    cached: Any = None
    has_cached: bool = False


class Container:
    """Minimal DI container: register factories/instances, resolve by name."""

    def __init__(self) -> None:
        self._bindings: Dict[str, _Binding] = {}
        self._resolving: List[str] = []

    def register(self, name: str, factory: Callable[..., Any] | None = None,
                 instance: Any = None, singleton: bool = True) -> None:
        if factory is None and instance is None:
            raise ValueError("register requires factory or instance")
        self._bindings[name] = _Binding(factory=factory, instance=instance,
                                        singleton=singleton)

    def override(self, name: str, instance: Any) -> None:
        self._bindings[name] = _Binding(instance=instance, singleton=True,
                                        cached=instance, has_cached=True)

    def has(self, name: str) -> bool:
        return name in self._bindings

    def names(self) -> List[str]:
        return sorted(self._bindings)

    def resolve(self, name: str) -> Any:
        if name not in self._bindings:
            raise KeyError(f"no binding for {name!r}")
        if name in self._resolving:
            chain = " -> ".join(self._resolving + [name])
            raise CircularDependencyError(f"circular dependency: {chain}")
        b = self._bindings[name]
        if b.instance is not None and not b.singleton:
            return b.instance
        if b.instance is not None:
            return b.instance
        if b.singleton and b.has_cached:
            return b.cached
        self._resolving.append(name)
        try:
            assert b.factory is not None
            obj = b.factory(self) if _takes_container(b.factory) else b.factory()
        finally:
            self._resolving.pop()
        if b.singleton:
            b.cached = obj
            b.has_cached = True
        return obj


def _takes_container(fn: Callable[..., Any]) -> bool:
    try:
        import inspect
        return len(inspect.signature(fn).parameters) >= 1
    except Exception:  # noqa: BLE001
        return False
