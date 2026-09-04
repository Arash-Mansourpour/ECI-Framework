"""Component registry - a lightweight, typed plugin system.

Components (simulators, analyzers, consensus engines, ...) register under a
name + protocol tag; consumers resolve them without hard imports, which
keeps the three-layer architecture decoupled.
"""

from __future__ import annotations

from typing import Callable, Dict, Generic, Iterable, List, Optional, Type, TypeVar

__all__ = ["Registry", "GLOBAL_REGISTRY", "register_component"]

T = TypeVar("T")


class Registry(Generic[T]):
    """Name -> factory registry with optional protocol tagging."""

    def __init__(self, name: str = "registry") -> None:
        self.name = name
        self._factories: Dict[str, Callable[..., T]] = {}
        self._protocols: Dict[str, str] = {}

    def register(
        self,
        name: str,
        factory: Optional[Callable[..., T]] = None,
        protocol: str = "generic",
    ) -> Callable:
        """Register ``factory`` under ``name``. Usable as a decorator."""

        def _register(fn: Callable[..., T]) -> Callable[..., T]:
            if name in self._factories:
                raise KeyError(f"'{name}' already registered in {self.name}")
            self._factories[name] = fn
            self._protocols[name] = protocol
            return fn

        if factory is not None:
            return _register(factory)
        return _register

    def unregister(self, name: str) -> None:
        self._factories.pop(name, None)
        self._protocols.pop(name, None)

    def get(self, name: str) -> Callable[..., T]:
        if name not in self._factories:
            raise KeyError(
                f"'{name}' not registered in {self.name}. "
                f"Available: {sorted(self._factories)}"
            )
        return self._factories[name]

    def create(self, name: str, *args: object, **kwargs: object) -> T:
        return self.get(name)(*args, **kwargs)

    def names(self, protocol: Optional[str] = None) -> List[str]:
        if protocol is None:
            return sorted(self._factories)
        return sorted(n for n, p in self._protocols.items() if p == protocol)

    def __contains__(self, name: str) -> bool:
        return name in self._factories

    def __len__(self) -> int:
        return len(self._factories)


#: Global component registry shared by all ECI subsystems.
GLOBAL_REGISTRY: Registry[object] = Registry("eci-global")


def register_component(name: str, protocol: str = "generic") -> Callable:
    """Decorator registering a class or factory into :data:`GLOBAL_REGISTRY`."""
    return GLOBAL_REGISTRY.register(name, protocol=protocol)
