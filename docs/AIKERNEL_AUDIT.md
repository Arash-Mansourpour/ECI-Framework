# AIKernel Subsystem Audit (Phase 7, Part 1 — blocking)

Every package under `src/eci/`, exactly one category each. Re-confirmed
rows for the 4 already-adapted subsystems are marked. No new adapter code
was written before this table existed.

Categories: **good-fit** (maintains a belief-like distribution; F is a
natural reading of its existing objective) · **adaptable** (relevant
state, but the F-share needs a real framing decision) · **poor-fit**
(not probabilistic/informational — wrapping it would be forced).

## Adapted (re-confirmed)

| package | category | reason | adapter status |
|---|---|---|---|
| quantum | good-fit | VQE loss is F exactly via the energy-target likelihood (Phase 2a) | existing: VQEContributor (+NoisyVQEContributor, Phase 4) |
| consciousness | adaptable | Phi ≠ F-share by explicit decision; share is complexity KL (Phase 2b) | existing: PhiContributor |
| governance | good-fit | conjugate agent posteriors; consensus is shared-prior fusion (Phase 2c) | existing: AgentContributor |
| cognition (world_model, scientist) | good-fit | real posterior Gaussians + VFE-shaped/conjugate objectives (Phase 6) | existing: WorldModelContributor, ScientistContributor |

## New in this phase

| package | category | reason | adapter status |
|---|---|---|---|
| consciousness (FreeEnergyAgent) | good-fit | maintains a Gaussian belief (MAP μ + fixed precisions) and minimizes its OWN F literally — Laplace posterior N(μ,(ΠAᵀA+I)⁻¹) is exact for its linear-Gaussian model | existing: FEPContributor (Phase 7) |
| learning (EWC) | good-fit | Fisher precision + snapshot means = Gaussian posterior over weights (textbook variational reading of the EWC penalty) | existing: EWCContributor (Phase 8) |

## Deferred, not denied (genuine fits, out of scope)

| package | category | reason | adapter status |
|---|---|---|---|
| quantum (QNN) | good-fit | variational parameters trained by a loss, same pattern as VQE | deferred-duplicate: quantum/ already conforms; second adapter adds no coverage |

## Poor fit, do not adapt

| package | reason |
|---|---|
| precog (RiskEngine) | point logistic weights + calibration counts; no maintained distribution (Laplace would need new machinery = forcing) |
| cognition (tom) | capability/coop are lr-updated point estimates; no success/failure counts for a Beta reading |
| cognition (planner) | CEM distribution over action sequences is transient per-plan, not a persistent belief |
| cognition (curiosity) | RND predictor + error scalar; no posterior |
| cognition (executive) | ECE bins + commitment embeddings; no distribution |
| cognition (consolidation) | episodic store; storage, not belief |
| cognition (causal) | graph with edge strengths; not a distribution |
| cognition (charter) | rules + amendments; symbolic |
| neural (GNN/Cortex/WorldModel) | deterministic message-passing/predictors ("fixed spread"); RSSM role already covered by cognition/world_model |
| learning (MAML/NAS/federated) | meta-init/architecture-search/DP-averaging procedures; no distributional belief |
| immune | detector population with affinities; pattern matching, not inference |
| morph, genome | populations/structures/genes; evolution, not belief |
| semantic | symbolic facts with confidences; KL over confidences is undefined |
| market, futura (treasury, Futarchy wrapper) | inventories/balances/mechanisms; the LMSR *mechanism* was studied in 2c, the market itself holds no belief |
| court | verdicts/panels; symbolic outcomes |
| economy | balances; accounting |
| twin | simulator procedure |
| authz, protocol0 | rules/policies/decisions; symbolic |
| network (consensus/gossip/DHT/reputation/transport) | procedures and point scores; beliefs live in the governance adapter |
| agents (loop) | ReAct procedure with budget; belief covered by governance AgentContributor |
| redteam (challenger/forecasters) | probes + point probs + Brier scores; per-claim Beta would need new count machinery alongside the registry |
| mlops (registry/drift) | versions + divergence *measures*; measures divergence but maintains no belief |
| cybernetics (autopoiesis) | viability dynamics scalar; no distribution |
| mapek | SLO control loop; setpoints, not beliefs |
| resilience | breakers/sagas/limiters; state machines |
| chaos | fault plans; scenarios |
| eval, benchmarking | harnesses; measurement, not belief |
| orchestration | DAGs/scheduler; plans, not beliefs |
| data (cache/vectors/blobs) | storage |
| persistence, streaming | store/transport |
| provenance, verify (audit/proofs), continuum | records/receipts/snapshots; evidence, not belief |
| caps, security (pqc/secrets/channel) | crypto material/primitives |
| compat | version registry |
| supply | SBOM artifact |
| tenancy, plugins | quotas/manifests |
| api, mcp, kernel | plumbing/transport (mcp CARRIES the interface) |
| observability | meters/counters |
| core, config, constants, logging, version, health | types/settings/diagnostics |
| framework, __main__ | composition root / CLI |

## IIT4 note (from Phase 3 context)

`consciousness/iit4.py` has no `StateContributor` — deliberate (forcing
continuous state through the discrete TPM path would violate its §1
limitation). Stays deferred unless a discrete-native contributor design
emerges; NOT filled silently in this phase.

## Phase 9 note — default mesh complete

`aikernel.mcp_bridge.build_unification()` now registers all 8 adapters
(quantum, noisy, phi, agent, world, sci, fep, ewc) in the default ledger
and tool mesh, and `aik.ledger.describe` covers every member class (no
more `unlisted` for known adapters). No new adapter was needed: this
phase closed the mesh, not the audit.
