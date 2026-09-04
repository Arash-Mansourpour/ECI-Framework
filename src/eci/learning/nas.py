"""Differentiable Neural Architecture Search (DARTS, Liu et al. 2019).

Fixes over the legacy version:
* ``Zero`` op returns ``torch.zeros_like(x)`` (still records autograd shape).
* Architecture derivation keeps the *top-2 edges* per node by softmax mass
  (standard DARTS derive) instead of a per-input argmax.
* The search loop cycles a proper validation iterator instead of
  ``next(iter(val_loader))`` + bare ``except``.
"""

from __future__ import annotations

import itertools
from typing import Dict, Iterator, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader

from eci.logging import get_logger

__all__ = ["Zero", "SeparableConv2d", "DARTSSearchSpace", "AdvancedNAS"]


class Zero(nn.Module):
    """Zero operation (output structurally zero, gradient-free)."""

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return torch.zeros_like(x)


class SeparableConv2d(nn.Module):
    """Depthwise + pointwise separable convolution."""

    def __init__(self, in_channels: int, out_channels: int, kernel_size: int, stride: int, padding: int) -> None:
        super().__init__()
        self.depthwise = nn.Conv2d(
            in_channels, in_channels, kernel_size,
            stride=stride, padding=padding, groups=in_channels,
        )
        self.pointwise = nn.Conv2d(in_channels, out_channels, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.pointwise(self.depthwise(x))


class DARTSSearchSpace(nn.Module):
    """Micro-cell DARTS search space."""

    PRIMITIVES = [
        "none",
        "skip_connect",
        "conv_3x3",
        "conv_5x5",
        "sep_conv_3x3",
        "sep_conv_5x5",
        "dil_conv_3x3",
        "dil_conv_5x5",
        "avg_pool_3x3",
        "max_pool_3x3",
    ]

    def __init__(self, n_nodes: int = 4, channels: int = 16) -> None:
        super().__init__()
        self.n_nodes = n_nodes
        self.channels = channels

        self.alphas = nn.ParameterList()
        for i in range(n_nodes):
            n_inputs = i + 2
            self.alphas.append(nn.Parameter(torch.randn(n_inputs, len(self.PRIMITIVES)) * 1e-3))

        self.ops = nn.ModuleList()
        for i in range(n_nodes):
            node_ops = nn.ModuleList()
            for _ in range(i + 2):
                ops = nn.ModuleList(self._build_ops(channels))
                node_ops.append(ops)
            self.ops.append(node_ops)

    def _build_ops(self, channels: int) -> List[nn.Module]:
        c = channels
        return [
            Zero(),
            nn.Identity(),
            nn.Conv2d(c, c, 3, padding=1),
            nn.Conv2d(c, c, 5, padding=2),
            SeparableConv2d(c, c, 3, 1, 1),
            SeparableConv2d(c, c, 5, 1, 2),
            nn.Conv2d(c, c, 3, padding=2, dilation=2),
            nn.Conv2d(c, c, 5, padding=4, dilation=2),
            nn.AvgPool2d(3, stride=1, padding=1),
            nn.MaxPool2d(3, stride=1, padding=1),
        ]

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        states = [x, x]
        for node in range(self.n_nodes):
            weights = F.softmax(self.alphas[node], dim=-1)
            s = sum(
                (weights[inp, op] * self.ops[node][inp][op](states[inp])
                 for inp in range(len(states))
                 for op in range(len(self.PRIMITIVES))),
                torch.zeros_like(x),
            )
            states.append(s)
        return torch.cat(states[-self.n_nodes:], dim=1)

    def derive(self, keep_edges: int = 2) -> List[Tuple[int, int, str]]:
        """Discretize: top-``keep_edges`` inputs per node, best op per edge."""
        architecture: List[Tuple[int, int, str]] = []
        for node in range(self.n_nodes):
            weights = F.softmax(self.alphas[node], dim=-1)
            edge_strength = weights.max(dim=1).values
            top_inputs = torch.topk(edge_strength, min(keep_edges, edge_strength.numel())).indices.tolist()
            for inp in sorted(top_inputs):
                op_idx = int(torch.argmax(weights[inp]).item())
                op_name = self.PRIMITIVES[op_idx]
                if op_name != "none":
                    architecture.append((node, inp, op_name))
        return architecture

    # Backwards-compatible alias used by the legacy API.
    def get_architecture(self) -> List[Tuple[str, int]]:
        return [(op, inp) for (_, inp, op) in self.derive()]


class AdvancedNAS:
    """DARTS search driver with bilinear (alternating) optimization."""

    def __init__(
        self,
        search_space: str = "darts",
        device: Optional[torch.device] = None,
        w_lr: float = 0.025,
        alpha_lr: float = 3e-4,
    ) -> None:
        if search_space != "darts":
            raise ValueError(f"unknown search space: {search_space}")
        self.search_space = search_space
        self.device = device if device is not None else torch.device("cpu")
        self.logger = get_logger("learning.nas")
        self.w_lr = w_lr
        self.alpha_lr = alpha_lr
        self.search_history: List[Dict[str, float]] = []

    async def search(
        self,
        train_loader: DataLoader,
        val_loader: DataLoader,
        n_epochs: int = 50,
        n_nodes: int = 4,
        channels: int = 16,
    ) -> Dict[str, object]:
        """Run DARTS search; returns the derived architecture and metrics."""
        model = DARTSSearchSpace(n_nodes=n_nodes, channels=channels).to(self.device)
        criterion = nn.CrossEntropyLoss()

        w_optimizer = torch.optim.SGD(
            [p for n, p in model.named_parameters() if "alphas" not in n],
            lr=self.w_lr, momentum=0.9, weight_decay=3e-4,
        )
        alpha_optimizer = torch.optim.Adam(
            model.alphas, lr=self.alpha_lr, betas=(0.5, 0.999), weight_decay=1e-3,
        )

        val_iter: Iterator = iter(val_loader)
        best_val_acc = 0.0
        best_architecture: Optional[List[Tuple[int, int, str]]] = None

        for epoch in range(n_epochs):
            model.train()
            for data, target in train_loader:
                data, target = data.to(self.device), target.to(self.device)

                # Architecture step on a validation batch
                try:
                    val_data, val_target = next(val_iter)
                except StopIteration:
                    val_iter = iter(val_loader)
                    val_data, val_target = next(val_iter)
                val_data, val_target = val_data.to(self.device), val_target.to(self.device)
                alpha_optimizer.zero_grad()
                val_loss = criterion(model(val_data), val_target)
                val_loss.backward()
                alpha_optimizer.step()

                # Weight step on the training batch
                w_optimizer.zero_grad()
                loss = criterion(model(data), target)
                loss.backward()
                w_optimizer.step()

            # Validation pass
            model.eval()
            correct, total = 0, 0
            with torch.no_grad():
                for data, target in val_loader:
                    data, target = data.to(self.device), target.to(self.device)
                    pred = model(data).argmax(dim=1)
                    correct += (pred == target).sum().item()
                    total += target.size(0)
            val_acc = correct / max(1, total)
            self.search_history.append({"epoch": float(epoch), "val_accuracy": val_acc})
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_architecture = model.derive()
            self.logger.info("NAS epoch %d: val_acc=%.4f", epoch, val_acc)

        return {
            "architecture": best_architecture,
            "val_accuracy": best_val_acc,
            "search_epochs": n_epochs,
        }
