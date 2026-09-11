"""Integrated Information Theory (IIT) - gaussian, quantum and discrete Phi.

References
----------
* Oizumi, Albantakis, Tononi (2014) "From the Phenomenology to the
  Mechanisms of Consciousness" PLoS Comput Biol - gaussian Phi.
* Tononi et al. (2016) Nat Rev Neurosci - IIT framework.
* The ``quantum`` method links to the quantum core: the normalized
  covariance matrix is treated as a density matrix and Phi is computed
  from von Neumann entropies of the whole system vs. bipartitions.

Unification note (AIK Phase 2b): ``calculate_phi`` accepts an opt-in
``state: GenerativeState``. Both the raw-tensor path and the state path
funnel into the same covariance-core helpers, so the state path is a
*thin, exact* wrapper (no resampling noise in the Phi value itself).
See ``consciousness/LIMITATIONS.md`` for what Phi is and is not.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import torch

from eci.constants import COVARIANCE_REGULARIZER, EPS
from eci.core.device import get_device
from eci.logging import get_logger
from eci.quantum import density as qd

if TYPE_CHECKING:
    from eci.aikernel.generative_model import GenerativeState

__all__ = ["IntegratedInformationTheory", "sample_neural_state"]


class IntegratedInformationTheory:
    """Integrated information (Phi) calculator with three estimators."""

    def __init__(self, device: torch.device | None = None) -> None:
        self.device = device if device is not None else get_device()
        self.logger = get_logger("consciousness.iit")

    # ------------------------------------------------------------------
    def calculate_phi(
        self,
        neural_state: torch.Tensor | None = None,
        connectivity: torch.Tensor | None = None,
        method: str = "gaussian",
        exhaustive: bool = False,
        state: GenerativeState | None = None,
    ) -> dict[str, float]:
        """Compute Phi and its causal decomposition.

        Args:
            neural_state: activity tensor ``[time, neurons]``.
            connectivity: optional ``[neurons, neurons]`` matrix; defaults
                to the empirical correlation matrix.
            method: ``"gaussian"``, ``"quantum"`` or ``"discrete"``.
            exhaustive: if True and neurons <= 8, search all 2^n
                bipartitions for the true MIP instead of contiguous cuts.
            state: opt-in ``GenerativeState`` (AIK unification). When given
                (and ``neural_state`` is None), the working covariance is
                ``state.cov`` directly — the SAME covariance-core helpers
                run, so this path agrees with the raw-tensor path exactly
                (see ``sample_neural_state`` for time-series needs).
        """
        if state is not None:
            if neural_state is not None:
                raise ValueError("pass either neural_state or state, not both")
            return self._phi_from_state(state, connectivity, method, exhaustive)
        if neural_state is None:
            raise ValueError("neural_state or state is required")
        neural_state = neural_state.to(self.device).double()
        neural_state = torch.nan_to_num(neural_state, nan=0.0, posinf=1.0, neginf=-1.0)
        if connectivity is None:
            if neural_state.shape[1] < 2:
                connectivity = torch.ones(1, 1, device=self.device)
            else:
                cc = torch.corrcoef(neural_state.T)
                connectivity = torch.nan_to_num(cc, nan=0.0).clamp(-1.0, 1.0)
        connectivity = connectivity.to(self.device).double()
        connectivity = torch.nan_to_num(connectivity, nan=0.0, posinf=1.0, neginf=-1.0)

        if method == "gaussian":
            phi = self._phi_gaussian(neural_state, exhaustive=exhaustive)
        elif method == "quantum":
            phi = self._phi_quantum(neural_state)
        elif method == "discrete":
            phi = self._phi_discrete(neural_state)
        else:
            raise ValueError(f"unknown phi method: {method}")

        components = self._decompose_phi(neural_state, connectivity)
        return {
            "phi_total": float(max(0.0, phi)),
            "phi_cause": components["cause"],
            "phi_effect": components["effect"],
            "phi_intrinsic": components["intrinsic"],
        }

    # ------------------------------------------------------------------
    # GenerativeState path (AIK Phase 2b): exact thin wrapper, no resampling.
    # ------------------------------------------------------------------
    def _phi_from_state(
        self,
        state: GenerativeState,
        connectivity: torch.Tensor | None,
        method: str,
        exhaustive: bool,
    ) -> dict[str, float]:
        cov = state.cov.to(self.device).double()
        cov = 0.5 * (cov + cov.T)
        n = cov.shape[0]
        cov = cov + torch.eye(n, device=cov.device, dtype=cov.dtype) * COVARIANCE_REGULARIZER
        if method == "gaussian":
            phi = self._phi_gaussian_from_cov(cov, exhaustive=exhaustive)
        elif method == "quantum":
            phi = self._phi_quantum_from_cov(cov)
        elif method == "discrete":
            # Discrete needs a time series: seeded reconstruction whose only
            # role is feeding the binary predictive-information proxy.
            phi = self._phi_discrete(sample_neural_state(state, seed=0).to(self.device))
        else:
            raise ValueError(f"unknown phi method: {method}")
        if connectivity is None:
            connectivity = _cov_to_corr(cov)
        else:
            connectivity = connectivity.to(self.device).double()
            connectivity = torch.nan_to_num(connectivity, nan=0.0, posinf=1.0, neginf=-1.0)
        components = self._decompose_phi(
            sample_neural_state(state, seed=1).to(self.device).double(), connectivity
        )
        return {
            "phi_total": float(max(0.0, phi)),
            "phi_cause": components["cause"],
            "phi_effect": components["effect"],
            "phi_intrinsic": components["intrinsic"],
        }

    def _covariance(self, neural_state: torch.Tensor) -> torch.Tensor:
        n_time = neural_state.shape[0]
        centered = neural_state - neural_state.mean(dim=0, keepdim=True)
        cov = centered.T @ centered / max(1, n_time - 1)
        cov = 0.5 * (cov + cov.T)
        n = cov.shape[0]
        return cov + torch.eye(n, device=cov.device, dtype=cov.dtype) * COVARIANCE_REGULARIZER

    def _phi_gaussian(self, neural_state: torch.Tensor, exhaustive: bool = False) -> float:
        """Phi = 1/2 min_partition [logdet(Sigma_A) + logdet(Sigma_B) - logdet(Sigma)].

        This is the (non-negative) mutual-information gap between the
        bipartition halves and the whole (Oizumi et al. 2014, gaussian
        IIT). Fischer's inequality guarantees logdet(Sigma) <=
        logdet(Sigma_A) + logdet(Sigma_B), so the whole-minus-parts form
        used by the legacy implementation was always <= 0. Uses
        ``slogdet`` (stable even near-singular) and skips partitions with
        non-positive determinant signs.

        By default only contiguous cuts [:i, i:] are tried (O(n) heuristic
        that upper-bounds the true MIP cost). With exhaustive=True and
        n <= 8 all bipartitions are searched for the exact minimum.
        """
        return self._phi_gaussian_from_cov(self._covariance(neural_state), exhaustive=exhaustive)

    def _phi_gaussian_from_cov(self, cov: torch.Tensor, exhaustive: bool = False) -> float:
        """Covariance-core of gaussian Phi (shared by both input paths)."""
        n = cov.shape[0]
        if n < 2:
            return 0.0

        sign_w, logdet_w = torch.linalg.slogdet(cov)
        if sign_w <= 0:
            return 0.0

        min_phi = float("inf")

        def _gap(idx_a: list[int]) -> None:
            nonlocal min_phi
            idx_b = [i for i in range(n) if i not in idx_a]
            if not idx_a or not idx_b:
                return
            ia = torch.tensor(idx_a, device=cov.device)
            ib = torch.tensor(idx_b, device=cov.device)
            cov_a = cov.index_select(0, ia).index_select(1, ia)
            cov_b = cov.index_select(0, ib).index_select(1, ib)
            sign_a, logdet_a = torch.linalg.slogdet(cov_a)
            sign_b, logdet_b = torch.linalg.slogdet(cov_b)
            if sign_a <= 0 or sign_b <= 0:
                return
            phi = 0.5 * (float(logdet_a) + float(logdet_b) - float(logdet_w))
            min_phi = min(min_phi, phi)

        if exhaustive and n <= 8:
            from itertools import combinations

            for k in range(1, n // 2 + 1):
                for combo in combinations(range(n), k):
                    # Canonical half to avoid duplicate complements.
                    if 0 not in combo and len(combo) * 2 == n:
                        continue
                    _gap(list(combo))
        else:
            for i in range(1, n):
                _gap(list(range(i)))
        if min_phi == float("inf") or not torch.isfinite(torch.tensor(min_phi)):
            return 0.0
        return max(0.0, min_phi)

    # ------------------------------------------------------------------
    def _phi_quantum(self, neural_state: torch.Tensor) -> float:
        """Quantum Phi: min_i [S(rho_A(i)) + S(rho_B(i))] - S(rho) >= 0.

        By subadditivity S(rho) <= S(rho_A) + S(rho_B), the gap between the
        partition entropies and the whole is the non-negative quantum
        mutual-information gap; the covariance matrix (normalized) plays
        the role of a density matrix.
        """
        return self._phi_quantum_from_cov(self._covariance(neural_state))

    def _phi_quantum_from_cov(self, cov: torch.Tensor) -> float:
        """Covariance-core of quantum Phi (shared by both input paths)."""
        rho = cov / torch.trace(cov).real.clamp_min(EPS)
        entropy = qd.von_neumann_entropy(rho.unsqueeze(0))[0].item()
        n = rho.shape[0]

        def _sub_entropy(sub: torch.Tensor) -> float:
            tr = torch.trace(sub).real.clamp_min(EPS)
            sub_rho = sub / tr
            return qd.von_neumann_entropy(sub_rho.unsqueeze(0))[0].item()

        min_phi = float("inf")
        for i in range(1, n):
            sa = _sub_entropy(rho[:i, :i])
            sb = _sub_entropy(rho[i:, i:])
            min_phi = min(min_phi, sa + sb - entropy)
        if min_phi == float("inf"):
            return 0.0
        return max(0.0, min_phi)

    # ------------------------------------------------------------------
    def _phi_discrete(self, neural_state: torch.Tensor) -> float:
        """Discrete Phi proxy: predictive information I(past; future)."""
        from eci.consciousness.metrics import mutual_information

        if neural_state.shape[0] < 3:
            return 0.0
        binary = (neural_state > neural_state.median(dim=0, keepdim=True).values).double()
        past = binary[:-1].flatten()
        future = binary[1:].flatten()
        return max(0.0, mutual_information(past, future, bins=8))

    # ------------------------------------------------------------------
    def _decompose_phi(
        self,
        neural_state: torch.Tensor,
        connectivity: torch.Tensor,
    ) -> dict[str, float]:
        """Cause / effect / intrinsic decomposition (correlation-based)."""
        n_time = neural_state.shape[0]
        if n_time < 3:
            return {"cause": 0.0, "effect": 0.0, "intrinsic": 0.0}

        def _corr(a: torch.Tensor, b: torch.Tensor) -> float:
            a = a.flatten().double()
            b = b.flatten().double()
            va, vb = a.var(unbiased=False), b.var(unbiased=False)
            if va < EPS or vb < EPS:
                return 0.0
            cov = ((a - a.mean()) * (b - b.mean())).mean()
            return float(max(0.0, (cov / (va.sqrt() * vb).clamp_min(EPS)).item()))

        cause = _corr(neural_state[:-1], neural_state[1:])
        effect = _corr(neural_state[:-2], neural_state[2:])
        intrinsic = float(
            (connectivity.abs().sum() / max(1, connectivity.numel())).item()
        )
        return {"cause": cause, "effect": effect, "intrinsic": intrinsic}


def sample_neural_state(state: GenerativeState, n_time: int = 256, seed: int = 0) -> torch.Tensor:
    """Draw a [time, neurons] series from Q(s) = N(mu, cov) (seeded).

    Used ONLY where a time series is structurally required (discrete Phi
    proxy, cause/effect decomposition) — never for the gaussian/quantum
    Phi values themselves, which run on the covariance directly.
    """
    g = torch.Generator().manual_seed(seed)
    L = torch.linalg.cholesky(state.cov.double().to("cpu") + 1e-9 * torch.eye(state.dim, dtype=torch.float64))
    z = torch.randn(n_time, state.dim, dtype=torch.float64, generator=g)
    return (state.mu.double().to("cpu") + z @ L.T).float()


def _cov_to_corr(cov: torch.Tensor) -> torch.Tensor:
    """Exact correlation matrix of a covariance (for connectivity)."""
    v = torch.diag(cov).clamp_min(EPS)
    s = v.sqrt().outer(v.sqrt())
    return (cov / s).clamp(-1.0, 1.0)
