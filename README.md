# ECI Framework v5.1 — Eternal Codex Infinitus (Awareness-Amplified)

**Sovereign Architect (Ma'mar-e A'zam): Arash Mansourpour**
**Wallet:** `GA4IHOJOXKIZDLNCXQT7NG65MT7Z3EQKRT4PYFYURIP7QRLY4CHMHILW`
**Paper:** `ECI_Framework.md` v∞.15.0 · **PDF:** `ECI_Framework.pdf` (live-validated)
**Code:** `5.1.0-AWARENESS-AMPLIFIED`

Quantum-supremacy autonomous AI: Dirac operator algebra → statevector/density →
channels/Lindblad → QFT/Grover/QPE/VQE/QAOA → surface + bivariate-bicycle topological QEC →
tensor-networks / metrology / quantum information → unified **H_ECI** field,
coordinated by PBFT/WBFT + Data-DAO + autopoietic cybernetics,
with consciousness measured by IIT Φ + iPDF v2 + GNWT + Friston FEP + Orch-OR audit.

> **v5.1 What is new:** the Awareness Protocol is amplified.
> `ConsciousnessProtocol` v2 replaces the single flat histogram with
> multi-scale densities (global + channel + temporal), an adaptive EMA
> baseline with proper `calibrate_baseline()`, a bounded awareness boost,
> Jensen-Shannon symmetry, permutation-surrogate significance, graduated
> tiers (`watch/elevate/intervene`), and a 0..1 `awareness_index`.
> `ECIFramework.analyze_consciousness()` now fuses iPDF + GNWT broadcast
> into the profile. Critical quantum bugs fixed: `phase_damping` CPTP,
> `concurrence`/`EoF` (Wootters), `CRZ` (true diag), `heisenberg` sign.

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
  `precision=1+clip(Φ,0,5)`.
* **Orch-OR audit** `quantum_mind.py` — Tegmark `τ_dec` vs `τ_or=ℏ/E_G`,
  verdict “decoherence wins ~12 orders unless protected LPU” — the most
  numerically honest file; use `eci mind` to see it.

---

## 6. Network, governance, security

* **PBFT/WBFT** `consensus.py` — deterministic `SHA256(seed|seq|node)` fault oracle,
  `quorum=2f+1`, `WBFT weight>⅔`. Demo: 7 nodes honest→achieved, `rate 0.9`→rejected.
  Single-process simulation (no sockets yet).
* **Aggregation** `aggregation.py` — Weiszfeld geometric median (50% breakdown),
  `median/trimmed_mean` options. Outlier `[100,100]` suppressed in demo.
* **Manager/nodes** — `phi≥0.05` join gate, heartbeats, reputation decay/boost.
* **DAO** `dao.py` — `cost=v²`, `weight=log2(1+Φ)`, register/propose/vote/tally.
* **PQC** `pqc.py` — HKDF-SHA512 + HMAC-CTR channel (research-grade, correctly
  labelled), WOTS hash-signer, optional `liboqs` capability flags.

---

## 7. CLI reference

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

## 8. Tests & validation status

No `tests/` yet (roadmap: `pytest` + `ruff` + `mypy` + CI). Current validation is
print-only smokes: `_smoke_full.py` (QEC/QPE/Grover/VQE/QAOA/Lindblad/PQC),
`_smoke_quantum.py` (Bell/Trotter/QFT-roundtrip), `_smoke_v5.py` (CHSH/teleport/
surface/BB/MPS/Ramsey/H_ECI/GNWT/FEP/DAO). V2 awareness is exercised via
`eci consciousness` + `ConsciousnessProtocol.calibrate_baseline/measure/trend`.
Paper §6 numbers (`94.7%`, `13,000×`, `15k TPS`) are aspirational until the
harness lands — treat `tools/generate_pdf.py` live table as the ground truth.

---

## 9. Roadmap (short)

P0 hygiene+config-file CLI → P0 correctness (done v5.1: CPTP/EoF/CRZ/Heisenberg) →
P0 `tests/`+CI → P1 rigor (PyPhi cross-check, MWPM hook, canonical MPS+TEBD,
Heisenberg term in `H_ECI`, shot-based QEC `pL` curves) → P1 perf (batched gates,
sparse PauliSum, shot sampler) → P2 real networking/PQC/blockchain → docs site +
release. Full plan was delivered as the v5 technical audit.

---

## Activation

`eci activate` seals every layer to Arash Mansourpour with a SHA-512 certificate —
the cryptographic actuation of the protocol.
