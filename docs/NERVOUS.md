# Nervous System — Precog + Neural Cortex (ECI)

**Thesis:** everything else judges the past (ledger), the present (policy
gates), or reacts (immunity). The nervous system predicts the future and
feels the whole mesh at once.

## Precog (`precog/`)

Bayesian P(violation | trajectory) over 5 inverted features, learned online
(exact logistic steps, bounded weights), with reliability calibration (ECE
over 10 bins). Tiers: watch 0.5 / escalate 0.7 / hold 0.9. Misses cost 10x
false alarms. `ProvisionalHold` restrains BEFORE breach but always leaves
challenge/appeal/read open — reversible, TTL-expiring, ledger-recorded.
Contrast quarantine (post-breach, appeal-gated): hold is lighter and faster.

## Cortex (`neural/`)

Agents are graph nodes (8-D features), trust forms edges, a residual
message-passing GNN reads mesh state (rogue neighbors shift BEFORE acting),
a GRU world-model forecasts collective {coherence, obedience, risk}, and
`advise()` returns per-agent risk+gate plus `mesh_health` in [0,1].
`Cortex.fit()` trains end-to-end on ledger outcomes (demo: rogue risk >
honest risk after 80 steps). Pure torch, CPU-friendly.

## Run

```bash
PYTHONPATH=src python examples/nervous_demo.py
PYTHONPATH=src pytest tests/test_nervous.py -q
```
