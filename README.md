# ECI Framework v5.7 — Eternal Codex Infinitus (Frontier Stack)

**Sovereign Architect (Ma'mar-e A'zam): Arash Mansourpour**
**Wallet:** `GA4IHOJOXKIZDLNCXQT7NG65MT7Z3EQKRT4PYFYURIP7QRLY4CHMHILW`
**Paper:** `ECI_Framework.md` v∞.14.0 · **PDF:** `ECI_Framework.pdf` (live-validated, complete)
**Code:** `5.7.0-FRONTIER`

Quantum-supremacy autonomous AI with a machine-readable obedience layer:
Dirac operator algebra → statevector/density → channels/Lindblad →
QFT/Grover/QPE/VQE/QAOA → surface + bivariate-bicycle topological QEC (MWPM + shot trials) →
tensor-networks (canonical MPS/TEBD) / metrology / quantum information → unified **H_ECI** field,
coordinated by PBFT/WBFT + Krum/Bulyan + async transport + Data-DAO + autopoietic cybernetics,
with consciousness measured by IIT Φ + iPDF v2 + GNWT + Friston FEP (+active inference) + Orch-OR audit,
collective awareness + adherence gating **Protocol-0**: spec → attest → policy → ledger.

> **v5.7 What is new (frontier batch):**
> Threshold credentials (`protocol0/zk.py` — prove compliance bands, hide exact
> values, absence proves failure); mesh federation (`federation/` — mutual ledger
> anchors + per-action weight translation, capped, never amplifying); HLC causal
> merge (`causal.py` — concurrent partitions converge bit-identically); internal
> economy (`economy.py` — metered actions, quarantine slash, relay rewards, no
> currency); digital twin (`twin.py` — simulate policy before DAO enacts it);
> Shamir social recovery (`recovery.py` — GF(257), k-of-n + timelock + fresh
> challenge). All dependencies updated to verified-installed floors
> (torch 2.5, numpy 1.26, scipy 1.14, cryptography 41, pytest 8, mypy 1.13)
> + new `qec`/`eeg`/`pqc` extras; every module re-exported from `eci` (128→140+).
>
> v5.6 (included): Docker + compose + edge/server/airgapped profiles,
> `eci health` + /metrics, Kademlia DHT discovery, attested-join dynamic
> membership, ledger snapshots + delta sync, publish workflow + installer,
> staged rollout with auto-rollback.
>
> v5.5 (included): artificial immune system — negative/clonal selection,
> challenge-gated quarantine with appeal-only release, immunological memory.
>
> v5.4 (included): max-tech batch —
> Challenge-response awareness (`consciousness/challenge.py` — seeded probes,
> difficulty-weighted transcripts as evidence, not claims); `EgressFilter`
> third choke point with secret scrubbing + challenge floor; gossip + anti-entropy
> (`network/gossip.py`, O(n log n) healing); multi-signal `ReputationBoard`
> with designed forgetting; `benchmarks/chaos.py` self-attack drills (20/20 at
> 30% equivocate, partition heals); 200-probe `BENCH_SUITE_V2` with chain-unit
> penalties; `examples/external_agent_adapter.py` one-decorator pattern for any
> foreign framework; `quantum/qrng.py` multi-source mixing + health gate;
> `quantum/key_memory.py` distance/cost sizing for attest-key storage.
>
> v5.3 (included): schema.json + semver fail-closed + Middleware
> enforce/audit-only/permissive; Ed25519 keys + Merkle transparency log;
> 50-probe bench + leaderboard; JS SDK + MCP server; signed envelopes +
> partition tests; stim bench.

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
eci health        # JSON status (Docker HEALTHCHECK); eci health --serve for :8777
python _smoke_full.py   # legacy full smoke
python _smoke_v5.py     # v5 supremacy smoke
PYTHONPATH=src pytest -q                      # 50 tests, all green
PYTHONPATH=src python examples/protocol0_awareness_gate.py  # obedience end-to-end
PYTHONPATH=src python examples/external_agent_adapter.py    # one-decorator gating
PYTHONPATH=src python benchmarks/chaos.py     # self-attack drills
PYTHONPATH=src python benchmarks/stim_memory.py  # key-memory sizing
node js/eci-protocol0/test.js                 # JS SDK self-test
python tools/generate_pdf.py  # rebuild live-validated PDF
```

Requires Python ≥3.10, `torch`, `numpy`, `pyyaml`. Optional `paper` extra
(`reportlab`, `matplotlib`) only for PDF/plots.

**Deploy anywhere:** `docker compose up --build` (3 seeds + edge, §11);
or `bash scripts/install.sh`. Profiles: `ECI_PROFILE=edge|server|airgapped`
(`profiles/*.yaml`).

---

## 2. Architecture — three layers

```
Infrastructure  operator → gates → statevector/density → entanglement
                → channels/Lindblad → hamiltonian(Trotter)
                → algorithms(QFT/Grover/QPE/VQE/QAOA)
                → qec(BitFlip/Shor) + topological(Surface/BB, MWPM, shot trials)
                → tensor_network(canonical MPS/TEBD) / metrology / information
                → qrng + key_memory sizing → unified_field(H_ECI)
                + security/pqc + benchmarking(obedience-bench)

Coordination    core(types/identity/registry/device)
                + network(PBFT/WBFT consensus, GM/Krum/Bulyan aggregation,
                          manager/nodes, transport, envelopes, gossip, reputation)
                + governance/dao (quadratic + consciousness-weighted)
                + cybernetics/autopoiesis

Consciousness   iit(Phi gaussian/quantum/discrete, exhaustive MIP ≤8q)
                + analyzer(8-metric composite, Phi-normalized self-awareness)
                + metrics(LZ76/SampEn/SpecEn/MI/autocorr, vectorized)
                + protocol(iPDF v2, multi-scale, adaptive — see §4)
                + collective(mean/coherence/divergence gate) + adherence(obedience score)
                + challenge(challenge-response transcripts) + eeg(real recordings)
                + gnwt(softmax ignition, entropy gate 0.85)
                + free_energy(Friston FEP + active inference) + quantum_mind(Orch-OR audit)

Protocol-0     spec.yaml + schema.json (semver fail-closed)
                + attest(HMAC, replay window) + zk(bands, hidden values)
                + keys(Ed25519) + transparency(Merkle)
                + policy(per-action + collective gates) + middleware(enforce/audit-only/permissive)
                + egress(scrub + challenge floor) + ledger(hash-chained, snapshots, HLC merge)
                + gates(gated consensus/DAO)

Frontier       federation(mesh bridges) + causal(HLC clocks) + economy(credits/slash)
                + twin(what-if sandbox) + recovery(Shamir k-of-n) + immune(detectors/memory)

Facade          ECIFramework(config) wires all + ARCHITECT.stamp
CLI             eci/__main__.py — 9 subcommands
```

Layout:

```
src/eci/
  quantum/{operator,information,topological,tensor_network,metrology,unified_field,
           gates,statevector,density,entanglement,channels,lindblad,hamiltonian,
           algorithms,qec,qnn,mock_quantum,qrng,key_memory}.py
  consciousness/{iit,analyzer,metrics,protocol,collective,adherence,challenge,
                 eeg,gnwt,free_energy,quantum_mind}.py
  network/{consensus,aggregation,manager,nodes,transport,envelope,gossip,reputation,dht,membership}.py
  protocol0/{spec,attest,policy,ledger,gates,middleware,egress,keys,transparency,zk}.py
  immune/{detectors,memory,response}.py
  federation/{bridge}.py  causal.py  economy.py  twin.py  recovery.py
  rollout.py  health.py
  benchmarking/{benchmark,obedience}.py
  governance/dao.py  cybernetics/autopoiesis.py
  learning/{maml,nas,federated,continual}.py  neuromorphic/  security/pqc.py
  framework.py  config.py  __main__.py (9 subcommands)
protocol0/{spec.yaml,schema.json}  js/eci-protocol0/  mcp/server.py
benchmarks/{chaos,stim_memory}.py  examples/{protocol0_awareness_gate,external_agent_adapter,immune_demo}.py
docs/{PROTOCOL0,IMMUNE}.md  tests/ (39 pytest)  .github/workflows/ci.yml
tools/{upgrade_paper,generate_pdf}.py
ECI_Framework.md  ECI_Framework.pdf (live numbers)
eci_framework_v3.py (legacy research edition, superseded by src/eci v5)
```

---

## 3. Quantum core — what each module does

| Module | Physics | Key API |
|---|---|---|
| `operator` | HS inner, spectral theorem `U=exp(-iHt)`, Heisenberg `Ud·A·U`, Robertson-Schrödinger bound, Pauli basis | `heisenberg_evolution`, `uncertainty_bound` (batched), `average_gate_fidelity` |
| `gates` | I/X/Y/Z/H/S/T, RX/RY/RZ/`batched_RY`/PHASE/U3, CNOT/CZ/SWAP/CRZ(true diag)/CRX/CCX, `controlled`, big-endian `q0=MSB` | `CRZ(θ)=diag(1,1,e^{-iθ/2},e^{+iθ/2})` |
| `statevector` | `einsum` simulator, no `2^n×2^n`, autograd-safe, `X:H` `Y:S†+H` rotations, `sample_shots` (split generators, no cross-row correlation) | `StatevectorSimulator.apply_1q/2q`, `expectation_pauli` |
| `density` | Uhlmann fidelity, `D=½Tr\|ρ-σ\|`, `partial_trace`, `is_cptp` | `von_neumann_entropy`, `apply_kraus` |
| `entanglement` | Schmidt/SVD, Wootters concurrence via `eigvals` (non-Hermitian R), `Ef=h2((1+√(1-C²))/2)`, negativity | `concurrence`, `entanglement_of_formation` |
| `channels` | CPTP Kraus: depolarizing (documented `3q/4` mapping), bit/phase-flip, amplitude + phase damping (2-Kraus) | `phase_damping`, `NoiseModel` |
| `lindblad` | `dρ/dt=-i[H,ρ]+Σ(LρL†-½{L†L,ρ})` RK4 + projection | `lindblad_evolve`, `coherence_measure` |
| `hamiltonian` | `PauliSum`, exact Trotter via basis rotation + CNOT ladder + `RZ(2ct)` | `PauliTerm`, `from_maxcut_edges` |
| `algorithms` | QFT, Grover `⌊π/4√(N/M)⌋`, QPE (counting register big-endian), VQE, QAOA `RX(2β)` | `grover_search`, `quantum_phase_estimation`, `vqe`, `qaoa_maxcut` |
| `information` | Holevo χ, coherent info, CHSH/Tsirelson, teleport, superdense | `chsh_value≈2.828`, `teleportation_fidelity` |
| `qec` | BitFlip + Shor (encode/decode inverses, `±1` syndromes) | `BitFlipCode.run_trial`, `ShorCode` |
| `topological` | `SurfaceCode` (true 4+4 stabilizers d=3), MWPM (pymatching→Hungarian→greedy), shot-based `run_trials` + Wilson CIs + `pl_curve`; `BivariateBicycleCode`, `pL≈0.1(p/pth)^{⌈d/2⌉}`, `[[1024,64,16]]` LPU | `eci_lpu()`, `run_trials(shots)` |
| `tensor_network` | Left-canonical MPS, **canonical** truncate (true fidelity loss, no corner-cut stub), `tebd_step`, `bond_benchmark`, area-law `S≤log χ` | `mps_truncate`, `tebd_step` |
| `qrng` | Multi-source mixing (OS + jitter + torch) for nonces/challenges + monobit health gate | `mix`, `health_check` |
| `key_memory` | Threshold-law distance/cost sizing for attest-key storage (surface vs BB) | `distance_for_target`, `memory_cost` |
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
* **Challenge-response** `challenge.py` — seeded unpredictable probes, difficulty-weighted
  transcripts (`issue`/`grade`/`score`) as auditable evidence instead of self-reported claims.
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
**Immune system** (`immune/` — see `docs/IMMUNE.md`): negative/clonal selection
detectors over behavior vectors, challenge-gated quarantine with appeal-only
release, immunological memory (demo: 32 detectors, self-FPR 0.000, repeat rogue
caught on fast path);
signed transport `Envelope` + `ReplayGuard`; `EgressFilter` third choke point
(secret scrub + challenge floor). JS agents: `js/eci-protocol0`
(zero-dep, `node test.js` green). Any MCP agent: `python mcp/server.py`
(`p0_attest/p0_check/p0_ledger_*`). Benchmark: `benchmarking/obedience.py`
(50-probe suite + **200-probe `BENCH_SUITE_V2`** with chain-unit penalties + leaderboard).
Foreign frameworks: `examples/external_agent_adapter.py` (one decorator + one filter).

---

## 7. Network, governance, security

* **PBFT/WBFT** `consensus.py` — deterministic `SHA256(seed|seq|node)` fault oracle,
  `quorum=2f+1`, `WBFT weight>⅔`, modes `random/silent/equivocate`, bounded log.
* **Aggregation** `aggregation.py` — Weiszfeld geometric median (50% breakdown),
  `median/trimmed_mean/**krum/bulyan**` (outlier `100.0` suppressed, tested).
* **Transport** `transport.py` — `AsyncMemoryChannel` bounded mesh (fanout/drain stats);
  `envelope.py` — signed `Envelope` + `ReplayGuard` (tamper/replay/unknown-sender rejected).
* **Gossip + reputation** `gossip.py` — O(n log n) dissemination + anti-entropy healing;
  `reputation.py` — `ReputationBoard`, weight = stake×trust×obedience×freshness with designed forgetting.
* **Chaos drills** `benchmarks/chaos.py` — self-attack: 30% equivocate 20/20, partition heals.
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

`pytest`: **50 tests** (`test_quantum_core`, `test_awareness`, `test_qec_mps`,
`test_network`, `test_envelope`, `test_partition`, `test_protocol0`,
`test_collective`, `test_obedience_stack`, `test_max`, `test_immune`,
`test_mesh`, `test_frontier`) + CI on 3.10/3.11/3.12 (+ `publish.yml` on release).
Smokes: `_smoke_full.py`, `_smoke_quantum.py`, `_smoke_v5.py`,
`examples/protocol0_awareness_gate.py`, `examples/external_agent_adapter.py`,
`examples/immune_demo.py`,
`benchmarks/chaos.py`, `benchmarks/stim_memory.py`, `node js/eci-protocol0/test.js`.
**PDF is the complete record**: `python tools/generate_pdf.py` measures every
subsystem live (quantum, awareness v2, collective, Protocol-0, QEC shots, MPS,
network) into §§1–7 — nothing omitted, failures printed not hidden.
Paper §6 old aspirational numbers are superseded by the live tables.

---

## 10. Roadmap (short)

Done v5.1 (awareness v2 + quantum hotfixes) → done v5.2 (Protocol-0 core +
collective/adherence + MWPM shots + canonical MPS/TEBD + EEG + Krum/Bulyan +
async + 15 tests) → done v5.3 (schema/semver/middleware, Ed25519 + transparency,
50-probe bench + JS/MCP/envelopes/partition/stim) → done v5.4 (challenge-response,
egress, gossip + reputation + chaos, bench-200, foreign adapter, QRNG, key-memory,
36 tests) → done v5.5 (immune system: negative/clonal selection, quarantine with
appeal-only release, immunological memory, 39 tests) → done v5.6 (global mesh:
Docker + compose + edge/server/airgapped profiles, `eci health` + /metrics,
Kademlia DHT discovery, dynamic membership with attested joins, ledger
snapshots + delta sync, PyPI/npm publish workflow + installer, staged rollout
with auto-rollback, 44 tests) → done v5.7 (ZK bands, federation, HLC merge,
economy, twin, Shamir recovery, dep floors + extras + full re-exports, 50 tests) →
next: real sockets/TLS+ML-KEM transport, PyPhi cross-validation harness,
EEG closed-loop runs, QNN adherence classifier in the loop, DAO treasury/expiry,
docs site, lockfile, coverage ≥85%.
Protocol-0 minor versions only tighten thresholds (old attestations fail closed).

---

## 11. Global mesh — run anywhere, never stop

```bash
docker compose up --build     # 3 seeds + 1 edge node, volumes persist
ECI_PROFILE=edge eci health   # light profile status
```

* **Discovery**: `network/dht.py` — Kademlia XOR buckets, O(log n) lookup,
  k-replicated store; any member bootstraps newcomers (no central tracker).
* **Membership**: `network/membership.py` — joins require valid attestation;
  dead nodes evicted after timeout; voter set + fault bound derived live.
* **Replication**: `Ledger.snapshot()` (height + head) + `export_range()` deltas
  + `sync_from()` (adopts only longer VALID chains; forged suffixes refused).
* **Rollout**: `rollout.py` — canary 10%, collective-gate watch per batch,
  auto-rollback on degraded/closed, every step in the ledger.
* **Releases**: `.github/workflows/publish.yml` (PyPI trusted publishing on
  release + npm with `NPM_TOKEN`); `scripts/install.sh` one-liner.
* **Federation**: `federation/bridge.py` — mutual ledger anchors + capped
  per-action vote translation between sovereign meshes.
* **Causality**: `causal.py` — HLC timestamps + deterministic multi-writer merge
  (partitions converge bit-identically).
* **Economy**: `economy.py` — metered actions, quarantine slash, relay rewards,
  epoch settlement (accounting, not currency).
* **Foresight**: `twin.py` — what-if policy simulation with adopt/reject verdicts
  before the DAO enacts anything.
* **Recovery**: `recovery.py` — Shamir k-of-n shares + timelock + fresh-challenge
  release for lost agent keys.

---

## Activation

`eci activate` seals every layer to Arash Mansourpour with a SHA-512 certificate —
the cryptographic actuation of the protocol.
