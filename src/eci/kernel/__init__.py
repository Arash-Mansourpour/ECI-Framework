"""Kernel facade: EventBus + Container + LifecycleManager in one handle."""

from eci.kernel.bus import Event, EventBus, Subscription
from eci.kernel.container import CircularDependencyError, Container
from eci.kernel.lifecycle import LifecycleManager, ServiceState

__all__ = ["Event", "EventBus", "Subscription", "Container", "CircularDependencyError", "LifecycleManager", "ServiceState", "Kernel"]


class Kernel:
    """Single ownership point for core plumbing."""

    def __init__(self, replay_capacity: int = 512) -> None:
        self.bus = EventBus(replay_capacity=replay_capacity)
        self.container = Container()
        self.lifecycle = LifecycleManager()
        # self-registration so plugins/services can discover the kernel
        self.container.register("kernel", instance=self)
        self.container.register("bus", instance=self.bus)
        self.container.register("lifecycle", instance=self.lifecycle)

    def stats(self) -> dict:
        return {"bus": self.bus.stats(), "services": self.lifecycle.health(), "bindings": self.container.names()}
