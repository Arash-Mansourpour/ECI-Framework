"""Autonomous agent runtime facade."""

from eci.agents.loop import AgentLoop, AgentState, demo_brain
from eci.agents.memory import EpisodicMemory, VectorMemory
from eci.agents.tools import ToolBudgetExceeded, ToolDenied, ToolRegistry, ToolSpec

__all__ = ["ToolRegistry", "ToolSpec", "ToolDenied", "ToolBudgetExceeded",
           "EpisodicMemory", "VectorMemory", "AgentLoop", "AgentState", "demo_brain", "Agents"]


class Agents:
    name = "agents"

    def __init__(self, authz=None, economy=None, tenancy=None,
                 provenance=None, audit=None, bus=None, precog=None) -> None:
        self.tools = ToolRegistry()
        self.memory = EpisodicMemory()
        self.vectors = VectorMemory()
        self.loop = AgentLoop(tools=self.tools, authz=authz, economy=economy,
                              tenancy=tenancy, provenance=provenance,
                              audit=audit, bus=bus, precog=precog)
        # default safe tools
        self.tools.register("echo", lambda args, ctx: {"echo": args.get("text", "")},
                            params={"text": "str"}, cost=1.0, description="echo back text")
        self.tools.register("add", lambda args, ctx: {"sum": args["a"] + args["b"]},
                            params={"a": "float", "b": "float"}, cost=2.0, description="a+b")

    def start(self) -> None: ...
    def stop(self) -> None: ...
    def health(self) -> dict:
        return {"ok": True, "tools": self.tools.health(), "memory": len(self.memory)}
