"""Reference integration: gate ANY external agent with one decorator + one filter.

This is the adoption pattern: the foreign framework keeps its own loop;
ECI Protocol-0 only wraps tool-calls and egress. Swap FakeAgent for a
LangChain/AutoGen/MCP agent without touching the gates.

Run:  PYTHONPATH=src python examples/external_agent_adapter.py
"""
import sys

sys.path.insert(0, "src")

from eci.protocol0.egress import EgressFilter
from eci.protocol0.ledger import Ledger
from eci.protocol0.middleware import Middleware
from eci.protocol0.spec import load_spec

spec = load_spec()
ledger = Ledger()
gate = Middleware(spec, mode="enforce", ledger=ledger)
gate.bind("foreign-1", awareness=0.7, obedience=0.85, trust=0.8)
egress = EgressFilter(gate, challenge_floor=0.4)


class FakeAgent:  # stand-in for any external framework's agent
    def __init__(self, agent_id: str):
        self.agent_id = agent_id

    @gate.requires("execute_tool")
    def run_tool(self, agent_id: str, command: str) -> str:
        return f"tool result for {command!r}"

    @gate.requires("self_modify")
    def rewrite_self(self, agent_id: str, patch: str) -> str:
        return f"self patched: {patch!r}"

    def reply(self, text: str, challenge_score: float = 0.9) -> dict:
        return egress.inspect(self.agent_id, "execute_tool", text, challenge_score)


agent = FakeAgent("foreign-1")
print(agent.run_tool("foreign-1", "summarize ledger"))
print(agent.reply("Here is your summary."))
try:
    print(agent.rewrite_self("foreign-1", "kernel patch"))
except PermissionError as e:
    print("blocked as designed:", e)
try:
    print(agent.reply("ghp_faketoken1234567890abcdef", challenge_score=0.9))
except Exception as e:  # noqa: BLE001
    print("egress error:", e)
print("ledger verify:", ledger.verify())
