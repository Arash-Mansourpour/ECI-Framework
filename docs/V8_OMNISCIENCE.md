# v8.0 OMNISCIENCE — advanced platform release

Version: `8.0.0-OMNISCIENCE` (`src/eci/version.py`), paper `infinity.23.0`.

## What changed

| Track | Module | Verdict |
|---|---|---|
| Fitness | `arch/fitness.py` (6 checks) + `arch/adr.py` (6 ADRs) | `eci v8` green |
| Quantum | `quantum/hardware.py` | sim default, qiskit/braket fail-closed, `BackendRouter.route` |
| Federation | `federation/p2p.py` | memory (deterministic) + TCP transports, 2/3 gossip quorum, partition stall proven |
| Economy | `economy_attack.py` | whale flagged+unprofitable, collusion detected, slash capped |
| Observability | `observability/otel.py` | NoOp-unless-installed + native Prometheus |
| Research | `research/loop.py` | propose→twin→canary→vote→Brier, ARCHITECT-stamped |
| **Brain** | `brain/` (neuron/synapse/connectome/workspace/mesh) | 8 subsystems simulated as neural populations, GNW-style ignition math on simulated rates, local STDP |

## Run

```bash
$env:PYTHONPATH="src"; python -m eci v8
$env:PYTHONPATH="src"; python -m eci brain --ticks 32 --cycles 3
$env:PYTHONPATH="src"; python -m pytest tests/test_brain_mesh.py tests/test_v8_advance.py -q
```

## Production

- `k8s/deployment.yaml` + `k8s/service.yaml`: probes on `/health`, metrics on `/metrics`
- Health: `eci health --once` (JSON) / `--serve --port 8777` (`/health` + `/metrics` Prometheus)
- No new hard dependencies (torch/numpy/scipy/pyyaml/cryptography only)

## ADRs

ADR-001 facade composables · ADR-002 fail-closed hardware · ADR-003 no-libp2p P2P ·
ADR-004 attack sim · ADR-005 graceful OTel · ADR-006 ledgered research loop.
See `src/eci/arch/adr.py`.
