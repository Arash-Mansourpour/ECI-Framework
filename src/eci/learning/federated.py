"""Federated learning with differential privacy (DP-FedAvg).

McMahan et al. (2017) FedAvg, extended with:
* per-client L2 update clipping,
* Gaussian noise calibrated to (epsilon, delta)-DP at the aggregation step,
* honest weighted averaging by client sample counts.
"""

from __future__ import annotations

import copy
import math
from typing import Dict, List, Optional, Sequence, Tuple

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from eci.core.device import get_device
from eci.logging import get_logger

__all__ = ["FederatedLearningCoordinator"]


class FederatedLearningCoordinator:
    """Server-side coordinator for DP-FedAvg."""

    def __init__(
        self,
        global_model: nn.Module,
        n_clients: int,
        privacy_epsilon: float = 1.0,
        privacy_delta: float = 1e-5,
        clip_norm: float = 1.0,
        participation_fraction: float = 0.3,
        local_lr: float = 0.01,
        device: Optional[torch.device] = None,
    ) -> None:
        if n_clients < 1:
            raise ValueError("n_clients must be >= 1")
        if privacy_epsilon <= 0:
            raise ValueError("privacy_epsilon must be positive")
        if clip_norm <= 0:
            raise ValueError("clip_norm must be positive")
        self.global_model = global_model
        self.n_clients = n_clients
        self.privacy_epsilon = privacy_epsilon
        self.privacy_delta = privacy_delta
        self.clip_norm = clip_norm
        self.participation_fraction = participation_fraction
        self.local_lr = local_lr
        self.device = device if device is not None else get_device()
        self.logger = get_logger("learning.federated")
        self.round_history: List[Dict[str, float]] = []
        self.noise_multiplier = self._compute_noise_multiplier(privacy_epsilon, privacy_delta)

    @staticmethod
    def _compute_noise_multiplier(epsilon: float, delta: float) -> float:
        """Gaussian-mechanism sigma for one round (simplified accounting)."""
        return math.sqrt(2.0 * math.log(1.25 / delta)) / epsilon

    # ------------------------------------------------------------------
    async def federated_round(
        self,
        client_data: Sequence[DataLoader],
        n_local_epochs: int = 2,
        rng: Optional[torch.Generator] = None,
    ) -> Dict[str, float]:
        """One FedAvg round: sample clients, train, clip+noise, aggregate."""
        n_participants = max(
            1, min(self.n_clients, len(client_data)),
            int(self.participation_fraction * self.n_clients),
        )
        perm = torch.randperm(self.n_clients, generator=rng)[:n_participants].tolist()
        selected = [c for c in perm if c < len(client_data)]
        if not selected:
            selected = [0]

        updates: List[Dict[str, torch.Tensor]] = []
        weights: List[float] = []
        for client_id in selected:
            update, weight = self._client_update(client_data[client_id], n_local_epochs)
            updates.append(update)
            weights.append(weight)

        aggregated = self._aggregate_with_privacy(updates, weights)
        self._apply_update(aggregated)

        avg_loss = self._evaluate_global_model(list(client_data))
        result = {
            "participating_clients": float(len(selected)),
            "average_loss": avg_loss,
            "privacy_epsilon": self.privacy_epsilon,
            "noise_multiplier": self.noise_multiplier,
        }
        self.round_history.append(result)
        return result

    # ------------------------------------------------------------------
    def _client_update(
        self,
        data_loader: DataLoader,
        n_epochs: int,
    ) -> Tuple[Dict[str, torch.Tensor], float]:
        local_model = copy.deepcopy(self.global_model).to(self.device)
        optimizer = torch.optim.SGD(local_model.parameters(), lr=self.local_lr)
        criterion = nn.CrossEntropyLoss()

        local_model.train()
        n_samples = 0
        for _ in range(n_epochs):
            for data, target in data_loader:
                data, target = data.to(self.device), target.to(self.device)
                optimizer.zero_grad()
                loss = criterion(local_model(data), target)
                loss.backward()
                optimizer.step()
                n_samples += data.size(0)

        global_params = dict(self.global_model.named_parameters())
        update: Dict[str, torch.Tensor] = {}
        for name, param in local_model.named_parameters():
            if name in global_params:
                update[name] = (param.data - global_params[name].data).cpu()
        return update, float(max(1, n_samples))

    def _clip_update(self, update: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        norm = torch.sqrt(sum((u ** 2).sum() for u in update.values()))
        scale = min(1.0, self.clip_norm / (norm.item() + 1e-12))
        return {k: v * scale for k, v in update.items()}

    def _aggregate_with_privacy(
        self,
        updates: List[Dict[str, torch.Tensor]],
        weights: List[float],
    ) -> Dict[str, torch.Tensor]:
        clipped = [self._clip_update(u) for u in updates]
        total_weight = sum(weights)
        aggregated: Dict[str, torch.Tensor] = {}
        names = clipped[0].keys()
        sigma = self.noise_multiplier * self.clip_norm / math.sqrt(len(clipped))
        for name in names:
            weighted = sum(
                u[name] * (w / total_weight) for u, w in zip(clipped, weights)
            )
            aggregated[name] = weighted + torch.randn_like(weighted) * sigma
        return aggregated

    def _apply_update(self, update: Dict[str, torch.Tensor]) -> None:
        with torch.no_grad():
            for name, param in self.global_model.named_parameters():
                if name in update:
                    param.data += update[name].to(param.device)

    def _evaluate_global_model(self, client_data: List[DataLoader]) -> float:
        self.global_model.eval()
        criterion = nn.CrossEntropyLoss()
        total_loss, n_samples = 0.0, 0
        with torch.no_grad():
            for data_loader in client_data:
                for data, target in data_loader:
                    data, target = data.to(self.device), target.to(self.device)
                    output = self.global_model(data)
                    total_loss += criterion(output, target).item() * data.size(0)
                    n_samples += data.size(0)
        return total_loss / max(1, n_samples)
