# ECI Brain Mesh — subsystems simulated as neural populations (v8 OMNISCIENCE)

> Every subsystem is simulated as a cortical-inspired region. The framework runs spiking math,
> computes GNW-style ignition flags on simulated rates, and updates weights without backprop.

## Why (web research, 2026)

- **SpikingBrain 7B/76B (Sep 2025–May 2026)**: adaptive-threshold spiking +
  hybrid-linear attention + MoE modular specialization; 100x TTFT on 4M tokens,
  69% neuronal sparsity, stable 76B training on non-NVIDIA clusters.
  Lesson: event-driven sparsity + modular regions = scale.
- **Parallelized Hierarchical Connectome / PHCSSM (May 2026)**: diagonal
  per-neuron core + hierarchical connectome matrix (lateral + feedback) with
  O(log T) parallel scan; Dale E/I, ALIF, Tsodyks–Markram STP built in.
  Lesson: separate temporal core from spatial connectome.
- **Predictive GNW (Whyte/Dehaene)**: ignition is non-linear all-or-none
  (200–800ms), broadcast = `ignition × (1 − H/logN)`; top-down estimates meet
  bottom-up precision-weighted errors (active inference).
  Lesson (analogy only): GNW models global availability as ignition math plus
  prediction-error math, not felt experience.
- **Loihi 2 / SpiNNaker 2 (Sandia 2024–2026)**: 1.15B neurons / 128B synapses;
  memory+compute colocation, three-factor local STDP, metaplasticity,
  neurogenesis/pruning. Lesson: learn only where spikes occur.

## Mapping (8 regions = 8 subsystems, mirrors GNWT n=8)

| Region | Subsystem | Cortical analogy (labels only, not anatomy) |
|---|---|---|
| quantum | `quantum_sim` | sensory input |
| consciousness | `consciousness_analyzer` | prefrontal |
| governance | `dao` | cingulate (control) |
| memory | `agents` | hippocampus |
| market | `market_commons` | striatum (value) |
| immune | `immune` | amygdala (threat) |
| federation | `network_manager` | corpus callosum (binding) |
| cognition | `cognition` | parietal (integration) |

## One tick

1. `sense(snapshot)` encodes each subsystem into input currents [0,2]
2. Event-driven rollout (`ticks`, default 32): silent regions cost ~0
3. Local three-factor STDP + metaplasticity on spikes only (no backprop)
4. Rates → max-normalized salience → GNW-style `cycle` ("predictive" = EMA of salience, not a world forecast)
5. Broadcast returns as third factor + descending modulation next tick

Focused coalition → ignition flag + broadcast ~0.9. Diffuse drive → below-threshold flag
(`ignited=False`, honestly reported — Dehaene-style math dichotomy, not measured awareness).

## Honesty ledger

- Firing rates are properties of the LIF simulation, not brain measurements
- Ignition = competition math on simulated rates, not conscious experience
- Twin/drill limits inherited; Brier exact on resolved outcomes only
- See `docs/VALIDATION_STATUS.md` + `src/eci/consciousness/LIMITATIONS.md`

## API

```python
from eci.brain import build_default_mesh
m = build_default_mesh(seed=0)
out = m.sense({"consciousness": {"phi": 1.0, "awareness": 1.0}})
# {"ignited": True, "winner": "consciousness", "broadcast": 0.94, ...}
m.adapt_structure()  # prune silent + sprout new synapses
```

CLI: `python -m eci brain --ticks 32 --cycles 3`
Framework: `fw.brain_tick()` + `system_status()["brain"]` + `v8_status()["brain"]`
Ledger: `BrainMesh` is a `StateContributor` (F = workspace surprise).
