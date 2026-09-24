"""Connectome: hierarchical PHC-style matrix with Dale E/I + sparsity.

- 8 regions = 8 ECI subsystems (mirrors GNWT n_processors=8):
  quantum, consciousness, governance, memory, market, immune, federation, cognition
- Diagonal core (within-population) + inter-region feedforward/feedback +
  intra-region lateral, all in one sparse mask (event-driven, ~70% sparse)
- Dale enforced: column sign fixed excitatory (80%) / inhibitory (20%)
- Small-world init: local dense + few long-range; neurogenesis/pruning by rate
"""

from __future__ import annotations

import torch

__all__ = ["REGIONS", "Connectome"]

REGIONS = ("quantum", "consciousness", "governance", "memory",
           "market", "immune", "federation", "cognition")


class Connectome:
    def __init__(self, per_region: int = 8, seed: int = 0, sparsity: float = 0.7) -> None:
        g = torch.Generator().manual_seed(seed)
        self.per_region = per_region
        self.n_regions = len(REGIONS)
        self.n = per_region * self.n_regions
        self.sparsity = sparsity
        # block connectivity: strong diagonal, medium lateral, weak long-range
        w = torch.zeros(self.n, self.n)
        for i in range(self.n_regions):
            for j in range(self.n_regions):
                blk = torch.rand(per_region, per_region, generator=g)
                if i == j:
                    scale, thr = 0.5, 0.3  # dense local
                elif abs(i - j) == 1:
                    scale, thr = 0.3, 0.55  # lateral
                else:
                    scale, thr = 0.25, 0.8  # sparse long-range feedback
                mask = (blk > thr).float()
                w[i * per_region:(i + 1) * per_region,
                  j * per_region:(j + 1) * per_region] = mask * blk * scale
        # Dale: 80% excitatory columns, 20% inhibitory
        n_inh = self.n // 5
        perm = torch.randperm(self.n, generator=g)
        self.inh_cols = set(perm[:n_inh].tolist())
        self.sign = torch.ones(self.n)
        for c in self.inh_cols:
            self.sign[c] = -1.0
        self.w = w
        self.region_of = [REGIONS[i // per_region] for i in range(self.n)]
        self.seed = seed

    def project(self, spikes: torch.Tensor) -> torch.Tensor:
        """Signed spikes (n,) -> postsynaptic currents (n,) via sparse matvec."""
        return (spikes.abs() @ self.w) * self.sign

    def sparsity_actual(self) -> float:
        return 1.0 - (self.w > 0).float().mean().item()

    def prune_and_grow(self, rates: torch.Tensor, prune_thr: float = 0.001,
                       grow_prob: float = 0.01, seed: int = 1) -> dict[str, int]:
        """Structural plasticity: prune silent synapses, sprout a few new ones."""
        g = torch.Generator().manual_seed(seed)
        with torch.no_grad():
            out_strength = self.w.sum(dim=1)
            silent = (rates < prune_thr)
            pruned = 0
            for i in torch.where(silent)[0].tolist():
                row = self.w[i]
                if (row > 0).sum() > 1:
                    j = int(torch.argmax(row).item())
                    if self.w[i, j] > 0:
                        self.w[i, j] = 0.0
                        pruned += 1
            grown = 0
            cand = (torch.rand(self.n, self.n, generator=g) < grow_prob) & (self.w == 0)
            # never self-connect across identical index strongly; keep Dale sign implicit
            self.w[cand] = 0.05
            grown = int(cand.sum().item())
            _ = out_strength
        return {"pruned": pruned, "grown": grown}

    def to_dict(self) -> dict[str, object]:
        return {"regions": list(REGIONS), "n": self.n, "per_region": self.per_region,
                "sparsity": self.sparsity_actual(),
                "inhibitory_cols": len(self.inh_cols)}
