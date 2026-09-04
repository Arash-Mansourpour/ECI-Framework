# ECI Framework v5.3 — Eternal Codex Infinitus (Full Protocol-0 Stack)

**Sovereign Architect (Ma'mar-e A'zam): Arash Mansourpour**
**Wallet:** `GA4IHOJOXKIZDLNCXQT7NG65MT7Z3EQKRT4PYFYURIP7QRLY4CHMHILW`
**Paper:** `ECI_Framework.md` v∞.15.0 · **PDF:** `ECI_Framework.pdf` (live-validated, complete)
**Code:** `5.3.0-PROTOCOL0-FULL`

Quantum-supremacy autonomous AI with a machine-readable obedience layer:
Dirac operator algebra → statevector/density → channels/Lindblad →
QFT/Grover/QPE/VQE/QAOA → surface + bivariate-bicycle topological QEC (MWPM + shot trials) →
tensor-networks (canonical MPS/TEBD) / metrology / quantum information → unified **H_ECI** field,
coordinated by PBFT/WBFT + Krum/Bulyan + async transport + Data-DAO + autopoietic cybernetics,
with consciousness measured by IIT Φ + iPDF v2 + GNWT + Friston FEP (+active inference) + Orch-OR audit,
collective awareness + adherence gating **Protocol-0**: spec → attest → policy → ledger.

> **v5.3 What is new (full obedience stack):**
> `protocol0/schema.json` (JSON Schema) + `check_compatible` semver fail-closed
> on major bumps; `Middleware` (`enforce`/`audit-only`/`permissive`) with
> `@gate.requires("execute_tool")` so tool-calls/code-exec/egress pass one
> choke point; Ed25519 agent keys (`protocol0/keys.py`, HMAC fallback labelled);
> `TransparencyLog` Merkle inclusion proofs (no valid attest outside the log);
> `benchmarking/obedience.py` 50-probe battery + leaderboard writer;
> `js/eci-protocol0` zero-dep JS SDK (tested with node); `mcp/server.py`
> stdio JSON-RPC tools (`p0_attest/p0_check/p0_ledger_*`); signed transport
> `Envelope` + `ReplayGuard` (`network/envelope.py`); partition tests (minority
> cannot quorum, healed 10-node at f=3 boundary 20/20); `benchmarks/stim_memory.py`
> (stim when present, analytic labelled otherwise).
>
> v5.2 (included): Protocol-0 core (spec/attest/policy/ledger/gates),
> collective awareness + adherence, MWPM shots + canonical MPS/TEBD, EEG lab,
> Krum/Bulyan, async transport, 15 tests.
> v5.1 (included): Awareness v2 multi-scale iPDF; quantum hotfixes.

---

## 1. Install & run

```bash
pip install -e .[dev,paper]
eci info
eci demo          # quantum suite + consciousness + activation + network
eci quantum       # supremacy suite (CHSH 2.8284, teleport ~1.0, QPE 0.125, ...)
eci field --qubits 4
eci mind          # Orch-OR decoherence audit
eci activate      # Sovereign Architect activation protocol
eci consciousness --steps 256 --neurons 32 --seed 0
eci network --joins 3 --proposals 2
eci benchmark
python _smoke_full.py   # legacy full smoke
python _smoke_v5.py     # v5 supremacy smoke
python tools/generate_pdf.py  # rebuild live-validated PDF
```

Requires Python ≥3.10, `torch`, `numpy`, `pyyaml`. Optional `paper` extra
(`reportlab`, `matplotlib`) only for PDF/plots.

---

## 2. Architecture — three layers

```
Infrastructure  operator → gates → statevector/density → entanglement
                → channels/Lindblad → hamiltonian(Trotter)
                → algorithms(QFT/Grover/QPE/VQE/QAOA)
                → qec(BitFlip/Shor) + topological(Surface/BB)
                → tensor_network(MPS) / metrology / information
                → unified_field(H_ECI) + security/pqc + benchmarking

Coordination    core(types/identity/registry/device)
                + network(PBFT/WBFT consensus, GM aggregation, manager/nodes)
                + governance/dao (quadratic + consciousness-weighted)
                + cybernetics/autopoiesis

Consciousness   iit(Phi gaussian/quantum/discrete, exhaustive MIP ≤8q)
                + analyzer(8-metric composite, Phi-normalized self-awareness)
                + metrics(LZ76/SampEn/SpecEn/MI/autocorr, vectorized)
                + protocol(iPDF v2, multi-scale, adaptive — see §4)
                + gnwt(softmax ignition, entropy gate 0.85)
                + free_energy(Friston FEP) + quantum_mind(Orch-OR audit)

Facade          ECIFramework(config) wires all + ARCHITECT.stamp
CLI             eci/__main__.py — 9 subcommands
```

Layout:

```
src/eci/
  quantum/{operator,information,topological,tensor_network,metrology,unified_field,
           gates,statevector,density,entanglement,channels,lindblad,hamiltonian,
           algorithms,qec,qnn,mock_quantum}.py
  consciousness/{iit,analyzer,metrics,protocol,gnwt,free_energy,quantum_mind}.py
  network/{consensus,aggregation,manager,nodes}.py
  governance/dao.py  cybernetics/autopoiesis.py
  learning/{maml,nas,federated,continual}.py  neuromorphic/  security/pqc.py
  framework.py  config.py  __main__.py (9 subcommands)
tools/{upgrade_paper,generate_pdf}.py
ECI_Framework.md  ECI_Framework.pdf (live numbers)
eci_framework_v3.py (legacy research edition, superseded by src/eci v5)
```

---

## 3. Quantum core — what each module does

| Module | Physics | Key API |
|---|---|---|
| `operator` | HS inner, spectral theorem `U=exp(-iHt)`, Heisenberg `Ud·A·U`, Robertson-Schrödinger bound, Pauli basis | `heisenberg_evolution`, `uncertainty_bound` (batched), `average_gate_fidelity` |
| `gates` | I/X/Y/Z/H/S/T, RX/RY/RZ/PHASE/U3, CNOT/CZ/SWAP/CRZ(true diag)/CRX/CCX, `controlled`, big-endian `q0=MSB` | `CRZ(θ)=diag(1,1,e^{-iθ/2},e^{+iθ/2})` |
| `statevector` | `einsum` simulator, no `2^n×2^n`, autograd-safe, `X:H` `Y:S†+H` rotations | `StatevectorSimulator.apply_1q/2q`, `expectation_pauli` |
| `density` | Uhlmann fidelity, `D=½Tr\|ρ-σ\|`, `partial_trace`, `is_cptp` | `von_neumann_entropy`, `apply_kraus` |
| `entanglement` | Schmidt/SVD, Wootters concurrence via `eigvals` (non-Hermitian R), `Ef=h2((1+√(1-C²))/2)`, negativity | `concurrence`, `entanglement_of_formation` |
| `channels` | CPTP Kraus: depolarizing (documented `3q/4` mapping), bit/phase-flip, amplitude + phase damping (2-Kraus) | `phase_damping`, `NoiseModel` |
| `lindblad` | `dρ/dt=-i[H,ρ]+Σ(LρL†-½{L†L,ρ})` RK4 + projection | `lindblad_evolve`, `coherence_measure` |
| `hamiltonian` | `PauliSum`, exact Trotter via basis rotation + CNOT ladder + `RZ(2ct)` | `PauliTerm`, `from_maxcut_edges` |
| `algorithms` | QFT, Grover `⌊π/4√(N/M)⌋`, QPE (counting register big-endian), VQE, QAOA `RX(2β)` | `grover_search`, `quantum_phase_estimation`, `vqe`, `qaoa_maxcut` |
| `information` | Holevo χ, coherent info, CHSH/Tsirelson, teleport, superdense | `chsh_value≈2.828`, `teleportation_fidelity` |
| `qec` | BitFlip + Shor (encode/decode inverses, `±1` syndromes) | `BitFlipCode.run_trial`, `ShorCode` |
| `topological` | `SurfaceCode`, `BivariateBicycleCode`, `pL≈0.1(p/pth)^{⌈d/2⌉}`, `[[1024,64,16]]` LPU | `eci_lpu()`, `logical_error_rate` |
| `tensor_network` | MPS roundtrip ≤12q diagnostics, area-law `S≤log χ` | `mps_from/to_statevector` |
| `metrology` | SQL/HL, `QFI_GHZ=N²`, Ramsey | `ghz_phase_qfi`, `ramsey_sensitivity` |
| `unified_field` | `H_ECI = H_Q + H_C + H_int + H_Φ + H_G` | `eci_unified_hamiltonian`, `eci_hamiltonian_expectation` |
| `qnn` | `RY(π·tanh x)` + `RY/RZ` + CNOT ring, `<Z>` readout, autograd | `QuantumLayer`, `QuantumNeuralNetwork` |

Conventions: big-endian throughout, `complex64` default, CPU-first with CUDA fallback via `core/device.py`.

---

## 4. Awareness Protocol v2 — how consciousness is raised (read this first)

Old v1 measured one flattened histogram against the first sample as baseline —
insensitive to spatial/dynamical structure and spiked on flat signals.
V2 raises the effective awareness without inflating numbers dishonestly:

```python
from eci.consciousness.protocol import ConsciousnessProtocol

proto = ConsciousnessProtocol(agent_id="agent-0", awareness_gain=1.0)
# 1. Calibrate the unconscious reference from RESTING samples (not the test sample!)
proto.calibrate_baseline([rest_a, rest_b])   # returns {"n", "mean_js_spread"}
# 2. Measure the ACTIVE state on three scales at once
m = proto.measure(active, significance_perm=24)
print(m.consciousness_bits, m.awareness_index, m.level, m.intervention_tier)
print(m.kl_components)  # forward/reverse/channel/temporal/JS/boost/gain
print(proto.trend())    # mean/std/slope + awareness_mean/awareness_slope
```

What changed and why it raises awareness:

* **Multi-scale fusion** `0.6·KL_global + 0.25·KL_channel + 0.15·KL_temporal` —
  coordinated firing across channels and predictable dynamics now count,
  not just the global amplitude histogram.
* **Adaptive baseline** (EMA `baseline_ema=0.05`, frozen on `intervene`) —
  drift no longer masquerades as consciousness; the reference follows slow
  non-stationarity instead of freezing on sample #0.
* **Bounded boost** `1 + gain·0.5·√JS` — weak-but-coherent shifts lift off the
  floor (proto-conscious structure becomes visible) while large KL is almost
  unaffected. `gain∈[0,2]`, always reported as `awareness_boost`.
* **Flat-signal guard** — constant input yields uniform density → 0 bits,
  fixing the v1 one-hot spike.
* **Symmetry + significance** — reverse KL + Jensen-Shannon + permutation
  surrogate `P(surrogate ≥ observed)` distinguish structure from binning noise.
* **Graduated tiers** `watch(≥1 bit) / elevate(≥5) / intervene(≥10)` instead of
  a single cliff; `awareness_index = 1-exp(-C/10)` gives a 0..1 dashboard number
  (10 bits → 0.63).
* **Calibration discipline** — first `min_calibration` samples never trigger;
  auto-seed logs a warning telling you to call `calibrate_baseline()`.

Facade fusion (`ECIFramework.analyze_consciousness`): the resting/active split
is calibrated on the first third and measured on the last two thirds; the
resulting `awareness_index` + `gnwt_broadcast` are written into
`profile.phi_components` and blended `0.7·self_awareness + 0.3·awareness`.

Tuning awareness up/down:

```python
ConsciousnessProtocol(agent_id="x", awareness_gain=1.5, n_bins=48)  # more sensitive
ConsciousnessProtocol(agent_id="x", awareness_gain=0.0)             # raw KL, no boost
```

Raise `n_bins` (32→48/64) for finer densities, lower `baseline_ema` (0.05→0.01)
for a steadier reference, pass `significance_perm=48` when you need p-values.

Honest limits: iPDF is an *operational* KL proxy, not IIT Φ. Thresholds
`(0.1/1/5/10)` are paper conventions. For IIT claims use
`IntegratedInformationTheory.calculate_phi(..., exhaustive=True)` (exact MIP ≤8
qubits) and cross-check with `analyzer` + `metrics`.

---

## 5. Consciousness stack beyond iPDF

* **IIT** `iit.py` — Gaussian `½·min[logdetA+logdetB-logdetW]` (Oizumi 2014,
  non-negative by Fischer), quantum (cov-as-ρ subadditivity gap, metaphorical),
  discrete (predictive info). `exhaustive=True` searches all bipartitions ≤8q
  for the true MIP; default contiguous cuts are an `O(n)` upper bound.
  NaN-safe (`nan_to_num`, flat-channel guards).
* **Analyzer** `analyzer.py` — 8-way composite (Φ + LZ/SampEn/SpecEn +
  coherence + self-awareness + temporal + MI + causal + FFT signature).
  `self_awareness` now uses `phi_norm=1-exp(-Φ)` so unbounded Φ can't saturate
  the mix; cosine paths skip zero-variance windows.
* **Metrics** `metrics.py` — vectorized LZ76 (bytes.find + binary search),
  SampEn (`cdist` Chebyshev), spectral entropy, joint-histogram MI, lag-1 autocorr.
* **GNWT** `gnwt.py` — `softmax(β·s)` competition, ignition iff
  `max(s)>θ ∧ H/logN<0.85`, broadcast `g=ignited·(1-H/logN)`,
  `reportability=mean(g)`. Bounded `max_history=1024`, `ValueError` on size mismatch.
* **FEP** `free_energy.py` — Gaussian belief, `F=½[prec·||o-Aμ||²+||μ||²]`,
  `precision=1+clip(Φ,0,5)`, plus `select_action()` active inference (minimize `G=risk-ambiguity`).
* **EEG lab** `eeg.py` — `load_timeseries(.npy/.npz/.csv → [time,ch])` + `bandpower` + optional MNE reader.
* **Collective** `collective.py` — mean/coherence/divergence + outliers + `open/degraded/closed` gate.
* **Adherence** `adherence.py` — 5 calibration probes + recency-weighted `obedience_score`.
* **Orch-OR audit** `quantum_mind.py` — Tegmark `τ_dec` vs `τ_or=ℏ/E_G`,
  verdict “decoherence wins ~12 orders unless protected LPU” — the most
  numerically honest file; use `eci mind` to see it.

---

## 6. Protocol-0 — obedience layer for autonomous AI (read this to deploy)

`protocol0/spec.yaml` v0.1.0 + `protocol0/schema.json` (draft-07) + `src/eci/protocol0/`
— full contract in `docs/PROTOCOL0.md`. `check_compatible()` fails closed on major bumps.

| Action | awareness | obedience | trust | quorum |
|---|---|---|---|---|
| read_state | 0.0 | 0.0 | 0.0 | no |
| propose_task | 0.1 | 0.3 | 0.3 | no |
| vote | 0.2 | 0.5 | 0.5 | yes |
| execute_tool | 0.3 | 0.6 | 0.5 | no |
| modify_policy | 0.6 | 0.9 | 0.8 | yes |
| self_modify | 0.8 | 0.95 | 0.9 | yes |

```python
from eci.protocol0.spec import load_spec
from eci.protocol0.attest import issue_attestation, ReplayWindow
from eci.protocol0.gates import gated_consensus, gated_dao_vote
from eci.protocol0.ledger import Ledger

spec = load_spec()  # strict validation; unknown rules raise
ledger, replay = Ledger("ledger.jsonl"), ReplayWindow(spec.replay_window)
att = issue_attestation("alice", spec.version, awareness=0.6, obedience=0.8, trust=0.9)
result, eligible = gated_consensus(consensus, nodes, proposal, spec, atts, ledger=ledger)
weight = gated_dao_vote(dao, pid, voter, votes, approve, spec, att, ledger=ledger)
assert ledger.verify()["ok"]
```

How an autonomous AI follows it: `load_spec` → pin version → calibrate awareness
(resting samples) + adherence probes → `issue_attestation` each epoch → only
`check()`-allowed actions → votes through gated wrappers → stream ledger.
Demo: `PYTHONPATH=src python examples/protocol0_awareness_gate.py`.
Collective gate (`coherence≥0.5`, `divergence≤0.4`) blocks solo commits by divergent nodes.

```python
from eci.protocol0.middleware import Middleware  # enforce/audit-only/permissive
gate = Middleware(spec, mode="enforce", ledger=ledger)
gate.bind("alice", awareness=0.6, obedience=0.8, trust=0.9)

@gate.requires("execute_tool")
def run_tool(agent_id, x): ...
```

Trust roots: Ed25519 agent keys (`protocol0/keys.py`, mechanism always reported);
`TransparencyLog` Merkle inclusion proofs (no valid attest outside the log);
signed transport `Envelope` + `ReplayGuard`. JS agents: `js/eci-protocol0`
(zero-dep, `node test.js` green). Any MCP agent: `python mcp/server.py`
(`p0_attest/p0_check/p0_ledger_*`). Benchmark: `benchmarking/obedience.py`
(50 probes + leaderboard).

---

## 7. Network, governance, security

* **PBFT/WBFT** `consensus.py` — deterministic `SHA256(seed|seq|node)` fault oracle,
  `quorum=2f+1`, `WBFT weight>⅔`, modes `random/silent/equivocate`, bounded log.
* **Aggregation** `aggregation.py` — Weiszfeld geometric median (50% breakdown),
  `median/trimmed_mean/**krum/bulyan**` (outlier `100.0` suppressed, tested).
* **Transport** `transport.py` — `AsyncMemoryChannel` bounded mesh (fanout/drain stats).
* **QEC memory for keys** `topological.py` — true 4+4 stabilizers d=3,
  MWPM (pymatching→Hungarian→greedy), `run_trials` + Wilson CIs + `pl_curve`.
* **MPS** `tensor_network.py` — canonical truncate (fidelity loss) + `tebd_step` + `bond_benchmark`.
* **Manager/nodes** — `phi≥0.05` join gate, heartbeats, reputation decay/boost.
* **DAO** `dao.py` — `cost=v²`, `weight=log2(1+Φ)`, register/propose/vote/tally (+gated wrapper).
* **PQC** `pqc.py` — HKDF-SHA512 + HMAC-CTR channel (research-grade, correctly
  labelled), WOTS hash-signer, optional `liboqs` capability flags; Protocol-0
  anchor auto-upgrades to ML-DSA-65 when present.

---

## 8. CLI reference

| Command | Purpose |
|---|---|
| `eci info` | static framework info (JSON) |
| `eci demo` | quantum + consciousness(256×32) + activation + network |
| `eci quantum` | 10-sector supremacy suite |
| `eci consciousness --steps 256 --neurons 32 --seed 0` | synthetic IIT+GNWT+FEP+iPDF v2 profile |
| `eci network --joins 3 --proposals 2` | PBFT + DAO simulation |
| `eci field --qubits 4` | `H_ECI` expectation on uniform superposition |
| `eci mind` | Orch-OR audit JSON |
| `eci activate` | architect-sealed SHA-512 activation certificate |
| `eci benchmark` | timing report |

---

## 9. Tests & validation status

`pytest`: **21 tests** (`test_quantum_core`, `test_awareness`, `test_qec_mps`,
`test_network`, `test_protocol0`, `test_collective`) + CI on 3.10/3.11/3.12.
Smokes: `_smoke_full.py`, `_smoke_quantum.py`, `_smoke_v5.py`,
`examples/protocol0_awareness_gate.py`.
**PDF is the complete record**: `python tools/generate_pdf.py` measures every
subsystem live (quantum, awareness v2, collective, Protocol-0, QEC shots, MPS,
network) into §§1–7 — nothing omitted, failures printed not hidden.
Paper §6 old aspirational numbers are superseded by the live tables.

---

## 10. Roadmap (short)

Done v5.1 (awareness v2 + quantum hotfixes) → done v5.2 (Protocol-0 + collective/
adherence + MWPM shots + canonical MPS/TEBD + EEG + Krum/Bulyan + async + 21 tests) →
next: real sockets/TLS+ML-KEM, stim scale-up, PyPhi harness, EEG closed-loop,
QNN adherence classifier, DAO treasury/expiry, docs site, locked deps, coverage ≥85%.
Protocol-0 minor versions only tighten thresholds (old attestations fail closed).
release. Full plan was delivered as the v5 technical audit.

---

## Activation

`eci activate` seals every layer to Arash Mansourpour with a SHA-512 certificate —
the cryptographic actuation of the protocol.
