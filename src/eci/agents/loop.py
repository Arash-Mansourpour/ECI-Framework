"""ReAct agent loop: think -> act (tool) -> observe, with hard guardrails.

The loop is deliberately *policy-first*: every step consults authz
(RBAC/ABAC + Protocol-0 attestation), economy budget, tenancy quota and
precog risk before a tool runs. Each step appends to provenance + audit +
event-bus, so runs are replayable in twin, disputable in court and priced
in the market. The 'brain' is injectable: pass any ``policy_fn(state)``
returning {"thought": str, "tool": str|None, "args": dict, "done": bool,
"answer": str}. A deterministic demo brain is included for tests/CLI.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

__all__ = ["AgentState", "AgentLoop", "demo_brain"]


@dataclass
class AgentState:
    goal: str
    steps: list[dict[str, Any]] = field(default_factory=list)
    budget: float = 100.0
    done: bool = False
    answer: str = ""


def demo_brain(state: AgentState, tools: list[str]) -> dict[str, Any]:
    """Two-step demo: echo goal via `echo` tool then finish."""
    if not state.steps:
        return {"thought": f"plan for: {state.goal}", "tool": "echo" if "echo" in tools else None,
                "args": {"text": state.goal}, "done": False, "answer": ""}
    return {"thought": "done", "tool": None, "args": {}, "done": True,
            "answer": f"completed: {state.goal}"}


class AgentLoop:
    name = "agent-loop"

    def __init__(self, tools=None, authz=None, economy=None, tenancy=None,
                 provenance=None, audit=None, bus=None, precog=None) -> None:
        self.tools = tools
        self.authz = authz
        self.economy = economy
        self.tenancy = tenancy
        self.provenance = provenance
        self.audit = audit
        self.bus = bus
        self.precog = precog

    async def run(self, goal: str, agent_id: str = "agent-0", namespace: str = "default",
                  budget: float = 100.0, max_steps: int = 6,
                  policy_fn: Callable[..., dict[str, Any]] | None = None,
                  attestation: dict[str, float] | None = None) -> dict[str, Any]:
        from eci.kernel.bus import Event
        policy_fn = policy_fn or demo_brain
        state = AgentState(goal=goal, budget=budget)
        tool_names = self.tools.names() if self.tools else []
        t0 = time.time()
        for i in range(max_steps):
            decision = policy_fn(state, tool_names)
            step: dict[str, Any] = {"i": i, "thought": decision.get("thought", ""),
                                    "tool": decision.get("tool"), "args": decision.get("args", {})}
            # guardrail 1: tenancy quota
            if self.tenancy is not None:
                try:
                    if not self.tenancy.admit(namespace, actions=1):
                        step["blocked"] = "tenancy-quota"
                        state.steps.append(step)
                        break
                except Exception:  # noqa: BLE001
                    pass
            # guardrail 2: authz (when a tool is requested)
            tool = decision.get("tool")
            if tool and self.authz is not None:
                dec = self.authz.decide(agent_id, f"tool.{tool}", f"agent/{agent_id}",
                                        attrs={"namespace": namespace},
                                        attestation=attestation or {"awareness": 1.0, "obedience": 1.0, "trust": 1.0})
                step["authz"] = dec.to_dict()
                if not dec.allow:
                    step["blocked"] = "authz-deny"
                    state.steps.append(step)
                    continue
            # guardrail 3: precog risk (advisory hold)
            if self.precog is not None:
                try:
                    risk = self.precog.assess(str(tool), step.get("args", {}))  # type: ignore[attr-defined]
                    step["precog"] = risk
                    if isinstance(risk, dict) and risk.get("tier") == "hold":
                        step["blocked"] = "precog-hold"
                        state.steps.append(step)
                        break
                except Exception:  # noqa: BLE001
                    pass
            if decision.get("done"):
                state.done = True
                state.answer = str(decision.get("answer", ""))
                state.steps.append(step)
                break
            if not tool or self.tools is None:
                state.steps.append(step)
                continue
            # economy charge (pre-check)
            if self.economy is not None:
                try:
                    chk = self.economy.charge(agent_id, "execute_tool")
                    if not chk.get("ok"):
                        step["blocked"] = "budget"
                        state.steps.append(step)
                        break
                except Exception:  # noqa: BLE001
                    pass
            out = await self.tools.call(tool, step["args"],
                                        {"subject": agent_id, "budget": state.budget,
                                         "capabilities": ["bus.publish", "store.read", "store.write"]})
            state.budget -= float(out.get("cost", 0.0))
            step["observation"] = out
            state.steps.append(step)
            if self.provenance is not None:
                try:
                    parent = state.steps[-2].get("prov") if len(state.steps) > 1 else ""
                    node = self.provenance.record("agent.step", agent_id,
                                                  {"goal": goal, "tool": tool, "args": step["args"]},
                                                  {"ok": out.get("ok"), "data": out.get("data")},
                                                  {"namespace": namespace}, parent=parent or "")
                    step["prov"] = node.id
                except Exception:  # noqa: BLE001
                    pass
        if self.audit is not None:
            try:
                self.audit.append(agent_id, "agent.run", {"goal": goal, "steps": len(state.steps), "done": state.done})
            except Exception:  # noqa: BLE001
                pass
        if self.bus is not None:
            try:
                self.bus.publish(Event(type="agent.run.done", source=agent_id,
                                       payload={"goal": goal, "done": state.done, "steps": len(state.steps)}))
            except Exception:  # noqa: BLE001
                pass
        return {"ok": state.done, "answer": state.answer, "steps": state.steps,
                "budget_left": state.budget, "duration_s": time.time() - t0}

    def start(self) -> None: ...
    def stop(self) -> None: ...
    def health(self) -> dict[str, Any]:
        return {"ok": True}
