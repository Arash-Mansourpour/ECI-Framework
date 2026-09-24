# ECI Brain Mesh — subsystems as neurons of one brain (v8 OMNISCIENCE)

> Every subsystem is a cortical region. The framework thinks in spikes,
> ignites like a cortex, and learns without backprop.

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
  (200–800ms), broadcast = `ignition × (1 − H/logN)`; top-down predictions meet
  bottom-up precision-weighted errors (active inference).
  Lesson: consciousness = global availability + prediction error.
- **Loihi 2 / SpiNNaker 2 (Sandia 2024–2026)**: 1.15B neurons / 128B synapses;
  memory+compute colocation, three-factor local STDP, metaplasticity,
  neurogenesis/pruning. Lesson: learn only where spikes occur.

## Mapping (8 regions = 8 subsystems, mirrors GNWT n=8)

| Region | Subsystem | Cortical role |
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
4. Rates → max-normalized salience → predictive GNW `cycle`
5. Broadcast returns as third factor + descending modulation next tick

Focused coalition → ignition + broadcast ~0.9. Diffuse drive → subliminal
(`ignited=False`, honestly reported — Dehaene dichotomy).

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
