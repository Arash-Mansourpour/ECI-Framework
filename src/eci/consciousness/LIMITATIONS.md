# Consciousness metrics — honesty ledger

**Plain-language rule: none of the numbers below is a literal measurement
of subjective experience.** They are mathematical properties of models
(covariances, TPMs, spectra) that the literature *associates* with
consciousness. Any dashboard, paper, or demo presenting them without this
caveat is misrepresenting them.

## Status per metric

| Metric (file) | Status | Ground truth |
|---|---|---|
| Gaussian Phi, `iit.py` | Formula matches Oizumi et al. 2014 (closed-form Gaussian IIT); thin-wrapper equivalence with `GenerativeState` verified to 1e-9 | Absolute values NOT benchmarked against PyPhi (not installed) |
| Quantum Phi, `iit.py` | Internally-consistent heuristic (covariance-as-density + subadditivity gap) | No external ground truth |
| Discrete Phi proxy, `iit.py` | Heuristic (predictive information I(past;future)) | No external ground truth |
| IIT 4.0 distinctions/relations/Phi, `iit4.py` | Structural theorems verified exactly (disconnected⇒Φ=0; COPY photodiode Φ=1; AND cause repertoire = hand-derived point mass; relation zero without overlap). **Repertoires cross-validated vs PyPhi 1.2.0 to 1e-9 (Phase 10, incl. asymmetric probes)** | Φ magnitudes remain cross-version (IIT 3.0 EMD vs IIT 4.0 composition — mutual-copy 1.0 vs 3.0, side by side, never equated) |
| GNWT ignition, `gnwt.py` | Heuristic (softmax competition, θ=0.6 default, entropy gate 0.85 = paper-convention parameters, not measured constants) | No external ground truth |
| FEP free energy, `free_energy.py` + `aikernel/` | Validated identities (closed-form vs Monte Carlo; autograd vs analytic gradient; F=evidence at exact posterior) | The *math* is validated; any claim that minimizing it = feeling is philosophy, not measurement |
| Orch-OR audit, `quantum_mind.py` | Order-of-magnitude physics (Tegmark decoherence vs ℏ/E_G); deliberately reports decoherence winning by ~12 orders | Physical estimate, not a consciousness detector |
| iPDF awareness, `protocol.py` | Operational KL proxy with calibrated tiers | Not IIT Φ; thresholds are paper conventions |
| Adherence / challenge-response / EEG bandpower / collective / analyzer composite | Behavioral and signal-processing proxies | No external ground truth for "awareness" |

## What you may and may not say

- MAY: "Gaussian Phi of this covariance is X", "IIT 4.0 Φ of this TPM is
  Y (unbenchmarked magnitudes)", "audit shows decoherence wins by N orders".
- MAY NOT: "the system is conscious at level X", "Phi proves experience",
  or any sentence where removing this file's caveat changes the meaning.
