"""Model-Agnostic Meta-Learning (Finn et al., 2017).

Unlike the legacy implementation (whose ``type(model)(*[])`` clone crashed
for any model with constructor arguments), this version is built around a
*functional forward*: the wrapped model must implement

    functional_forward(x, params: List[Tensor]) -> output

``MetaMLP`` provides a reference implementation. The inner loop adapts
cloned parameters via differentiable updates (``theta' = theta - lr * g``
with ``create_graph=True``), so gradients flow through the adaptation into
the meta-parameters - a true second-order MAML. ``first_order=True``
switches to FOMAML (cheaper, no second derivatives).
"""

from __future__ import annotations

import copy
from typing import Callable, List, Optional, Sequence, Tuple

import torch
import torch.nn as nn

from eci.logging import get_logger

__all__ = ["MetaMLP", "MAML", "TaskBatch"]


class MetaMLP(nn.Module):
    """Reference meta-learnable MLP with a functional forward."""

    def __init__(
        self,
        in_features: int,
        hidden: int = 64,
        out_features: int = 2,
        n_hidden_layers: int = 1,
    ) -> None:
        super().__init__()
        dims = [in_features] + [hidden] * n_hidden_layers + [out_features]
        self.shapes: List[Tuple[int, int]] = []
        self.biases: List[int] = []
        for a, b in zip(dims[:-1], dims[1:]):
            self.shapes.append((a, b))
            self.biases.append(b)
        self.n_params = sum(a * b for a, b in self.shapes) + sum(self.biases)
        # Registered placeholders only to expose parameter metadata.
        self._weights = nn.ParameterList(
            [nn.Parameter(torch.empty(a, b)) for a, b in self.shapes]
        )
        self._biases = nn.ParameterList([nn.Parameter(torch.empty(b)) for b in self.biases])
        self.reset_parameters()

    def reset_parameters(self) -> None:
        for w, (a, b) in zip(self._weights, self.shapes):
            nn.init.kaiming_uniform_(w, a=5 ** 0.5)
        for b in self._biases:
            nn.init.zeros_(b)

    def param_vector(self) -> List[torch.Tensor]:
        params: List[torch.Tensor] = [p for p in self._weights]
        params += [p for p in self._biases]
        return params

    def functional_forward(self, x: torch.Tensor, params: List[torch.Tensor]) -> torch.Tensor:
        """Forward with an explicit parameter list (enables MAML inner loop)."""
        n_w = len(self.shapes)
        weights = params[:n_w]
        biases = params[n_w:]
        h = x
        for i, (w, b) in enumerate(zip(weights, biases)):
            h = h @ w + b
            if i < len(weights) - 1:
                h = torch.relu(h)
        return h


TaskBatch = Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]


class MAML:
    """First- and second-order MAML over any ``functional_forward`` model."""

    def __init__(
        self,
        model: nn.Module,
        inner_lr: float = 0.01,
        outer_lr: float = 0.001,
        first_order: bool = False,
        loss_fn: Optional[Callable[..., torch.Tensor]] = None,
    ) -> None:
        if not hasattr(model, "functional_forward"):
            raise TypeError(
                "model must implement functional_forward(x, params); use MetaMLP"
            )
        self.model = model
        self.inner_lr = inner_lr
        self.first_order = first_order
        self.loss_fn = loss_fn or nn.functional.cross_entropy
        self.meta_optimizer = torch.optim.Adam(model.parameters(), lr=outer_lr)
        self.logger = get_logger("learning.maml")

    # ------------------------------------------------------------------
    def inner_loop(
        self,
        support_x: torch.Tensor,
        support_y: torch.Tensor,
        n_inner_steps: int = 5,
    ) -> List[torch.Tensor]:
        """Adapt a *cloned* parameter list to the support set.

        Returns the adapted parameters; with ``first_order=False`` the
        graph is retained so the outer loss backpropagates through the
        inner updates.
        """
        params = [p.clone() for p in self.model.param_vector()]
        for p in params:
            p.requires_grad_(True)

        for _ in range(n_inner_steps):
            output = self.model.functional_forward(support_x, params)
            loss = self.loss_fn(output, support_y)
            grads = torch.autograd.grad(
                loss, params, create_graph=not self.first_order
            )
            params = [p - self.inner_lr * g for p, g in zip(params, grads)]
        return params

    # ------------------------------------------------------------------
    def outer_loop(
        self,
        task_batch: Sequence[TaskBatch],
        n_inner_steps: int = 5,
    ) -> float:
        """Meta-update across a batch of tasks; returns mean meta-loss."""
        self.meta_optimizer.zero_grad()
        meta_loss = torch.zeros((), dtype=torch.float64)
        for support_x, support_y, query_x, query_y in task_batch:
            adapted = self.inner_loop(support_x, support_y, n_inner_steps)
            query_output = self.model.functional_forward(query_x, adapted)
            task_loss = self.loss_fn(query_output, query_y)
            meta_loss = meta_loss + task_loss.double()
        meta_loss = (meta_loss / len(task_batch)).float()
        meta_loss.backward()
        self.meta_optimizer.step()
        return float(meta_loss.item())

    # ------------------------------------------------------------------
    def adapt_and_evaluate(
        self,
        support_x: torch.Tensor,
        support_y: torch.Tensor,
        query_x: torch.Tensor,
        query_y: torch.Tensor,
        n_inner_steps: int = 5,
    ) -> dict:
        """Diagnostic: pre/post-adaptation loss on the query set."""
        with torch.no_grad():
            base_params = [p.clone() for p in self.model.param_vector()]
            pre = float(
                self.loss_fn(self.model.functional_forward(query_x, base_params), query_y).item()
            )
        adapted = self.inner_loop(support_x, support_y, n_inner_steps)
        with torch.no_grad():
            post = float(
                self.loss_fn(self.model.functional_forward(query_x, adapted), query_y).item()
            )
        return {"pre_adaptation_loss": pre, "post_adaptation_loss": post}
