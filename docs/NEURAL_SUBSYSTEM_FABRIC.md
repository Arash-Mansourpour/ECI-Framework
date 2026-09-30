# Neural Subsystem Fabric (additive integration layer)

The neural fabric extends the existing Brain Mesh without replacing the
framework facade, Kernel, EventBus, `StateContributor`, or subsystem APIs.
`BrainMesh` remains the eight-region global-workspace model; the new
`SubsystemNeuralFabric` adds a sparse population of live component and event
nodes around it.

## Runtime flow

1. `ECIFramework.brain_tick()` reads health snapshots from active subsystem
   objects through read-only adapters. Applications can also provide adapters
   with `fabric.register(name, region, observe=...)`.
2. EventBus publishers become nodes dynamically. Events reduce to bounded
   activity/error signals; payloads are not retained by the fabric.
3. The eight macro-regions summarize subsystem health/activity and enter the
   existing LIF/Global-Workspace cycle.
4. A sparse peripheral connectome combines local drive, recurrent weighted
   activity, regional attention and global broadcast. Bounded Hebbian updates
   adapt only fabric weights.
5. `brain.subsystem.signal` events route attention back through EventBus. The
   guarded agent loop consumes them as optional context; they do not grant
   tool permissions or bypass policy checks.

```text
subsystem health ─┐                  ┌─► brain.subsystem.signal ─► agent context
                  ├─► sparse fabric ─┤                         └► subscribers
domain events ────┘        │         └─► Global Workspace / BrainMesh
                            └─ bounded local plasticity
```

Nodes map onto the existing eight macro-regions by a stable name mapping;
unknown nodes join the cognition region and can be assigned explicitly. The
graph stays sparse, includes a low-gain connected backbone, uses a fixed seed
for reproducible initialization, and bounds learned weights. A failed health
adapter is recorded for that node and does not stop other subsystems.

## Inspect and extend

```python
from eci.brain import SubsystemNeuralFabric, build_default_mesh

fabric = SubsystemNeuralFabric(build_default_mesh(seed=7), seed=7)
fabric.register("my-planner", "cognition", observe=my_planner.health)
result = fabric.tick()
print(result["fabric"])  # nodes, edges, region counts, spikes, top activations
```

The framework attaches available component health adapters automatically.
`fw.brain_tick()` keeps returning the macro winner/broadcast and now adds a
`fabric` report. `system_status()` and `v8_status()` expose current fabric
health; Prometheus receives node, edge and spike metrics. `ResearchLoop`
publishes hypothesis and resolved-cycle events, joining the same graph.
`fabric.topology()` exports a JSON-safe node/edge snapshot with region,
activation, learned weight and excitatory/inhibitory polarity for visualization.

## Scientific and safety boundaries

- Neural activations, spikes, regional mappings, and plastic weights are
  software signals, not measurements of neurons or human cognition.
- Plasticity in this layer does not establish causal influence on the source
  subsystem. Outputs are advisory messages only.
- State changes still pass through the original subsystem APIs, authz, tool
  registry, verification and governance paths.
- In-memory topology is process-local; it is not yet a durable cross-process
  connectome.

Future extension points include versioned signal schemas, explicit adapters
for every subsystem, replayable topology snapshots, partition-aware
federation, and canary-verified plasticity changes. They remain composable
modules so stable core contracts do not need to change.
