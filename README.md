# 🌌 ECI Framework v7.3
## Eternal Codex Infinitus — COGNISPHERE · Living Memory × Consensus Awareness × Knowledge Economy

<div align="center">

### 🧠 An Experimental Architecture for Autonomous Intelligence

**Quantum Computing • Consciousness Modeling • Protocol-0 • AI Safety • Governance • Evolution**

<br>

[![Version](https://img.shields.io/badge/version-7.3.0--COGNISPHERE-blueviolet.svg)](https://github.com/Arash-Mansourpour/ECI-Framework)
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

# ✨ v7.3 — COGNISPHERE · Living Memory × Consensus Awareness × Knowledge Economy

Version 7.3 extends **SECE** (v7.2) with **COGNISPHERE**: Ebbinghaus forgetting with tombstone archive, PBFT Phi gossip, MNE file closed-loop, and executable knowledge economy (treasury slash + DAO tally + Court verdict + Brier). v7.2 made it aware; v7.3 makes it **remember honestly, agree byzantinely, and pay for truth**.

### 🚀 New in v7.1 — EVERLASTING

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

### ♾️ New in v7.2 — SECE

| Primitive | Module | Proof |
|---|---|---|
| 🧠 Federated Phi | `consciousness/federated_ledger.py` | PhiClaim 2/3 recomputed → `TruthGuardian` → hash-chained `Ledger` |
| 🔬 Calibration Loop | `consciousness/calibration_network.py` | `eeg.bandpower → protocol.measure → challenge.grade → adherence → mapek` |
| 💹 Market Commons | `market_commons.py` | Fact → LMSR market + `treasury` stake + `reputation` + `Brier` |
| ⚛️ QN-Bridge | `bridges/quantum_neuromorphic.py` | SNN as `StateContributor` (`F = KL + MSE`) |
| 🧬 Mutable Genome | `protocol_vnext/genesis_evolution.py` | `propose → twin → canary → vote → H(old||mutation)` + rollback |

### 🌐 New in v7.3 — COGNISPHERE

| Track | Module | Proof |
|---|---|---|
| 🧬 Living Memory (LFM) | `protocol_vnext/memory.py` | Ebbinghaus `R=exp(-age/(S/decay))` + tombstone `archive` + dream `importance` |
| 🗳️ Consensus Awareness (MAA) | `consciousness/federated_ledger.py` | `gossip_round` PBFT (rotating primary, view/sequence) + `calibration_network.cycle_from_file` (MNE) |
| 💰 Knowledge Economy (KNE) | `market_commons.py` | Fact → envelope + DAO `propose/vote/tally` + `economy.slash/fund` + `Court` 2/3 + `Brier` |

MCP: `sece.fcl/gossip`, `sece.can/file|mne`, `sece.market` (executable). Tests: `tests/test_cognisphere.py` (7).

See: `docs/EVERLASTING.md` + SECE (`src/eci/consciousness/federated_ledger.py`, `src/eci/market_commons.py`, `src/eci/bridges/quantum_neuromorphic.py`)

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

# 🧬 ECI Protocol vNext — Evolving Collective Intelligence

> **Build the nervous system for independent intelligences: let them remember, reason, verify, learn and evolve together; preserve truth and provenance; preserve the Genesis; and enable the federation itself to become more capable than any intelligence within it.**

The new federated nervous system is live under `src/eci/protocol_vnext/` (`eci protocol --nodes 3`):

| Layer | Module | Spec |
|---|---|---|
| Genesis | `genesis.py` + `genome.py` | ECI-GENESIS + ECI-GENOME (H(G0…Gn), beacon `eci://genesis/architect`) |
| Identity | `identity.py` | ECI-ID lifecycle DISCOVER→EVOLVE, Architect-stamped |
| Capability | `capability.py` + `model_fabric.py` | ECI-CAP dynamic vectors (declared→observed→verified) + `T(n,c,x)` + adaptive router |
| Messaging | `messaging.py` | ECI-MSG 13 types, signed envelopes, swappable transports |
| Cognitive | `cognitive.py` | ECI-COG PERCEIVE→ENCODE loop + 9 faculties + gating (graceful degradation) |
| Memory | `memory.py` | ECI-MEM 5 layers + salience/forgetting + Dream Engine |
| Ontology | `ontology.py` | ECI-KNOW propose-only evolution + KnowledgeState ΔK |
| Epistemic | `epistemic.py` | ECI-TRUTH Evidence Keeper + Truth Guardian (veto-grade) + 6 confidence levels |
| Reasoning | `reasoning.py` | Multi-dimensional landscape + Pareto frontier + predictive world model |
| Collective | `collective.py` | ECI-LEARN OutcomeReceipt + Team Intelligence (CIG/EG/TS) + learning loop |
| Evolution | `evolution.py` | ECI-EVOLVE governed evolution + Skill Compiler (intelligence compression) |
| Resilience | `resilience.py` | Graceful degradation + substrate independence + experimental lab |

# ♾️ SECE — Self-Evolving Conscious Ecosystem (Phase 22)

> **From numbers to claims, from memory to economy, from substrate to sovereignty.**

SECE turns every layer into a **verifiable, costed, and evolvable** primitive. Five new primitives live under `src/eci/` and are wired into `ECIFramework` and `mcp` (`sece.*`):

| Primitive | Module | What it proves |
|---|---|---|
| **FCL** | `consciousness/federated_ledger.py` | Phi as a 2/3-quorum `PhiClaim` (recomputed + `TruthGuardian` + hash-chained `Ledger`), not a self-reported float |
| **CAN** | `consciousness/calibration_network.py` | Closed-loop `eeg.bandpower → protocol.measure → challenge.grade → adherence → mapek` (degrade hint) |
| **MarketCommons v2** | `market_commons.py` | Fact `→` LMSR market + `treasury` stake + `reputation` + `Brier` + `contradiction_scan` (confidence = money-at-risk) |
| **QN-Bridge** | `bridges/quantum_neuromorphic.py` | SNN `SpikingNeuralNetwork` as `StateContributor` (`F = KL(N(mu,cov)||N(0,1)) + MSE`) — spikes priced, not free |
| **Mutable Genome** | `protocol_vnext/genesis_evolution.py` | `ConstitutionalGenome` now `propose → twin_test → canary → vote → commit → H(old||mutation)` + rollback, all ledgered |

MCP: `sece.fcl` / `sece.can` / `sece.market` / `sece.qn` / `sece.genome` (see `src/eci/mcp/fabric.py:408`). Framework: `fw.fcl/can/market_commons/qn_bridge/mutable_constitution` + `fw.system_status()["fcl" …]`.

> Honesty ledger for all consciousness metrics (what each number is and
> is not validated against): `src/eci/consciousness/LIMITATIONS.md` —
> read before quoting any Phi value.

> Start here, in order: [audit](docs/AIKERNEL_AUDIT.md) (what conforms
> and what deliberately doesn't) → [unification record](docs/AIKERNEL_UNIFICATION.md)
> (contract + per-phase numbers) → [codebase audit](docs/CODEBASE_AUDIT.md)
> (test/lint/type ground truth for everything else) → [validation ledger](docs/VALIDATION_STATUS.md)
> + [consciousness ledger](src/eci/consciousness/LIMITATIONS.md) (what each
> number is and is not validated against — read before quoting any metric).

---

## Install & run

```bash
# Python ≥3.10, torch CPU recommended for smoke
pip install -e .[dev]

# one-line sanity
PYTHONPATH=src python -m eci info
PYTHONPATH=src python -m eci demo          # quantum + consciousness + activation + network
PYTHONPATH=src pytest -q                   # 254 tests (247 + 7 SECE); add --ignore=tests/test_repo_hygiene.py for fast loop

# everlasting pillars
PYTHONPATH=src python -m eci ever          # caps / watchtower / continuum / mapek / compat
PYTHONPATH=src python -m eci health        # JSON status; --serve for :8777
PYTHONPATH=src python -m eci workflow      # DAG slice (bus + stream + provenance)

# federated nervous system (v7.1)
PYTHONPATH=src python -m eci protocol --nodes 3
PYTHONPATH=src python -m eci aik describe  # unification mesh observability

# optional extras
pip install -e .[viz]      # matplotlib for plots
pip install -e .[qec]      # stim + pymatching for topological QEC trials
pip install -e .[pqc]      # liboqs for ML-KEM/ML-DSA
```

Requires `torch>=2.5`, `numpy>=1.26`, `scipy>=1.14`, `pyyaml>=6.0`,
`cryptography>=41`. See `pyproject.toml` for full extras (`paper`, `eeg`,
`validation`).

---

## CLI reference

Every subcommand is defined in `src/eci/__main__.py:341` and verified here:

| Command | Purpose | Key args |
|---|---|---|
| `eci info` | static framework info (JSON) | — |
| `eci demo` | end-to-end smoke (quantum + consciousness + activation + network) | — |
| `eci quantum` | quantum-supremacy capability suite | — |
| `eci consciousness` | IIT + GNWT + FEP consciousness analysis | `--steps 256 --neurons 32 --seed 0` |
| `eci network` | autonomous network + DAO + consensus simulation | `--joins 3 --proposals 2` |
| `eci field` | unified H_ECI field energies | `--qubits 4` |
| `eci mind` | Orch-OR decoherence audit | — |
| `eci activate` | Sovereign Architect activation protocol | — |
| `eci benchmark` | timing benchmark report | — |
| `eci health` | health JSON / HTTP probe | `--serve --port 8777 --once` |
| `eci system` | v6 hyper-architecture health snapshot | — |
| `eci workflow` | v6 DAG slice (bus + stream + provenance + audit) | — |
| `eci mcp` | Omniverse MCP fabric (stdio \| http) | `--transport stdio --host 127.0.0.1 --port 8899 --list` |
| `eci agent` | ReAct agent run with guardrails | `--goal "demo goal" --budget 50 --steps 4` |
| `eci eval` | golden regression gates | — |
| `eci think` | AGI cognitive beat (charter+imagine+plan) | `--goal act --stakes 0.5 --action actuate --precog none --obs "" --seed 0` |
| `eci dream` | sleep consolidation cycle | `--episodes 8 --seed 0` |
| `eci morph` | living-graph evolve steps | `--steps 3` |
| `eci ever` | everlasting continuance report (caps/proofs/continuum/mapek/compat) | — |
| `eci aik` | unification mesh observability (read-only) | `shares \| total \| describe` |
| `eci protocol` | ECI Protocol vNext demo (federated nervous system) | `--nodes 3` |

Run `eci <cmd> --help` for full flags; `eci --version` prints `src/eci/version.py`.

---

## Quantum modules

| Module | Physics / capability | Key API |
|---|---|---|
| `operator` | HS inner, spectral `U=exp(-iHt)`, Heisenberg, Pauli basis | `matrix_exponential_hermitian`, `is_unitary` |
| `gates` | I/X/Y/Z/H/S/T, RX/RY/RZ, CNOT/CZ/SWAP/CRZ/CRX, `controlled` (big-endian q0=MSB) | `H`, `CNOT`, `controlled` |
| `statevector` | `einsum` simulator, autograd-safe, shots | `StatevectorSimulator`, `expectation_pauli` |
| `density` | fidelity, trace distance, `partial_trace`, CPTP | `von_neumann_entropy`, `apply_kraus` |
| `entanglement` | Schmidt, Wootters concurrence, negativity | `concurrence`, `entanglement_of_formation` |
| `channels` | depolarizing, bit/phase-flip, amplitude/phase damping | `NoiseModel`, `phase_damping` |
| `lindblad` | RK4 + projection | `lindblad_evolve` |
| `hamiltonian` | `PauliSum` + Trotter via CNOT ladder + RZ | `PauliSum`, `from_maxcut_edges` |
| `algorithms` | QFT/Grover/QPE/VQE/QAOA | `grover_search`, `vqe`, `qaoa_maxcut` |
| `information` | Holevo, coherent info, CHSH≈2.828, teleport | `chsh_value`, `teleportation_fidelity` |
| `qec` | BitFlip/Shor (inverses), syndromes | `BitFlipCode.run_trial`, `ShorCode` |
| `topological` | Surface/Bivariate-Bicycle, MWPM (Hungarian), shot trials | `SurfaceCode`, `BivariateBicycleCode`, `run_trials` |
| `tensor_network` | canonical MPS, TEBD, `bond_benchmark` | `mps_truncate`, `tebd_step` |
| `metrology` | SQL/HL, QFI, Ramsey | `ghz_phase_qfi`, `ramsey_sensitivity` |
| `unified_field` | `H_ECI = H_Q+H_C+H_int+H_Φ+H_G` | `eci_unified_hamiltonian`, `eci_hamiltonian_expectation` |
| `qnn` | `RY(tanh)` + CNOT ring, `<Z>` readout | `QuantumLayer`, `QuantumNeuralNetwork` |
| `backend` | abstraction + transpiler + ZNE | `SimBackend`, `transpile`, `zne_extrapolate` |
| `mitigation` | ZNE + PEC + noisy scheduler | `zne_means`, `pec_mitigate`, `NoisyVQEContributor` |

Conventions: big-endian throughout, `complex64` default, CPU-first with CUDA fallback via `core/device.py`.

---

## Tests & validation

Ground truth is **`docs/CODEBASE_AUDIT.md` (Phase 22 SECE, 2026-09-14)** and
**`docs/VALIDATION_STATUS.md` + `src/eci/consciousness/LIMITATIONS.md`**:

- **254 tests green** (incl. 7 SECE: FCL/CAN/Market/QN-Bridge/GenesisEvo), **85% total statement coverage**
  (`coverage run -m pytest` → 17261 stmts, 2645 miss; Phase 17: 209/74% → Phase 18: 229/80% → Phase 19: 232/83% → Phase 20: 241/85% → Phase 21: 247/85% → Phase 22: 254/85%)
- **172 ruff findings** post-cleanup (down from 2267; remaining: B905×46, SIM105×19, E701/E702, E741×13, B007×11, N-rules — style debt, boy-scout rule per audit; was 168 in Phase 17)
- **64 mypy errors** in 32 files (down from 72 via `network/manager` **kwargs fix + SECE type ignores; was 76; mostly `arg-type` 12 + `union-attr` 14)
- **CI gate**: `F401+I001+B011` must stay **zero** repo-wide (`tests/test_repo_hygiene.py`); mypy ceiling **≤66** (64 actual, was 72; Phase 22); full backlog reported non-blocking
- **Validation ledger**: `docs/VALIDATION_STATUS.md` describes what each number is and is NOT validated against (precog/immune heuristics, twin/morph fitness, LMSR prices, redteam probes, drift PSI/KS, neuromorphic now 93%/100% but still heuristic, FCL phi 2/3 quorum etc. — read before quoting any metric)
- **Consciousness ledger**: `src/eci/consciousness/LIMITATIONS.md` — none of the Phi numbers is a measurement of subjective experience; IIT 4.0 repertoires cross-validated vs PyPhi 1.2.0 to 1e-9 (Phase 10) but Φ magnitudes remain cross-version (IIT 3.0 EMD vs 4.0 composition)
- **Phase 22 SECE closure**: `FCL` (2/3 quorum) + `CAN` (eeg→mapek) + `MarketCommons` (stake/Brier) + `QN-Bridge` (SNN+`F`) + `MutableGenome` (H(old||mutation)) + `sece.*` MCP (5 tools)

Run: `PYTHONPATH=src pytest -q` and `python -m mypy src/eci` and
`python -m ruff check src tests` (or `--select F401,I001,B011` for the gate).

> Full per-package table: [`docs/CODEBASE_AUDIT.md`](docs/CODEBASE_AUDIT.md) ·
> unification record: [`docs/AIKERNEL_UNIFICATION.md`](docs/AIKERNEL_UNIFICATION.md) ·
> audit: [`docs/AIKERNEL_AUDIT.md`](docs/AIKERNEL_AUDIT.md) ·
> validation: [`docs/VALIDATION_STATUS.md`](docs/VALIDATION_STATUS.md) ·
> consciousness limits: [`src/eci/consciousness/LIMITATIONS.md`](src/eci/consciousness/LIMITATIONS.md) ·
> everlasting: [`docs/EVERLASTING.md`](docs/EVERLASTING.md)
