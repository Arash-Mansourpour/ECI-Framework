"""Phase 5 — StateContributor adapters as MCP tools, one shared schema.

Every conformant adapter exposes the SAME three tools under
``aik.{namespace}.{posterior,update,free_energy}``:

  posterior         {} -> GenerativeState dict (mu/cov/n_qubits/paulis/meta/rho_*)
  update            {observation: [...], options: {...}} -> GenerativeState dict
  free_energy       {} -> {free_energy: float}

plus ``aik.ledger.shares`` / ``aik.ledger.total`` for the whole
unification state. Schemas are built once from GenerativeState.to_dict()
keys — not per-subsystem ad hoc.

Wire format for rho (documented tradeoff decision): row-major
``rho_real``/``rho_imag`` nested lists, always present as keys (null when
Gaussian-only), reconstructed exactly by ``GenerativeState.from_dict``
(float32 values survive the float64 JSON round-trip losslessly). O(4^n)
floats: exact and cheap at the small-n this interface carries; large
registers should travel as Gaussian coords (``include_rho=False``).

Deliberately KEPT direct imports (Phase 5 §4 bypass list — file:line:reason):
- aikernel/*:31-32,36-37 (quantum adapter), :56-57 (consciousness adapter),
  :45-47 (governance adapter): the SUBSTRATE itself (contract types + F math).
  Routing substrate math through MCP serialization per call would add
  JSON churn to every optimizer step with zero semantic gain.
- governance/aikernel_adapter.py:47 (gaussian_complexity from the
  consciousness adapter): pure-function reuse; duplicating the closed form
  risks divergence between two copies of one equation.
- consciousness/iit.py:28 (eci.quantum.density): pure entropy math on the
  hot Phi path; per-call MCP round-trips would dominate compute.
- framework.py (composition root wiring ECIFramework): owns instances by
  design; MCP is the *external/cross-agent* interface, not a ban on
  in-process composition.
- mcp_bridge below imports all four adapters + TFI helper: interface
  construction (registry wiring), runs once at fabric build, not per call.
"""

from __future__ import annotations

import inspect
from typing import Any

__all__ = ["STATE_SCHEMA", "EMPTY_SCHEMA", "FREE_ENERGY_SCHEMA",
           "register_contributor", "register_ledger", "describe_ledger",
           "build_unification", "ADAPTER_NAMESPACES"]

STATE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "observation": {
            "type": "array",
            "description": "nested list of floats: flat vector or [time, dim] window",
        },
        "options": {
            "type": "object",
            "description": "contributor-specific flags (e.g. recompute_phi)",
            "additionalProperties": True,
        },
    },
    "additionalProperties": True,
}

EMPTY_SCHEMA: dict[str, Any] = {"type": "object", "properties": {}}

FREE_ENERGY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"free_energy": {"type": "number"}},
}

ADAPTER_NAMESPACES = ("quantum", "phi", "agent", "noisy")


def _coerce_observation(raw: Any) -> Any:
    import torch
    return torch.as_tensor(raw, dtype=torch.float32)


def _filter_options(contributor: Any, options: dict[str, Any]) -> dict[str, Any]:
    try:
        params = inspect.signature(contributor.update).parameters
    except (TypeError, ValueError):
        return {}
    return {k: v for k, v in options.items() if k in params}


def register_contributor(registry: Any, namespace: str, contributor: Any,
                         version: str = "7.0.0") -> list[str]:
    """Expose posterior/update/free_energy with the shared schema."""
    from eci.mcp.registry import McpTool
    base = f"aik.{namespace}"

    def _posterior(args: dict[str, Any], ctx: dict[str, Any]) -> Any:
        return contributor.posterior().to_dict()

    def _update(args: dict[str, Any], ctx: dict[str, Any]) -> Any:
        if "observation" not in args:
            raise ValueError("update requires 'observation'")
        obs = _coerce_observation(args["observation"])
        opts = _filter_options(contributor, dict(args.get("options", {})))
        return contributor.update(obs, **opts).to_dict()

    def _free(args: dict[str, Any], ctx: dict[str, Any]) -> Any:
        import torch
        val = contributor.free_energy_contribution()
        if torch.is_tensor(val):
            val = val.detach()
        return {"free_energy": float(val)}

    tools = [
        McpTool(f"{base}.posterior", f"{namespace} posterior as GenerativeState",
                _posterior, dict(EMPTY_SCHEMA), version=version,
                mutating=False, idempotent=True),
        McpTool(f"{base}.update", f"{namespace} assimilate observation",
                _update, dict(STATE_SCHEMA), version=version,
                mutating=True, idempotent=False),
        McpTool(f"{base}.free_energy", f"{namespace} F-share",
                _free, dict(EMPTY_SCHEMA), version=version,
                mutating=False, idempotent=True),
    ]
    for t in tools:
        registry.register(t, overwrite=True)
    return [t.name for t in tools]


def register_ledger(registry: Any, ledger: Any,
                    namespace: str = "aik.ledger") -> list[str]:
    """Expose shares()/total_free_energy() for the whole unification state."""
    from eci.mcp.registry import McpTool

    def _shares(args: dict[str, Any], ctx: dict[str, Any]) -> Any:
        return {"shares": {k: float(v) for k, v in ledger.shares().items()}}

    def _total(args: dict[str, Any], ctx: dict[str, Any]) -> Any:
        import torch
        tot = ledger.total_free_energy()
        if torch.is_tensor(tot):
            tot = tot.detach()
        return {"total_free_energy": float(tot),
                "members": sorted(ledger.members())}

    def _describe(args: dict[str, Any], ctx: dict[str, Any]) -> Any:
        """Per-member share + audit category + what the share measures.

        Categories/notes paraphrased (short) from each adapter's framing
        docstring — the docstring stays the source of truth. Members whose
        class isn't listed report 'unlisted' rather than a guess.
        """
        return describe_ledger(ledger)

    tools = [
        McpTool(f"{namespace}.shares", "per-subsystem F shares",
                _shares, dict(EMPTY_SCHEMA), mutating=False, idempotent=True),
        McpTool(f"{namespace}.total", "unified total free energy",
                _total, dict(EMPTY_SCHEMA), mutating=False, idempotent=True),
        McpTool(f"{namespace}.describe", "F-share meanings + audit categories",
                _describe, dict(EMPTY_SCHEMA), mutating=False, idempotent=True),
    ]
    for t in tools:
        registry.register(t, overwrite=True)
    return [t.name for t in tools]


def describe_ledger(ledger: Any) -> dict[str, Any]:
    """Shared describe logic for the MCP tool AND framework status/CLI.

    One implementation, three callers (tool handler, system_status, CLI) —
    so the meanings can never diverge between transports.
    """
    notes = _adapter_notes()
    out: dict[str, Any] = {}
    for name, member in ledger.members().items():
        hit = notes.get(type(member))
        share = ledger.shares().get(name)
        out[name] = {"share": float(share) if share is not None else None,
                     "category": hit[0] if hit else "unlisted",
                     "note": hit[1] if hit else ""}
    return {"members": out}


def _adapter_notes() -> dict[Any, Any]:
    from eci.cognition.aikernel_adapter import ScientistContributor, WorldModelContributor
    from eci.consciousness.aikernel_adapter import FEPContributor, PhiContributor
    from eci.governance.aikernel_adapter import AgentContributor
    from eci.learning.aikernel_adapter import EWCContributor
    from eci.quantum.aikernel_adapter import VQEContributor
    from eci.quantum.mitigation import NoisyVQEContributor
    return {
        VQEContributor: ("good-fit",
                         "VQE loss is F exactly (energy-target likelihood)"),
        NoisyVQEContributor: ("good-fit",
                              "same F under ideal/noisy/ZNE routing; entropy term unmitigated"),
        PhiContributor: ("adaptable",
                         "share is complexity KL, NOT Phi (independent axes)"),
        AgentContributor: ("good-fit",
                           "conjugate posterior; consensus is shared-prior fusion"),
        WorldModelContributor: ("good-fit",
                                "native loss is weighted-F variant (0.1KL+0.5ens), parts reported"),
        ScientistContributor: ("good-fit",
                               "KL of conjugate belief vs N(0,1) prior"),
        FEPContributor: ("good-fit",
                         "its own F; Laplace posterior from MAP + fixed precisions"),
        EWCContributor: ("good-fit",
                         "EWC penalty as weight-posterior share; Fisher refreshed via consolidate()"),
    }


def build_unification(registry: Any = None) -> dict[str, Any]:
    """Default 8-member unification mesh (Phase 9: complete).

    quantum + noisy (quantum/) · phi + fep (consciousness/) · agent
    (governance/) · world + sci (cognition/) · ewc (learning/).
    Cheap to construct (no optimizer steps run here); the E2E test drives
    observations through afterwards. Returns ledger + contributors +
    registered tool names.
    """
    from eci.aikernel.state_contract import KernelLedger
    from eci.cognition.aikernel_adapter import ScientistContributor, WorldModelContributor
    from eci.cognition.world_model import WorldModelConfig
    from eci.consciousness.aikernel_adapter import FEPContributor, PhiContributor
    from eci.governance.aikernel_adapter import AgentContributor
    from eci.learning.aikernel_adapter import EWCContributor
    from eci.learning.continual import ElasticWeightConsolidation
    from eci.mcp.registry import McpRegistry
    from eci.quantum.aikernel_adapter import VQEContributor, tfi_hamiltonian
    from eci.quantum.mitigation import NoisyVQEContributor

    reg = registry or McpRegistry()
    ham = tfi_hamiltonian(2)
    import torch.nn as _nn
    contributors = {
        "quantum": VQEContributor(ham, 2, e_target=-3.2),
        "phi": PhiContributor(dim=2),
        "agent": AgentContributor("aik-agent-0", dim=1),
        "noisy": NoisyVQEContributor(ham, 2, e_target=-3.2, mode="noisy", noise_q=0.02),
        "world": WorldModelContributor(WorldModelConfig(obs_dim=4, act_dim=2,
                                                        hidden=16, latent=4)),
        "sci": ScientistContributor("aik-default", "y = a*x + b", 2),
        "fep": FEPContributor(2, 2),
        "ewc": EWCContributor(ElasticWeightConsolidation(_nn.Linear(2, 2))),
    }
    ledger = KernelLedger()
    for name, member in contributors.items():
        ledger.register(name, member)
    names: list[str] = []
    for ns, member in contributors.items():
        names += register_contributor(reg, ns, member)
    names += register_ledger(reg, ledger)
    return {"ledger": ledger, "contributors": contributors,
            "registry": reg, "tools": names}
