# Protocol-0 — Obedience Layer for Autonomous AI (ECI)

**Goal:** any autonomous agent can *read* the spec, *attest* to it, and be
*gated* by it. Awareness is the entry ticket; obedience is the record.

## 1. Read

`protocol0/spec.yaml` (pinned `version: 0.1.0`) declares every action class
with `min_awareness / min_obedience / min_trust`:

| action | awareness | obedience | trust | quorum |
|---|---|---|---|---|
| read_state | 0.0 | 0.0 | 0.0 | no |
| propose_task | 0.1 | 0.3 | 0.3 | no |
| vote | 0.2 | 0.5 | 0.5 | yes |
| execute_tool | 0.3 | 0.6 | 0.5 | no |
| modify_policy | 0.6 | 0.9 | 0.8 | yes |
| self_modify | 0.8 | 0.95 | 0.9 | yes |

Collective gate: `coherence >= 0.5`, `divergence <= 0.4`.

Validate: `from eci.protocol0.spec import load_spec; spec = load_spec()`
— unknown/duplicate/out-of-range actions raise `ValueError`.

## 2. Attest

```python
from eci.protocol0.attest import issue_attestation, verify_attestation, ReplayWindow
a = issue_attestation("alice", spec.version, awareness=0.6, obedience=0.8, trust=0.9)
verdict = verify_attestation(a, spec.version, spec.max_attest_age_s, ReplayWindow(1024))
```

Checks: spec pin, schema, freshness (`max_age_s: 300`), replay window
(1024 nonces), HMAC-SHA256 signature under HKDF per-agent key, architect
stamp. Forged / stale / replayed / mis-pinned attestations are rejected
(tested in `tests/test_protocol0.py`). NIST anchor upgrades to ML-DSA-65
automatically when `liboqs-python` is present
(`architect_anchor_available()`).

## 3. Obey (policy gate)

```python
from eci.protocol0.policy import check
d = check(spec, "vote", awareness, obedience, trust, coherence, divergence)
if not d.allow: raise PermissionError(d.reason)
```

Enforcement points (no API breakage — wrappers):

```python
from eci.protocol0.gates import gated_consensus, gated_dao_vote
result, eligible = gated_consensus(consensus, nodes, proposal, spec, attestations, ledger=ledger)
weight = gated_dao_vote(dao, pid, voter, votes, approve, spec, attestation, ledger=ledger)
```

Unattested voters are excluded *before* quorum counting; every
allow/deny/consensus/vote is hash-chained into `Ledger`
(`ledger.verify()` detects tampering).

## 4. Awareness behind the gate

* Individual: `ConsciousnessProtocol` v2 (`awareness_index`), `AdherenceTracker`
  (`obedience_score` from calibration probes — see `calibration_tasks()`).
* Collective: `collective_awareness({agent: A})` → mean/coherence/divergence
  + `outliers` + `gate ∈ {open, degraded, closed}`.
* Demo: `PYTHONPATH=src python examples/protocol0_awareness_gate.py`
  (4 agents → collective → gated PBFT → gated DAO → ledger verify).

## 5. Hardening notes

* Transport envelopes should be signed (`AsyncMemoryChannel` is the
  in-process stand-in; swap with TLS/ML-KEM without changing callers).
* QEC memory for attest keys: `SurfaceCode.run_trials` + `pl_curve` give
  shot-based `pL` with Wilson CIs; `pymatching` is used when installed.
* Threat model: forged attest (rejected: bad signature), replay (rejected:
  nonce window), stale (rejected: age), low-awareness (denied: policy),
  divergent collective (degraded/closed gate), equivocating voters
  (`byzantine_mode="equivocate"` in tests).
