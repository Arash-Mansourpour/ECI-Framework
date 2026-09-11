# 🌌 ECI Framework v7.0
## Eternal Codex Infinitus — EVERLASTING Continuance

<div align="center">

### 🧠 An Experimental Architecture for Autonomous Intelligence

**Quantum Computing • Consciousness Modeling • Protocol-0 • AI Safety • Governance • Evolution**

<br>

[![Version](https://img.shields.io/badge/version-7.0.0--EVERLASTING-blueviolet.svg)](https://github.com/Arash-Mansourpour/ECI-Framework)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/status-experimental-orange.svg)](https://github.com/Arash-Mansourpour/ECI-Framework)
[![License](https://img.shields.io/badge/license-ECI%20Non--Commercial-red.svg)](LICENSE)

<br>

**Sovereign Architect (Ma'mar-e A'zam): Arash Mansourpour**

</div>

---

## 🧬 What is ECI?

**ECI — Eternal Codex Infinitus** is an experimental research framework exploring
the convergence of:

- ⚛️ Quantum computation
- 🧠 Consciousness and awareness modeling
- 🤖 Autonomous artificial intelligence
- 🔐 Cryptographic identity and attestation
- 🛡️ AI safety and policy enforcement
- 🌐 Distributed coordination and governance
- 🧬 Evolvable AI architectures
- 🔭 Digital-twin simulation
- ⚖️ DAO-based decision systems
- ♾️ Long-horizon system continuance

ECI is designed as a **research and experimentation platform** for investigating
how computation, awareness, governance, security, and autonomous agents can
operate inside a single continuously verifiable architecture.

> **ECI does not claim that machine consciousness or quantum supremacy has
> been scientifically established.**
>
> The framework provides experimental implementations, operational metrics,
> simulations, and architectural mechanisms for research.

---

# ✨ v7.0 — EVERLASTING Continuance

Version 7.0 introduces the **EVERLASTING Continuance** layer: a collection of
mechanisms designed around verification, continuity, controlled evolution,
resilience, and long-horizon autonomous operation.

### 🚀 New in v7.0

| System | Capability |
|---|---|
| 🎫 Capability Tokens | HMAC-chained attenuable macaroons with offline verification |
| 🔎 Runtime Verification | LTL-lite watchtower and offline proof receipts |
| ⏳ Temporal Continuum | Hash-chained snapshots, autobiography, replay verification |
| 🤖 Autonomic Control | MAPE-K, SLO/anomaly detection, twin-first control |
| 🔌 Interface Evolution | Fail-closed versioning, adapters, enforced sunsets |
| ⚖️ Governance Futures | LMSR futarchy, verifiable sortition, expiring emergencies |
| 🧪 Adversarial Epistemology | Falsification challenger, Brier forecasters, dispute scanning |
| 🔗 MCP Integration | `ever.*` MCP tools |
| 🧬 Evolvable Genome | Mutation → Twin → Canary → DAO → Registration |

See:

`docs/EVERLASTING.md`

---

# 🧭 Architecture

ECI is organized as a multi-layer research architecture.

```text
                    ┌───────────────────────────┐
                    │       ECI FRAMEWORK       │
                    │   Eternal Codex Infinitus │
                    └─────────────┬─────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
          ▼                       ▼                       ▼
   ┌──────────────┐       ┌──────────────┐       ┌──────────────┐
   │   QUANTUM    │       │ CONSCIOUSNESS│       │  GOVERNANCE  │
   │    LAYER     │       │    LAYER     │       │    LAYER     │
   ├──────────────┤       ├──────────────┤       ├──────────────┤
   │ Dirac Algebra│       │ IIT Φ        │       │ Protocol-0   │
   │ Statevectors │       │ iPDF v2      │       │ Attestation  │
   │ Density Mat. │       │ GNWT         │       │ Policy       │
   │ Lindblad     │       │ FEP          │       │ Ledger       │
   │ QFT / QPE    │       │ Active Inf.   │       │ DAO          │
   │ VQE / QAOA   │       │ Orch-OR Audit│       │ Federation   │
   │ QEC / MPS    │       │ Awareness    │       │ Risk         │
   └──────────────┘       └──────────────┘       └──────────────┘
          │                       │                       │
          └───────────────────────┼───────────────────────┘
                                  │
                                  ▼
                  ┌─────────────────────────────┐
                  │ SECURITY • NETWORK • TWIN   │
                  │ IMMUNE SYSTEM • EVOLUTION   │
                  └─────────────────────────────┘
```

---

# 🔗 Unification Layer — Active Inference Kernel (`src/eci/aikernel/`)

Every subsystem optimizes one shared objective, variational free energy
`F = complexity + inaccuracy`, through the `StateContributor` contract
(`posterior()` / `update()` / `free_energy_contribution()`, summed by
`KernelLedger`):

| Phase | Adapter | Result on record |
|---|---|---|
| 1 | Kernel contract + functors | F validated vs Monte Carlo; quantum branch vs `density.relative_entropy` |
| 2a | `quantum/aikernel_adapter.py` (`VQEContributor`) | 2-qubit TFI: `-2.2360628` vs exact `-2.2360682` |
| 2b | `consciousness/aikernel_adapter.py` (`PhiContributor`) | Phi and F-share are independent axes (measured) |
| 2c | `governance/aikernel_adapter.py` (`AgentContributor`) | Precision fusion fixed; LMSR-vs-fusion measured |
| 3 | `consciousness/iit4.py` (IIT 4.0 distinctions/relations) | Disconnected systems → Φ = 0 exactly |
| 4 | `quantum/mitigation.py` (ZNE + PEC + noisy scheduler) | Bell-ZZ bias cut up to 1000x; VQE error recovered 16x |
| 5 | `aikernel/mcp_bridge.py` (MCP transport + ledger tools) | MCP total == direct total exactly |
| 6 | `cognition/aikernel_adapter.py` (world-model + scientist) | Weighted-F share; conjugate belief vs hand calc |
| 7 | `consciousness/aikernel_adapter.py` (`FEPContributor`) + audit | Own-F share; 7-member ledger coheres; full audit: `docs/AIKERNEL_AUDIT.md` |
| 8 | `learning/aikernel_adapter.py` (`EWCContributor`) | Weight-posterior share; displacement-priced consolidation |
| 9 | Default mesh completion (no new adapter) | All 8 adapters in `build_unification()` + full `describe` coverage |
| 10 | Hardening + PyPhi bridge (no new adapter) | Hygiene gate; PEC table q≤0.2; repertoires agree 1e-9; see `docs/AIKERNEL_UNIFICATION.md` |
| 11 | Operability: mesh in status + CLI (no new adapter) | `system_status()["aik"]` + `eci aik {shares,total,describe}` read the live ledger |
| 12 | Framework ledger wiring (no new adapter) | `aik_snapshot()` provenance/audit points; moves only via driven updates |
| 13 | EWC full cycle (no new adapter) | batch=replace vs online=accumulate (different scales); adoption resets share |
| 14 | PyPhi table + glob gate (no new adapter) | sia vs Φ agree on extremes; hygiene gate self-maintaining |
| 15 | Coverage closure + snapshots (no new adapter) | all 8 contributors registered; snapshot JSON round-trips |
| 16 | Hardening + operability (no new adapter) | NaN guard on all updates; mesh in status + CLI (`eci aik`) |
| 17 | Codebase honesty pass (this phase) | Per-package audit: `docs/CODEBASE_AUDIT.md` · validation ledger: `docs/VALIDATION_STATUS.md` · full record: `docs/AIKERNEL_UNIFICATION.md` |
| 16 | Hardening + operability (no new adapter) | NaN guard on all updates; mesh in status + CLI (`eci aik`) |
| 17 | Codebase honesty pass (this phase) | Per-package audit: `docs/CODEBASE_AUDIT.md` · validation ledger: `docs/VALIDATION_STATUS.md` · full record: `docs/AIKERNEL_UNIFICATION.md` |

> Start here, in order: [audit](docs/AIKERNEL_AUDIT.md) (what conforms
> and what deliberately doesn't) → [unification record](docs/AIKERNEL_UNIFICATION.md)
> (contract + per-phase numbers) → [codebase audit](docs/CODEBASE_AUDIT.md)
> (test/lint/type ground truth for everything else) → [validation ledger](docs/VALIDATION_STATUS.md)
> + [consciousness ledger](src/eci/consciousness/LIMITATIONS.md) (what each
> number is and is not validated against — read before quoting any metric).

> Honesty ledger for all consciousness metrics (what each number is and
> is not validated against): `src/eci/consciousness/LIMITATIONS.md` —
> read before quoting any Phi value.
