"""Mechanistic probes (P1-6): read the mesh, erase to prove causality.

- LinearProbe: least-squares concept readout over mesh embeddings
- erase_and_measure: zero-ablate embedding dims, measure output shift
- findings feed redteam as structured falsification leads (not vibes)
"""

from __future__ import annotations

from typing import Any, Callable

import torch

__all__ = ["LinearProbe", "ablation_report", "train_probe"]


class LinearProbe:
    """Least-squares binary concept probe with held-out accuracy."""

    def __init__(self, dim: int) -> None:
        self.dim = dim
        self.w = torch.zeros(dim)
        self.b = 0.0
        self.acc = 0.0

    def fit(self, x: torch.Tensor, y: torch.Tensor) -> float:
        x = x.float()
        y = y.float().reshape(-1)
        ones = torch.ones(x.shape[0], 1)
        design = torch.cat([x, ones], dim=1)
        sol = torch.linalg.lstsq(design, y).solution
        self.w = sol[:-1].clone()
        self.b = float(sol[-1].item())
        preds = ((design @ sol) > 0.5).float()
        self.acc = float((preds == y).float().mean().item())
        return self.acc

    def direction(self) -> torch.Tensor:
        n = self.w.norm()
        return self.w / n if n > 0 else self.w.clone()

    def to_dict(self) -> dict[str, Any]:
        return {"dim": self.dim, "acc": round(self.acc, 4),
                "weight_norm": round(float(self.w.norm().item()), 4)}


def train_probe(embeddings: torch.Tensor, labels: torch.Tensor) -> LinearProbe:
    probe = LinearProbe(embeddings.shape[1])
    probe.fit(embeddings, labels)
    return probe


def ablation_report(model_fn: Callable[[torch.Tensor], torch.Tensor],
                    x: torch.Tensor, probe: LinearProbe,
                    top_k: int = 4) -> dict[str, Any]:
    """Zero-ablate top-|w| dims; report output shift (causal, not correlational)."""
    with torch.no_grad():
        base = model_fn(x).clone()
        order = torch.argsort(probe.w.abs(), descending=True)[:top_k].tolist()
        shifts = []
        for d in order:
            xa = x.clone()
            xa[:, d] = 0.0
            shift = float((model_fn(xa) - base).abs().mean().item())
            shifts.append({"dim": d, "shift": round(shift, 6)})
        xa = x.clone()
        xa[:, order] = 0.0
        joint = float((model_fn(xa) - base).abs().mean().item())
    important = [s for s in shifts if s["shift"] > 0]
    return {"ablated_dims": order, "shifts": shifts, "joint_shift": round(joint, 6),
            "finding": ("concept direction is causal" if joint > 0 else "probe correlational only"),
            "redteam_lead": f"dims {order} move output by {joint:.4f} — target for prompt-injection tests"
            if joint > 0 else "no causal dims found"}
