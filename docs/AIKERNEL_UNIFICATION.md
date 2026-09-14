# AIK Unification — consolidated record (Phases 1–17, v7.1.0)

One shared objective (`F = complexity + inaccuracy`), one contract
(`StateContributor`: posterior / update / free_energy_contribution),
one ledger (`KernelLedger` sums shares), one transport (MCP `aik.*`).
Version source: `src/eci/version.py` (`__version__ = 7.1.0`).

## Contract

`src/eci/aikernel/`: `GenerativeState` (Gaussian + quantum branches;
quantum→Gaussian via the metrology covariance map) · closed-form VFE
(torch-autograd) + quantum F (relative entropy, exact) · precision-split
belief functors (exact round-trip) · `StateContributor` protocol +
`KernelLedger` · MCP bridge (shared schema, rho-preserving wire format).

## Results on record

| Phase | Adapter / work | Number |
|---|---|---|
| 1 | kernel + functors | F vs Monte Carlo Δ<0.05; autograd vs analytic 1e-4; F=evidence 1e-4; quantum vs `density.relative_entropy` 1e-3 |
| 2a | quantum VQE | E −2.2360628 vs exact −2.2360682; F 3.81→1.89, 90% monotonic |
| 2b | consciousness Phi | Phi↔complexity: no monotone link (Bell both-high; product complex-only; mixed neither) |
| 2c | governance agents | shared-prior fusion fix; identical-info dF≈0; asymmetric dF≈0.841; b=50 limit cycle reported |
| 3 | IIT 4.0 (iit4.py) | disconnected Φ=0 exact; photodiode 1.0; XOR 0.5; mutual-copy 3.0 |
| 4 | mitigation (ZNE+PEC) | Bell-ZZ bias cut up to 1028x; VQE err recovered 16x; PEC exact ±σ |
| 5 | MCP transport | MCP total == direct total exactly; rho round-trips exactly |
| 6 | world-model + scientist | weighted-F parts reported; conjugate belief vs hand calc |
| 7 | FEP + audit + 7-ledger | own-F share; trajectory [10.32, 9.86, 8.81, 8.88] |
| 8 | EWC weights | Fisher posterior; displacement-priced share |
| 9 | 8-member default mesh | total == sum; describe covers all |
| 10 | hardening + PyPhi bridge | hygiene gate; PEC table q≤0.2; repertoires agree 1e-9 (see below) |
| 11 | operability: mesh in status + CLI | `system_status()["aik"]` + `eci aik {shares,total,describe}` on the live ledger |
| 12 | framework ledger wiring | `aik_snapshot()` provenance/audit points; trajectory moves only via driven updates |
| 13 | EWC full cycle | batch=replace vs online=accumulate (scale finding); adoption resets share |
| 14 | PyPhi table + glob gate | sia vs Φ ordering agrees on extremes; gate self-maintaining |
| 15 | coverage closure + snapshots | all 8 contributors registered; snapshot JSON round-trips |
| 16 | NaN guard (in-flight hardening) | `require_finite` on all 8 updates: silent poison + eigh crash become loud ValueError |
| 17 | codebase honesty pass | per-package audit + validation ledger + ratchet gate; real bugs fixed (see report) |
| 18 | Release hygiene (this phase) | license/version/README/CI/CITATION consistent; 7.1.0-PROTOCOL-vNext |

## PyPhi cross-check (Phase 10 — first EXTERNAL validation)

PyPhi 1.2.0 (IIT 3.0) installed as `validation` extra (needs a
`collections.abc` backfill shim on Python ≥3.10, function-scoped).
Bit-ordering bridge validated on asymmetric probes, not assumed.

| probe (mutual-copy / AND, state (1,1)) | PyPhi | ours | Δ |
|---|---|---|---|
| cause m{0}/p{0} | [0.5, 0.5] | same | 0 |
| cause m{0}/p{1} (cross constraint) | [0, 1] | same | 0 |
| effect m{0}/p{0} | [0.5, 0.5] | same | 0 |
| full-purview AND cause/effect | point / uniform | same | 0 |
| big-Phi mutual-copy | 1.0 (IIT 3.0 EMD) | 3.0 (IIT 4.0 composition) | incommensurate by design |

## Audit

Full subsystem table: `docs/AIKERNEL_AUDIT.md` (8 adapters, 6 packages;
everything else explicitly poor-fit with reasons). Honesty ledger:
`src/eci/consciousness/LIMITATIONS.md`.
