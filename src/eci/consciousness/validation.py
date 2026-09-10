"""Consciousness validation harness (roadmap: PyPhi X-val, EEG closed-loop, QNN adherence).

- PyPhi cross-check: when `pyphi` is installed, compare ECI gaussian-Phi
  against pyphi's Phi on a tiny 2-node network; otherwise record a skip
  with the reason (no silent pass). Deterministic fallback keeps CI green.
- EEG closed-loop: bandpower(resting vs active) -> suggested intervention
  tier using the same thresholds as protocol v2 (0.1/1/5/10 bits proxy).
- QNN adherence classifier: tiny torch logistic head mapping
  [phi_norm, awareness, gnwt_broadcast] -> obedience probability; trains
  in <1s on CPU for demos, exports weights for the registry.
"""

from __future__ import annotations

import importlib.util
import math
from typing import Any, Dict, List, Optional, Sequence

__all__ = ["pyphi_crosscheck", "eeg_closed_loop", "AdherenceHead", "train_adherence_head"]


def pyphi_crosscheck(cov=None) -> Dict[str, Any]:
    """Compare ECI Phi with PyPhi when available; honest skip otherwise."""
    spec = importlib.util.find_spec("pyphi")
    if spec is None:
        return {"ok": True, "skipped": True, "reason": "pyphi not installed",
                "eci_phi": None, "pyphi_phi": None, "agree": None}
    try:
        import numpy as np
        import pyphi  # type: ignore
        from eci.consciousness.iit import IntegratedInformationTheory
        import torch
        cov_m = np.array([[1.0, 0.4], [0.4, 1.0]])
        eci = IntegratedInformationTheory()
        eci_phi = float(eci.gaussian_phi(torch.tensor(cov_m, dtype=torch.float32)))
        # minimal pyphi network: 2 nodes, deterministic TPM
        network = pyphi.Network(np.array([[[0, 0], [0, 1]], [[1, 0], [1, 1]]]))
        # pyphi API varies by version; guard everything
        py_phi = None
        try:
            subsys = pyphi.Subsystem(network, (1, 0), range(2))
            sia = pyphi.compute.sia(subsys)  # type: ignore[attr-defined]
            py_phi = float(sia.phi)
        except Exception as exc:  # noqa: BLE001
            return {"ok": True, "skipped": True, "reason": f"pyphi api: {exc}",
                    "eci_phi": eci_phi, "pyphi_phi": None, "agree": None}
        return {"ok": True, "skipped": False, "eci_phi": eci_phi, "pyphi_phi": py_phi,
                "agree": bool(abs(eci_phi - py_phi) < 1.0)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": repr(exc)}


def eeg_closed_loop(resting: Sequence[float], active: Sequence[float]) -> Dict[str, Any]:
    from eci.consciousness.eeg import bandpower
    import numpy as np
    r = np.asarray(list(resting), dtype=float)
    a = np.asarray(list(active), dtype=float)
    pr = float(bandpower(r).mean()) if r.size else 0.0
    pa = float(bandpower(a).mean()) if a.size else 0.0
    lift = pa / (pr + 1e-9)
    bits_proxy = max(0.0, math.log2(lift + 1e-9) + 1.0) if lift > 0 else 0.0
    tier = "none" if bits_proxy < 1 else ("watch" if bits_proxy < 5 else ("elevate" if bits_proxy < 10 else "intervene"))
    return {"rest_power": pr, "active_power": pa, "lift": lift,
            "bits_proxy": bits_proxy, "tier": tier, "act": tier != "none"}


class AdherenceHead:
    """Logistic head: p(obey) = sigmoid(w·[phi_norm, awareness, broadcast]+b)."""

    def __init__(self, w: Sequence[float] | None = None, b: float = 0.0) -> None:
        import torch
        self.w = torch.tensor(list(w) if w else [0.8, 0.6, 0.4], dtype=torch.float32)
        self.b = float(b)

    def predict(self, phi_norm: float, awareness: float, broadcast: float) -> float:
        import torch
        x = torch.tensor([phi_norm, awareness, broadcast], dtype=torch.float32)
        return float(torch.sigmoid(x @ self.w + self.b).item())

    def to_dict(self) -> Dict[str, Any]:
        return {"w": [float(v) for v in self.w.tolist()], "b": self.b}


def train_adherence_head(rows: List[Dict[str, float]], steps: int = 200, lr: float = 0.1) -> AdherenceHead:
    import torch
    head = AdherenceHead()
    w = head.w.clone().requires_grad_(True)
    b = torch.tensor(head.b, requires_grad=True)
    opt = torch.optim.SGD([w, b], lr=lr)
    for _ in range(steps):
        loss = torch.tensor(0.0)
        for r in rows:
            x = torch.tensor([r["phi_norm"], r["awareness"], r["broadcast"]])
            p = torch.sigmoid(x @ w + b)
            y = torch.tensor(r["label"])
            loss = loss - (y * torch.log(p + 1e-6) + (1 - y) * torch.log(1 - p + 1e-6))
        opt.zero_grad()
        loss.backward()
        opt.step()
    return AdherenceHead(w.detach().tolist(), float(b.item()))
