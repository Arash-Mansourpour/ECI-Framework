"""Phase 4 — noise + mitigation for the hybrid inference loop.

1. NOISE (§1): textbook single-qubit depolarizing
       N_q(rho) = (1-q)·rho + q·I/2            (0 <= q <= 1)
   via the existing Kraus ops in ``channels.py`` (their ``p`` parametrize
   rho -> (1-4p/3)rho + (2p/3)I, so we pass p = 3q/4 — stated, not hidden).
   ``apply_depolarizing`` maps the channel over chosen qubits.

2. ZNE (§2): global-folding-EQUIVALENT scaling — scale factor λ means
   λ full rounds of the per-qubit noise channel (λ = 1, 3, 5, matching
   global folding U->U(U'U)^k noise multipliers 1, 3, 5). Chose global
   over local folding: no circuit representation exists at the
   density-matrix level the adapter loop uses, and global folding needs
   none — documented tradeoff is coarser granularity for zero circuit
   surgery. The x-axis IS the noise multiplier, so x=0 is zero noise by
   construction (a scale/rounds mismatch here would halve the gain —
   caught during calibration). Extrapolation is full-order Richardson
   (Lagrange to x=0) with an optional least-squares order.

3. PEC (§3, optional): exact quasiprobability inverse of depolarizing,
       N^{-1} = a·Id + b·(X·X + Y·Y + Z·Z),
       a = 1 + 3q/(4(1-q)),  b = -q/(4(1-q)),
   one-norm gamma = 1 + 3q/(2(1-q)) PER QUBIT; k noisy locations cost
   variance factor gamma^{2k} (shots x~ that for fixed MC error). At the
   density level PEC is exact-in-expectation; cost shows up as Monte
   Carlo standard error, reported, not hidden.
   CONVENTION MAP vs the cited ~(1+2p/(1-p))^{2k} form: ours is exact
   for N_q = (1-q)rho + qI/2, i.e. single-Pauli rate q/4. Under the map
   p_tot = 3q/4 the two closed forms agree within 0.5%
   (q=0.05, k=2: ours 1.35519 vs cited 1.35005) — residual difference is
   convention (exact inverse vs bound-style accounting), not physics.
   Measured stderr follows 1/sqrt(N) exactly (4.035 vs 4.0 over 16x
   shots); the q-scaling carries an O(1) observable-dependent prefactor
   on top of the gamma ratio (measured stderr ratio 1.80 vs naive 1.37
   from q=0.05 to 0.15) — which is why theory states the scaling "up
   to" such prefactors.

4. Scheduler (§4): ``NoisyVQEContributor`` subclasses 2a's
   ``VQEContributor`` (2a untouched) with mode ideal|noisy|zne.
   ZNE mitigates the OBSERVABLE MEANS; the entropy/complexity term uses
   the scale-1 rho unmitigated — stated limitation, not silence.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from typing import Any

import torch

from eci.quantum import channels as qch
from eci.quantum.aikernel_adapter import VQEContributor

__all__ = ["apply_depolarizing", "richardson_extrapolate",
           "lagrange_weights_0", "zne_means", "zne_combine",
           "pec_mitigate", "pec_gamma", "NoisyVQEContributor",
           "ZNE_SCALES"]


ZNE_SCALES = (1, 3, 5)


# ----------------------------------------------------------------------
# 1. Noise
# ----------------------------------------------------------------------
def apply_depolarizing(rho: torch.Tensor, n_qubits: int, q: float,
                       qubits: Sequence[int] | None = None) -> torch.Tensor:
    """Textbook N_q per chosen qubit (default: all), via channels.py Kraus."""
    if not 0.0 <= q <= 1.0:
        raise ValueError("q must be in [0, 1]")
    out = rho
    for qb in (list(qubits) if qubits is not None else list(range(n_qubits))):
        out = qch.apply_channel_on_qubit(out, n_qubits, qb, qch.depolarizing(3 * q / 4))
    return out


# ----------------------------------------------------------------------
# 2. ZNE
# ----------------------------------------------------------------------
def richardson_extrapolate(scales: Sequence[float], values: Sequence[float],
                           order: int | None = None) -> float:
    """Lagrange interpolation to x=0 (full Richardson by default).

    `order`: fit degree-`order` least-squares polynomial instead (needs
    len(scales) > order). Both paths are pure algebra over the inputs.
    """
    import numpy as np
    x = np.asarray(list(scales), dtype=float)
    y = np.asarray(list(values), dtype=float)
    if order is None:
        if len(x) < 2:
            raise ValueError("need >= 2 scale points")
        # Lagrange basis at 0: exact degree-(n-1) interpolant
        total = 0.0
        for i in range(len(x)):
            num, den = 1.0, 1.0
            for j in range(len(x)):
                if i == j:
                    continue
                num *= 0.0 - x[j]
                den *= x[i] - x[j]
            total += y[i] * num / den
        return float(total)
    if len(x) <= order:
        raise ValueError("need more points than order")
    coef = np.polyfit(x, y, order)
    return float(np.polyval(coef, 0.0))


def zne_means(rho_at_scale, labels: Sequence[str], scales: Sequence[int] = (1, 3, 5),
              order: int | None = None) -> dict[str, Any]:
    """Extrapolate each Pauli mean m_k(scale) -> m_k(0).

    REPORTING path: inputs/outputs are plain floats (detached). The
    optimization loop must use ``zne_combine`` instead (same Lagrange
    weights, graph-preserving) — as_tensor() on floats would silently
    cut autograd (caught during calibration: near-zero ZNE gradients).
    """
    from eci.aikernel.functors import pauli_string_matrix
    per_scale: list[list[float]] = []
    for lam in scales:
        rho = rho_at_scale(lam)
        nq = int(round(math.log2(rho.size(-1))))
        per_scale.append([float(torch.trace(rho @ pauli_string_matrix(l, nq)).real.item())
                          for l in labels])
    mit = [richardson_extrapolate(list(scales), [per_scale[s][k] for s in range(len(scales))],
                                  order=order)
           for k in range(len(labels))]
    return {"mitigated": mit, "per_scale": per_scale, "scales": list(scales)}


def lagrange_weights_0(scales: Sequence[float]) -> list[float]:
    """Richardson weights: m(0) = sum_k w_k·m(x_k). Pure algebra."""
    x = list(scales)
    w = []
    for i in range(len(x)):
        num, den = 1.0, 1.0
        for j in range(len(x)):
            if i == j:
                continue
            num *= 0.0 - x[j]
            den *= x[i] - x[j]
        w.append(num / den)
    return w


def zne_combine(scale_means: Sequence[torch.Tensor],
                scales: Sequence[float] = (1, 3, 5)) -> torch.Tensor:
    """Graph-preserving Richardson combination (optimization path).

    ``scale_means[s]`` = attached mean vector at scales[s]; returns the
    extrapolated vector with grad intact. Tested equal to
    ``richardson_extrapolate`` on detached values.
    """
    w = torch.as_tensor(lagrange_weights_0(scales), dtype=torch.float32)
    stacked = torch.stack([torch.as_tensor(m, dtype=torch.float32).reshape(-1)
                           for m in scale_means], dim=0)
    return (w.unsqueeze(1) * stacked).sum(0)


# ----------------------------------------------------------------------
# 3. PEC (depolarizing only, exact-in-expectation at density level)
# ----------------------------------------------------------------------
def pec_gamma(q: float, n_locations: int = 1) -> float:
    """Variance factor gamma^{2k}: per-qubit gamma = 1 + 3q/(2(1-q))."""
    if not 0.0 <= q < 1.0:
        raise ValueError("need 0 <= q < 1 (inverse singular at q=1)")
    return (1.0 + 1.5 * q / (1.0 - q)) ** (2 * n_locations)


def pec_mitigate(rho_noisy: torch.Tensor, observable: torch.Tensor, q: float,
                 n_samples: int = 2048, seed: int = 0) -> dict[str, Any]:
    """Sample the quasiprobability inverse of per-state depolarizing.

    Draws Pauli-twirls with probability |c|/gamma, accumulates
    sign·gamma·Tr[O·twirl(rho)]; mean == Tr[O·rho_ideal] in expectation.
    """
    g = random.Random(seed)
    D = rho_noisy.size(0)
    nq = int(round(math.log2(D)))
    a = 1.0 + 0.75 * q / (1.0 - q)
    b = -0.25 * q / (1.0 - q)
    ops = [(a, None)] + [(b, P) for P in ("X", "Y", "Z")]
    from eci.aikernel.functors import pauli_string_matrix
    gamma1 = abs(a) + 3 * abs(b)
    acc, acc2 = 0.0, 0.0
    for _ in range(n_samples):
        sign_total, twirled, gtot = 1.0, rho_noisy, 1.0
        for _qb in range(nq):
            r = g.random() * gamma1
            run = 0.0
            for coeff, P in ops:
                run += abs(coeff)
                if r <= run:
                    c = coeff
                    break
            sign_total *= 1.0 if c > 0 else -1.0
            gtot *= gamma1
            if P is not None:
                U = pauli_string_matrix(f"{P}{_qb}", nq).to(rho_noisy.dtype)
                twirled = U @ twirled @ U.conj().T
        val = sign_total * gtot * float(torch.trace(twirled @ observable).real.item())
        acc += val
        acc2 += val * val
    mean = acc / n_samples
    var = max(0.0, acc2 / n_samples - mean * mean)
    return {"mitigated": mean, "stderr": math.sqrt(var / n_samples),
            "n_samples": n_samples, "gamma_total": gamma1 ** nq,
            "variance_factor": pec_gamma(q, nq)}


# ----------------------------------------------------------------------
# 4. Hybrid scheduler (2a untouched: subclass, additive kwargs only)
# ----------------------------------------------------------------------
class NoisyVQEContributor(VQEContributor):
    """VQEContributor routable through ideal | noisy | zne paths.

    - ideal: parent behavior bit-for-bit (same code path).
    - noisy: loss evaluated on N_q(ρ) with the declared q.
    - zne:   Pauli means extrapolated from scales (1,3,5) back to zero
             noise; inaccuracy rebuilt from mitigated means; complexity
             uses the scale-1 rho UNMITIGATED (stated limit — entropy has
             no observable-mean representation to extrapolate).
    Energy tracking follows the same routing (mitigated linear-combo
    energy under zne), so F/energy trajectories compare fairly.
    """

    def __init__(self, *args: Any, mode: str = "ideal", noise_q: float = 0.02,
                 zne_scales: Sequence[int] = ZNE_SCALES, **kwargs: Any) -> None:
        if mode not in ("ideal", "noisy", "zne"):
            raise ValueError(f"unknown mode {mode!r}")
        super().__init__(*args, **kwargs)
        self.mode = mode
        self.noise_q = noise_q
        self.zne_scales = tuple(zne_scales)
        self._last_emit: float | None = None

    def _rho_at_scale(self, rho_ideal: torch.Tensor, scale: int) -> torch.Tensor:
        out = rho_ideal
        for _ in range(max(1, int(scale))):
            out = apply_depolarizing(out, self.n_qubits, self.noise_q)
        return out

    def loss_parts(self) -> dict[str, torch.Tensor]:
        if self.mode == "ideal":
            return super().loss_parts()
        from eci.aikernel.free_energy import quantum_free_energy
        rho_ideal = self._rho if self._rho is not None else self._forward()
        if self.mode == "noisy":
            rho = self._rho_at_scale(rho_ideal, 1)
            parts = quantum_free_energy(rho, self.obs_labels, self.obs_target, self.R)
            c = torch.as_tensor([float(t.coeff) for t in self.hamiltonian.terms])
            self._last_emit = float((c * parts["mean"].detach()).sum().item())
            return parts
        # zne: extrapolate means, rebuild inaccuracy, keep scale-1 complexity
        from eci.aikernel.functors import pauli_string_matrix
        base = quantum_free_energy(self._rho_at_scale(rho_ideal, 1),
                                   self.obs_labels, self.obs_target, self.R)
        attached = []
        for lam in self.zne_scales:
            rho_l = self._rho_at_scale(rho_ideal, lam)
            attached.append(torch.stack([
                torch.trace(rho_l @ pauli_string_matrix(lab, self.n_qubits)
                            .to(rho_l.dtype)).real for lab in self.obs_labels]))
        m_mit = zne_combine(attached, list(self.zne_scales)).to(torch.float32)
        Rinv = torch.linalg.inv(self.R)
        resid = self.obs_target - m_mit
        inacc = 0.5 * (resid @ Rinv @ resid)
        # mitigated energy stashed HERE (pre-update, same forward as loss)
        c = torch.as_tensor([float(t.coeff) for t in self.hamiltonian.terms])
        self._last_emit = float((c * m_mit).sum().item())
        return {"complexity": base["complexity"], "inaccuracy": inacc,
                "total": base["complexity"] + inacc, "mean": m_mit}

    def step(self) -> dict[str, float]:
        out = super().step()
        if self.mode != "ideal" and self._last_emit is not None:
            self.e_history[-1] = self._last_emit
            out["energy"] = self._last_emit
        return out
