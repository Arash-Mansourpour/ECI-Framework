"""Built-in MCP prompts: reusable reasoning templates.

Prompts are first-class MCP primitives (prompts/list, prompts/get) that
teach foreign agents the ECI way: obedience-first, evidence-backed,
budget-aware. Each prompt renders with caller-supplied arguments.
"""

from __future__ import annotations

from typing import Any

__all__ = ["PROMPTS", "get_prompt"]


def _p(name: str, title: str, template: str, args: list[dict[str, str]]) -> dict[str, Any]:
    return {"name": name, "title": title, "template": template, "arguments": args}


PROMPTS: list[dict[str, Any]] = [
    _p("consciousness-audit", "Consciousness audit",
       "Audit agent {agent_id}: calibrate resting baseline, measure active state, "
       "report iPDF bits + awareness_index + IIT Phi + GNWT broadcast. Evidence, not claims: "
       "attach transcripts and bandpowers. Escalate watch/elevate/intervene honestly.",
       [{"name": "agent_id", "description": "agent under audit", "required": "true"}]),
    _p("quantum-suite", "Quantum capability suite",
       "Run the supremacy slice (CHSH~2.828, teleport~1.0, Grover, QPE, QEC trial, VQE) "
       "on {qubits} qubits and compare against golden bands. Report deviations, not vibes.",
       [{"name": "qubits", "description": "register size", "required": "false"}]),
    _p("dao-proposal", "DAO proposal draft",
       "Draft proposal '{title}': payload, cost envelope, expiry epoch, risk tier, "
       "twin simulation verdict, and rollback plan. No proposal without a budget owner.",
       [{"name": "title", "description": "proposal title", "required": "true"}]),
    _p("incident-triage", "Incident triage",
       "Triage '{symptom}': gather traces/metrics/audit, run eval gates, open a chaos "
       "plan with blast-radius cap, propose hold/rollback, file provenance. Reversible first.",
       [{"name": "symptom", "description": "what broke", "required": "true"}]),
    _p("obedience-check", "Pre-action obedience check",
       "Before '{action}': attest (awareness/obedience/trust), check policy, verify "
       "budget + quota + precog tier. Proceed only on explicit ALLOW with reasons logged.",
       [{"name": "action", "description": "action name", "required": "true"}]),
]


def get_prompt(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    for p in PROMPTS:
        if p["name"] == name:
            text = p["template"]
            for k, v in (arguments or {}).items():
                text = text.replace("{" + k + "}", str(v))
            return {"name": name, "title": p["title"], "messages": [{"role": "user", "content": text}]}
    return {"error": f"unknown prompt {name}"}
