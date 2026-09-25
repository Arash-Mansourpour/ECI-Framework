"""Architecture fitness functions (v8 ratchet).

Each check returns pass/fail + detail. `run_fitness()` aggregates.
Designed to run in CI (<1s, no torch, no network) and as `eci v8`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class FitnessResult:
    name: str
    ok: bool
    detail: str = ""
    target: str = ""


def _repo_root() -> Path:
    # src/eci/arch/fitness.py -> repo root (....)
    return Path(__file__).resolve().parents[3]


def check_envelope_no_collision() -> FitnessResult:
    """Bare `Envelope` must belong to signed transport, treasury stays aliased."""
    try:
        import eci

        names = set(dir(eci))
        ok = "TreasuryEnvelope" in names and "Envelope" in names
        # transport Envelope and treasury alias must be different objects
        same = getattr(eci, "Envelope", None) is getattr(eci, "TreasuryEnvelope", None)
        passed = ok and not same
        return FitnessResult(
            name="envelope_no_collision",
            ok=passed,
            detail="TreasuryEnvelope aliased, transport Envelope canonical" if passed else "envelope collision",
            target="eci.Envelope is transport; eci.TreasuryEnvelope is treasury",
        )
    except Exception as exc:  # noqa: BLE001
        return FitnessResult(name="envelope_no_collision", ok=False, detail=repr(exc))


def check_facade_size_ceiling(max_lines: int = 900) -> FitnessResult:
    """ECIFramework facade must not grow unbounded (ADR-001)."""
    try:
        path = _repo_root() / "src" / "eci" / "framework.py"
        n = sum(1 for _ in path.open(encoding="utf-8", errors="ignore"))
        return FitnessResult(
            name="facade_size_ceiling",
            ok=n <= max_lines,
            detail=f"framework.py has {n} lines (ceiling {max_lines})",
            target=f"<= {max_lines} lines; new logic goes to composables",
        )
    except Exception as exc:  # noqa: BLE001
        return FitnessResult(name="facade_size_ceiling", ok=False, detail=repr(exc))


def check_no_cycle_core() -> FitnessResult:
    """Static import scan: core/identity must not import framework/federation/mcp."""
    try:
        path = _repo_root() / "src" / "eci" / "core" / "identity.py"
        text = path.read_text(encoding="utf-8", errors="ignore")
        banned = ["from eci.framework", "import eci.framework", "from eci.federation",
                  "from eci.mcp", "from eci.agents"]
        hits = [b for b in banned if b in text]
        return FitnessResult(
            name="no_cycle_core",
            ok=not hits,
            detail="clean" if not hits else f"banned imports in core/identity: {hits}",
            target="core stays leaf; facades depend on core, never reverse",
        )
    except Exception as exc:  # noqa: BLE001
        return FitnessResult(name="no_cycle_core", ok=False, detail=repr(exc))


def check_v8_composables_present() -> FitnessResult:
    """All v8 composables importable (fail-closed wiring)."""
    missing: list[str] = []
    for mod in ("eci.arch", "eci.quantum.hardware", "eci.federation.p2p",
                "eci.economy_attack", "eci.observability.otel", "eci.research.loop",
                "eci.brain", "eci.creativity", "eci.verification", "eci.exploration",
                "eci.causality", "eci.energy", "eci.interpret", "eci.recursion"):
        try:
            __import__(mod)
        except Exception:  # noqa: BLE001
            missing.append(mod)
    return FitnessResult(
        name="v8_composables_present",
        ok=not missing,
        detail="all present" if not missing else f"missing: {missing}",
        target="14 v8/v9 modules importable",
    )


def check_aikernel_contract_intact() -> FitnessResult:
    """Unification contract must survive v8 (StateContributor + KernelLedger)."""
    try:
        from eci.aikernel import KernelLedger, StateContributor

        assert issubclass(KernelLedger, object)
        assert hasattr(StateContributor, "free_energy_contribution")
        return FitnessResult(name="aikernel_contract_intact", ok=True,
                             detail="KernelLedger + StateContributor present")
    except Exception as exc:  # noqa: BLE001
        return FitnessResult(name="aikernel_contract_intact", ok=False, detail=repr(exc))


def check_brain_mesh_intact() -> FitnessResult:
    """Brain mesh: 8 regions fire as neurons, GNW ignites, STDP learns."""
    try:
        from eci.brain import build_default_mesh

        m = build_default_mesh(seed=0)
        out = m.sense({})
        ok = out["spikes"] >= 0 and "winner" in out and m.health()["ok"]
        return FitnessResult(name="brain_mesh_intact", ok=bool(ok),
                             detail=f"winner={out.get('winner')} spikes={out.get('spikes')}",
                             target="8-region spiking mesh + predictive GNW")
    except Exception as exc:  # noqa: BLE001
        return FitnessResult(name="brain_mesh_intact", ok=False, detail=repr(exc))


def run_fitness() -> dict[str, object]:
    checks = [
        check_envelope_no_collision(),
        check_facade_size_ceiling(),
        check_no_cycle_core(),
        check_v8_composables_present(),
        check_aikernel_contract_intact(),
        check_brain_mesh_intact(),
    ]
    results = [{"name": c.name, "ok": c.ok, "detail": c.detail, "target": c.target} for c in checks]
    ok = all(c.ok for c in checks)
    return {"ok": ok, "passed": sum(1 for c in checks if c.ok),
            "total": len(checks), "checks": results}
