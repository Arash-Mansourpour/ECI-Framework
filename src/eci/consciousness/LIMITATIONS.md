# Consciousness metrics — honesty ledger

**Plain-language rule: none of the numbers below is a literal measurement
of subjective experience.** They are mathematical properties of models
(covariances, TPMs, spectra) that the literature *associates* with
consciousness. Any dashboard, paper, or demo presenting them without this
caveat is misrepresenting them.

## Status per metric

| Metric (file) | Status | Ground truth |
|---|---|---|
| Gaussian Phi, `iit.py` | Formula matches Oizumi et al. 2014 (closed-form Gaussian IIT); thin-wrapper equivalence with `GenerativeState` verified to 1e-9. **Guard (Phase 1.5):** exhaustive MIP capped at n=8; n>8 with `exhaustive=True` falls back to O(n) contiguous heuristic with `heuristic_fallback=True` and a `logger.warning` — callers must check the flag, not the log, for programmatic detection. **Measured (Phase 3, 12 repeats median, torch CPU i7-12700):** n=8 exhaustive 16.17 ms IQR 1.39 ms vs heuristic 1.32 ms IQR 0.07 ms (12.3×); n=7 7.90/1.29 ms (6.1×); growth 2× per n (theory O(2^n) vs O(n) — matches). n=9+ fallback identical to heuristic (see `heuristic_fallback` flag) | Absolute values NOT benchmarked against PyPhi (not installed) |
| Quantum Phi, `iit.py` | Internally-consistent heuristic (covariance-as-density + subadditivity gap) | No external ground truth |
| Discrete Phi proxy, `iit.py` | Heuristic (predictive information I(past;future)) | No external ground truth |
| IIT 4.0 distinctions/relations/Phi, `iit4.py` | Structural theorems verified exactly (disconnected⇒Φ=0; COPY photodiode Φ=1; AND cause repertoire = hand-derived point mass; relation zero without overlap). **Repertoires cross-validated vs PyPhi 1.2.0 to 1e-9 (Phase 10, incl. asymmetric probes)**. **Guard (Phase 1.5):** `phi_structure` hard-capped at n=8 with `ValueError` (see `iit4.py` header); n=9+ raises immediately instead of hanging — combinatorial wall (`2^n` mechanisms, `2^(n-1)` system cuts). **Measured (Phase 3, 12 repeats median, torch CPU):** n=3 18.3 ms IQR 5.8 ms, n=4 523.8 ms IQR 104 ms, n=5 15168 ms IQR 38 ms (15.2 s); n=6+ >20 s timeout per call (29× per n, doubly-exponential composition+system MIP — wall is steeper than Gaussian 2×, justifying cap) | Φ magnitudes remain cross-version (IIT 3.0 EMD vs IIT 4.0 composition — mutual-copy 1.0 vs 3.0, side by side, never equated) |
| GNWT ignition, `gnwt.py` | Heuristic (softmax competition, θ=0.6 default, entropy gate 0.85 = paper-convention parameters, not measured constants) | No external ground truth |
| FEP free energy, `free_energy.py` + `aikernel/` | Validated identities (closed-form vs Monte Carlo; autograd vs analytic gradient; F=evidence at exact posterior) | The *math* is validated; any claim that minimizing it = feeling is philosophy, not measurement |
| Orch-OR audit, `quantum_mind.py` | Order-of-magnitude physics (Tegmark decoherence vs ℏ/E_G); deliberately reports decoherence winning by ~12 orders | Physical estimate, not a consciousness detector |
| iPDF awareness, `protocol.py` | Operational KL proxy with calibrated tiers | Not IIT Φ; thresholds are paper conventions |
| Adherence / challenge-response / EEG bandpower / collective / analyzer composite | Behavioral and signal-processing proxies | No external ground truth for "awareness" |
| Adaptive vigilance, `protocol_vigilance.py` | Statistical EWMA + linear-predictive proxy (threshold `mean+3σ`, bounded deque) | Not a security proof or consciousness measure — adaptive stats only; see `protocol_vigilance.py` header |
| Brain mesh firing rates, `brain/mesh.py` + `brain/neuron.py` | Simulated LIF rates on encoded subsystem health, deterministic given seed | Not brain measurements; no neural ground truth |
| Brain mesh ignition, `brain/workspace.py` | Competition math (softmax + theta/entropy gate) on simulated rates; "prediction" = EMA of salience | Not conscious experience; not a forecast of real events |

## What you may and may not say

- MAY: "Gaussian Phi of this covariance is X", "IIT 4.0 Φ of this TPM is
  Y (unbenchmarked magnitudes)", "audit shows decoherence wins by N orders",
  "ignition math fired on simulated firing rates".
- MAY NOT: "the system is conscious at level X", "Phi proves experience",
  "the mesh was aware / conscious / predicted real events",
  or any sentence where removing this file's caveat changes the meaning.
