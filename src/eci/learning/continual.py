"""Elastic Weight Consolidation (Kirkpatrick et al. 2017).

Supports the standard EWC penalty and the online variant (Schwarz et al.
2018) where Fisher information is accumulated across tasks with a decay
``gamma``.
"""

from __future__ import annotations

from typing import Dict, Optional

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from eci.logging import get_logger

__all__ = ["ElasticWeightConsolidation"]


class ElasticWeightConsolidation:
    """Continual-learning regularizer protecting task A parameters."""

    def __init__(
        self,
        model: nn.Module,
        lambda_ewc: float = 0.4,
        online: bool = False,
        gamma: float = 0.999,
        device: Optional[torch.device] = None,
    ) -> None:
        self.model = model
        self.lambda_ewc = lambda_ewc
        self.online = online
        self.gamma = gamma
        self.device = device
        self.logger = get_logger("learning.ewc")
        self.fisher_dict: Dict[str, torch.Tensor] = {}
        self.optpar_dict: Dict[str, torch.Tensor] = {}
        for name, param in model.named_parameters():
            self.fisher_dict[name] = torch.zeros_like(param)
            self.optpar_dict[name] = param.data.clone()

    # ------------------------------------------------------------------
    def compute_fisher(self, data_loader: DataLoader, max_batches: Optional[int] = None) -> None:
        """Estimate F ~ E[(d/dtheta -log p(y|x,theta))^2] on task data."""
        self.model.eval()
        for name in self.fisher_dict:
            if self.online and self.fisher_dict[name].numel():
                self.fisher_dict[name] *= self.gamma
            else:
                self.fisher_dict[name].zero_()

        n_samples = 0
        for batch_idx, (data, target) in enumerate(data_loader):
            if max_batches is not None and batch_idx >= max_batches:
                break
            if self.device is not None:
                data, target = data.to(self.device), target.to(self.device)
            self.model.zero_grad()
            output = self.model(data)
            log_likelihood = torch.nn.functional.log_softmax(output.double(), dim=1)
            loss = -log_likelihood[range(len(target)), target].mean()
            loss.backward()
            for name, param in self.model.named_parameters():
                if param.grad is not None:
                    self.fisher_dict[name] += param.grad.data ** 2 * len(target)
            n_samples += len(target)

        if n_samples == 0:
            return
        for name in self.fisher_dict:
            if not self.online:
                self.fisher_dict[name] /= n_samples

    # ------------------------------------------------------------------
    def update_optimal_params(self) -> None:
        """Snapshot theta* after finishing a task."""
        for name, param in self.model.named_parameters():
            self.optpar_dict[name] = param.data.clone()

    def ewc_loss(self) -> torch.Tensor:
        """L_EWC = (lambda/2) * sum_i F_i (theta_i - theta*_i)^2."""
        loss = torch.zeros((), dtype=torch.float32)
        for name, param in self.model.named_parameters():
            fisher = self.fisher_dict.get(name)
            optpar = self.optpar_dict.get(name)
            if fisher is None or optpar is None:
                continue
            loss = loss + (fisher.to(param.device) * (param - optpar.to(param.device)) ** 2).sum()
        return self.lambda_ewc * loss / 2.0
