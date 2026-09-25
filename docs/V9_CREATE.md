# v8.1 CREATE — creativity × science release

Version: `8.1.0-CREATE` (`src/eci/version.py`), paper `infinity.24.0`.

Seven tracks that raise creativity (diversity without collapse) and science
(trustworthy claims). Research grounding: MAP-Elites/POET quality-diversity,
MLReplicate verification gap (Aug 2026 survey), ARC-AGI-3 interactive
exploration, AREX bi-level self-improvement, SpikingBrain sparsity economics.

## Tracks

| # | Track | Module | Demo in `eci create` |
|---|---|---|---|
| 1 | Quality-Diversity | `creativity/` | morph-probe archive, 4 cells, best 1.0 |
| 2 | Verification gate | `verification/` | claim admitted only if verifier green |
| 3 | Exploration | `exploration/` | keydoor solved, efficiency 0.83 |
| 4 | Causality | `causality/` | interventional ATE(X→Y) ≈ 2.5, skeleton |
| 5 | Energy | `energy/` | brain cycle in nJ, sparsity 0.94, priced |
| 6 | Interpretability | `interpret/` | probe acc 0.95, causal dims → redteam lead |
| 7 | Recursion | `recursion/` | outer loop adopts better quorum on Brier |

## Honesty ledger

- QD fitness is task-defined (change the task, change the winner)
- ATE is exact for the linear-Gaussian model, not a world measurement
- Energy uses Horowitz 45nm reference estimates (0.9pJ AC / 4.6pJ MAC)
- Skeleton discovery assumes causal sufficiency + faithfulness
- Probes show correlation first; only ablation proves causality

## Run

```bash
$env:PYTHONPATH="src"; python -m eci create
$env:PYTHONPATH="src"; python -m pytest tests/test_v9_create.py -q
```
