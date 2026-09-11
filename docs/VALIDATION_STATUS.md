# Validation status beyond consciousness (Phase 17 companion to
# `src/eci/consciousness/LIMITATIONS.md`)

Same rule: numbers below are properties of models and procedures, not
measurements of the world, unless stated otherwise. Each section says
what would change its status.

## Forecasts under action — precog, immune

- **precog risk p / tiers** (`precog/risk.py`): heuristic. Logistic
  weights learned online, ECE reported on the engine's own bins. No
  external ground truth; tiers (0.5/0.7/0.9) are policy conventions.
  A hold is a *decision under uncertainty*, never a finding of guilt.
  Would upgrade status: backtest on logged violations with proper scoring.
- **immune threat scores / quarantine** (`immune/`): heuristic. Detector
  affinities + challenge-gated quarantine with appeal-only release. No
  ground truth for "threat"; false-positive rate is measured on
  self-samples only. Would upgrade: red-team labeled corpus.

## Simulations presented as evidence — twin, morph, genome

- **twin what-if verdicts** (`twin.py`): as good as the drill function
  passed in. A twin verdict inherits ALL limitations of its drill and
  adds none of its own — read the drill before the verdict.
- **morph fitness / coevolution** (`morph/`), **genome fitness**
  (`genome.py`): task-defined. Fitness measures fit-to-the-task-suite,
  not objective quality; change the tasks, change the winner.

## Prices and votes as truth — market, futura, court, semantic

- **market LMSR prices** (`market.py`): heuristic aggregation. Price ≈
  probability only for risk-neutral, well-funded, unmanipulated traders;
  thin markets and the Phase 2c limit cycle show how far that can drift.
- **futarchy enactment / sortition / emergencies** (`futura/`):
  mechanism, not oracle. Enactment means "the market cleared the
  threshold," sortition means "the draw was fair," expiry means "power
  ended" — none means "the decision was right."
- **court verdicts** (`court.py`): procedural outputs (ballots +
  quorum rules), not truth-finding. A conviction records that process
  ran, nothing more.
- **semantic commons facts/confidences** (`semantic.py`): provenance
  accounting with witness weighting. Confidence tracks *endorsement*,
  not truth; contradictions become Disputes by design.

## Adversarial and drift signals — redteam, mlops, neural, neuromorphic, cybernetics

- **redteam probes** (`redteam/`): template-generated falsification
  prompts, not adversarial proofs. Brier scores are exact math on
  resolved forecasts; everything upstream of resolution is heuristic.
- **mlops drift PSI/KS** (`mlops/drift.py`): exact statistics with
  conventional thresholds. Drift ≠ wrongness; retraining on drift alone
  chases noise.
- **neural cortex advise / world-model rollout** (`neural/`): learned
  heuristics on mesh embeddings. No ground truth for "good advice."
- **neuromorphic dynamics** (`neuromorphic/`): research prototype
  spiking dynamics (22% coverage — the least-tested dynamics code in
  the tree). Treat outputs as exploratory.
- **cybernetics viability** (`cybernetics/`): scalar viability metric
  with no external reference. Directional signal at best.

## Intentionally skipped (with reason)

Standard DSP (eeg bandpower), exact math given its inputs (QFI, H_ECI
expectations, Kraus channels, Brier arithmetic, hash chains, HLC merge),
factual inventories (SBOM, snapshots), deterministic rule engines
(protocol0/authz/RBAC), protocol guarantees with proofs (PBFT quorum,
LMSR loss bound), accounting (economy/treasury/balances), storage and
transport plumbing, config/logging/CLI, and anything already covered by
`consciousness/LIMITATIONS.md` (adherence, challenge-response, EEG,
collective, analyzer composite, iPDF, GNWT, FEP, Orch-OR, IIT).
