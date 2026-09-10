"""Orchestration facade."""

from eci.orchestration.dag import DAG, TaskNode, WorkflowRun
from eci.orchestration.scheduler import Job, Scheduler

__all__ = ["DAG", "TaskNode", "WorkflowRun", "Job", "Scheduler", "Orchestration"]


class Orchestration:
    name = "orchestration"

    def __init__(self, bus=None) -> None:
        self.scheduler = Scheduler(bus=bus)

    def dag(self, name: str = "dag") -> DAG:
        return DAG(name)

    def start(self) -> None: ...
    def stop(self) -> None: ...
    def health(self) -> dict:
        return {"ok": True, "scheduler": self.scheduler.health()}
