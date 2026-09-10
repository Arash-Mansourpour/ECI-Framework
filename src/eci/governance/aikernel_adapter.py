"""Phase 2c — governance adapter: consensus as posterior reconciliation.

PLACEMENT (documented choice): this module lives in ``governance/`` rather
than ``futura/`` because *reconciliation* (fusion of Q_i into shared Q)
is governance's job — PBFT/WBFT in ``network/`` and voting in
``governance/dao.py`` are today's reconciliation procedures. ``futura/``
(Futarchy) is a *consumer* of the market-vs-fusion comparison in §3, not
its home. The LMSR experiment helpers live here so the whole 2c claim is
reviewable in one file.

MAPPING TO EXISTING AGENT STATE (stated explicitly, per spec): none of
``NetworkNode`` (trust/stake/capabilities), DAO members
(tokens/phi/stake), or market positions (shares) carries a probabilistic
belief. There is nothing to "adapt to" — Q_i is NEW state, keyed by the
same agent ids, held alongside. Trust/stake re-enter honestly as
*optional fusion weights* (voting power = precision share), tested.

GRANULARITY: one ``AgentContributor`` per agent (not per mechanism),
mirroring 2b's "one per analysis" call. PBFT votes and market trades are
reconciliation *procedures* over the same Q_i's — fusing twice through
two mechanisms would double-count evidence, so the ledger holds agents,
not mechanisms.

F-SHARE: ``complexity = D_KL[Q_i || P]`` (reused from
``consciousness.aikernel_adapter.gaussian_complexity`` — pure-function
reuse, not a bypass), i.e. each agent's belief displacement. Same
discipline as 2a/2b.

FUSION CORRECTNESS (the subtle point): naive ``fuse_beliefs`` sums
precisions — exact ONLY for split shares of one belief. Independent
posteriors sharing a prior need the prior subtracted once:
  Λ_f = Σ_i α_i·(Λ_i − Λ_0) + Λ_0,   μ_f = Λ_f⁻¹(Σ_i α_i(Λ_i μ_i − Λ_0 μ_0) + Λ_0 μ_0)
``reconcile()`` implements this (``fuse_with_shared_prior``). Fusing two
IDENTICAL posteriors is then idempotent (returns Q) — the zero-reduction
test rests on this identity, not on tuning.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence

import torch

from eci.aikernel.functors import fuse_beliefs, split_belief
from eci.aikernel.generative_model import GenerativeState, Likelihood, Prior
from eci.consciousness.aikernel_adapter import gaussian_complexity

__all__ = ["AgentContributor", "fuse_with_shared_prior", "reconcile",
           "event_prob", "stacked_likelihood", "pooled_free_energy",
           "market_vs_fusion"]


class AgentContributor:
    """One agent's local posterior Q_i(s) = N(mu, cov), conjugate updates."""

    def __init__(self, agent_id: str, dim: int = 1, prior: Prior | None = None,
                 obs_noise: float = 1.0) -> None:
        self.agent_id = agent_id
        self.dim = dim
        self.prior = prior or Prior.standard(dim)
        self.R = torch.eye(dim) * obs_noise
        self._mu = self.prior.mu0.clone().float()
        self._cov = self.prior.Sigma0.clone().float()

    def observe(self, o: torch.Tensor) -> "AgentContributor":
        """Exact conjugate update for o = s + N(0, R)."""
        o = torch.as_tensor(o, dtype=torch.float32).reshape(self.dim)
        Rinv = torch.linalg.inv(self.R)
        Lam_old = torch.linalg.inv(self._cov)
        Lam_new = Lam_old + Rinv
        self._cov = torch.linalg.inv(Lam_new)
        self._mu = self._cov @ (Lam_old @ self._mu + Rinv @ o)
        return self

    # -- StateContributor contract ------------------------------------------
    def posterior(self) -> GenerativeState:
        return GenerativeState(self._mu.clone(), self._cov.clone())

    def update(self, observation: torch.Tensor) -> GenerativeState:
        return self.observe(observation).posterior()

    def free_energy_contribution(self) -> torch.Tensor:
        return gaussian_complexity(self._mu, self._cov, self.prior)


def fuse_with_shared_prior(parts: Sequence[GenerativeState], prior: Prior,
                            weights: Sequence[float] | None = None) -> GenerativeState:
    """Precision fusion correcting the shared prior (exact Bayes for
    conditionally-independent observations). Equal weights default."""
    n = len(parts)
    w = torch.as_tensor(list(weights) if weights else [1.0] * n, dtype=torch.float32)
    w = w / w.sum()
    L0 = torch.linalg.inv(prior.Sigma0.float())
    Lam = L0.clone()
    b = L0 @ prior.mu0.float()
    for (wi, st) in zip(w, parts):
        Li = torch.linalg.inv(st.cov)
        Lam = Lam + float(wi) * (Li - L0)
        b = b + float(wi) * (Li @ st.mu - L0 @ prior.mu0.float())
    cov = torch.linalg.inv(Lam)
    return GenerativeState(cov @ b, cov)


def reconcile(contributors: Sequence[AgentContributor],
              weights: Sequence[float] | None = None) -> GenerativeState:
    """Consensus = fusion. Returns the shared Q (does NOT mutate members)."""
    if not contributors:
        raise ValueError("need at least one contributor")
    return fuse_with_shared_prior([c.posterior() for c in contributors],
                                  contributors[0].prior, weights)


def event_prob(mu: torch.Tensor, cov: torch.Tensor, threshold: float,
               coord: int = 0) -> float:
    """P(s_coord > threshold) under N(mu, cov) — exact via erfc."""
    m = float(mu.reshape(-1)[coord].item())
    s = math.sqrt(max(1e-12, float(cov[coord, coord].item())))
    return 0.5 * float(torch.erfc(torch.tensor((threshold - m) / (s * math.sqrt(2)))).item())


def stacked_likelihood(obs_list: Sequence[torch.Tensor],
                       R_list: Sequence[torch.Tensor]) -> tuple:
    """Stack independent o_j = s + N(0, R_j) into one Likelihood (A = [I;…])."""
    A = torch.cat([torch.eye(o.numel()) for o in obs_list], dim=0)
    R = torch.block_diag(*R_list)
    o = torch.cat([o.reshape(-1) for o in obs_list], dim=0)
    d = obs_list[0].numel()
    from eci.aikernel.generative_model import Likelihood as _L
    return o, _L(A.float(), R.float())


def pooled_free_energy(mu: torch.Tensor, cov: torch.Tensor,
                       obs_list: Sequence[torch.Tensor],
                       R_list: Sequence[torch.Tensor], prior: Prior) -> float:
    """F(Q) against ALL pooled evidence — the yardstick for ΔF."""
    from eci.aikernel.free_energy import free_energy as _F
    from eci.aikernel.generative_model import GenerativeState as _GS
    o, L = stacked_likelihood([torch.as_tensor(x, dtype=torch.float32) for x in obs_list],
                              [torch.as_tensor(r, dtype=torch.float32) for r in R_list])
    return float(_F(_GS(mu, cov), o, L, prior).item())


def market_vs_fusion(s_star: float, prior: Prior, noises: Sequence[float],
                     obs: Sequence[float], threshold: float = 1.0,
                     b: float = 10.0, rounds: int = 6, trade_k: float = 1.0,
                     tol: float = 1e-3, seed: int = 0) -> Dict[str, Any]:
    """Same scenario, two reconciliation paths. Returns both, unmerged.

    Fusion path: exact conjugate posteriors + shared-prior fusion.
    Market path (documented myopic protocol): round-robin LMSR trading;
      each agent moves the price toward P(E|Q_i) from PRIVATE info only
      (no inference from price — stated assumption A1); risk-neutral,
      fixed rule shares = clamp(trade_k·b·|p_i − price|, 1, b) (A2:
      position sizes are heuristic, not utility-optimal); stops on
      no-trade round or after `rounds`.
    Compares on the event margin P(E) — the market emits a scalar price,
    not a posterior (structural finding §D1, not a bug).
    """
    from eci.market import Marketplace
    agents = [AgentContributor(f"a{i}", dim=1, prior=prior, obs_noise=n)
              for i, n in enumerate(noises)]
    for ag, o in zip(agents, obs):
        ag.observe(torch.tensor([o]))
    # (a) exact fusion
    shared = fuse_with_shared_prior([a.posterior() for a in agents], prior)
    p_fused = event_prob(shared.mu, shared.cov, threshold)
    # (b) LMSR rounds
    mk = Marketplace()
    mkt = mk.market_for("s_gt_thr")
    price0 = mkt.price_yes()
    trades: List[Dict[str, Any]] = []
    for _ in range(rounds):
        moved = False
        for ag in agents:
            st = ag.posterior()
            p_i = event_prob(st.mu, st.cov, threshold)
            px = mkt.price_yes()
            if p_i > px * (1 + tol):
                side, want = "yes", True
            elif p_i < px * (1 - tol):
                side, want = "no", True
            else:
                want = False
            if want:
                shares = min(b, max(1.0, trade_k * b * abs(p_i - px)))
                r = mk.trade(ag.agent_id, "s_gt_thr", side, shares)
                trades.append({"agent": ag.agent_id, "side": side,
                               "shares": round(shares, 3), "price": r["price"]})
                moved = True
        if not moved:
            break
    price_final = mkt.price_yes()
    # F yardstick on pooled evidence
    Rs = [torch.eye(1) * n for n in noises]
    ob = [torch.tensor([o]) for o in obs]
    F_ind = sum(pooled_free_energy(a.posterior().mu, a.posterior().cov, ob, Rs, prior)
                for a in agents) / len(agents)
    F_fused = pooled_free_energy(shared.mu, shared.cov, ob, Rs, prior)
    return {"s_star": s_star, "threshold": threshold, "truth_yes": bool(s_star > threshold),
            "p_fused": p_fused, "price_start": price0, "price_final": price_final,
            "n_trades": len(trades), "trades": trades,
            "F_individual_mean": F_ind, "F_fused": F_fused,
            "dF_fusion": F_ind - F_fused}
