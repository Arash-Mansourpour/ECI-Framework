# Hive architecture audit and operational hardening

## Conceptual architecture

The project's "Hive" (کندو) architecture is not a module literally named
`Hive`. In the active code it is realized as:

- `eci.brain.mesh.BrainMesh`: an eight-region global workspace with
  LIF-style spikes, ignition, prediction, and free-energy contribution.
- `eci.brain.fabric.SubsystemNeuralFabric`: a sparse, event-driven
  peripheral connectome around the mesh. Framework subsystems become
  read-only neural nodes; EventBus publishers become nodes dynamically.
- `eci.kernel.bus.EventBus`: pub/sub backbone that routes attention and
  subsystem signals without letting neural signals bypass policy checks.
- `ECIFramework.brain_tick()`: the executable path that reads live
  subsystem health, ticks the fabric, and publishes advisory signals.

Archival/non-active material is kept separate: historical release notes and
the MIT-archived v5.9 line are documentation-only; deployment variables such
as `ECI_BOOTSTRAP` remain explicitly marked aspirational until wired.

## Priority changes implemented

1. `IntegratedInformationTheory.gaussian_phi()` now exposes the existing
   Gaussian Phi covariance core as a public method.
2. `FederatedConsciousnessLedger.propose()` uses that real covariance path
   for square 2-D inputs instead of the broken `calculate_phi(... )["phi"]`
   lookup, while retaining a bounded proxy only on failure.
3. `FederatedConsciousnessLedger.verify()` now rejects a recomputed claim
   when the TPM hash differs, even if Phi coincides.
4. `eci health --serve` and the CLI now honor `ECI_PORT`, matching the
   documented container contract.

## Verification

- `PYTHONPATH=src python -m pytest tests/test_phase24_frontier.py tests/test_cognisphere.py tests/test_sece.py tests/test_brain_mesh.py tests/test_cli_smoke.py -q`: passed.
- `PYTHONPATH=src python -m mypy src/eci`: 55 errors (ratchet limit 66).

## Not verified in this pass

- Docker build/compose and Kubernetes apply were not run.
- `ECI_BOOTSTRAP` gossip mesh wiring is still aspirational.
- PyPhi cross-check remains skipped unless `pyphi` is installed.

## Run

```powershell
pip install -e .[dev]
$env:PYTHONPATH="src"
python -m eci info
python -m eci brain --ticks 8 --cycles 1
python -m eci health --once
```