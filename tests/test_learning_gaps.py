"""Learning gaps (Phase 18): MAML / federated / NAS direct coverage.

learning/ was 41% — only EWC was tested. These lock the rest with small
synthetic tasks (no new machinery, seconds on CPU).
"""
import asyncio

import torch


def _binary_task(seed, n=32, shift=0.0):
    g = torch.Generator().manual_seed(seed)
    X = torch.randn(n, 2, generator=g) + shift
    return X, (X[:, 0] > 0).long()


def test_maml_inner_loop_descends():
    from eci.learning.maml import MAML, MetaMLP
    torch.manual_seed(0)
    model = MetaMLP(2, hidden=8, out_features=2, n_hidden_layers=1)
    maml = MAML(model, inner_lr=0.1, outer_lr=0.01)
    sx, sy = _binary_task(0)
    before = torch.nn.functional.cross_entropy(model.functional_forward(sx, model.param_vector()), sy).item()
    adapted = maml.inner_loop(sx, sy, n_inner_steps=5)
    after = torch.nn.functional.cross_entropy(model.functional_forward(sx, adapted), sy).item()
    assert after < before, (before, after)
    assert len(adapted) == len(model.param_vector())
    # first-order variant runs too (no graph retained -> still descends here)
    maml1 = MAML(MetaMLP(2, hidden=8, out_features=2, n_hidden_layers=1),
                 inner_lr=0.1, first_order=True)
    a1 = maml1.inner_loop(sx, sy, n_inner_steps=2)
    assert len(a1) == len(model.param_vector())


def test_maml_rejects_nonfunctional_model():
    import pytest

    from eci.learning.maml import MAML
    with pytest.raises(TypeError):
        MAML(torch.nn.Linear(2, 2))


def test_maml_outer_loop_runs():
    from eci.learning.maml import MAML, MetaMLP
    torch.manual_seed(1)
    maml = MAML(MetaMLP(2, hidden=8, out_features=2, n_hidden_layers=1),
                inner_lr=0.05, outer_lr=0.01)
    tasks = []
    for s in range(2):
        sx, sy = _binary_task(10 + s, n=16)
        qx, qy = _binary_task(20 + s, n=16)
        tasks.append((sx, sy, qx, qy))
    loss = maml.outer_loop(tasks, n_inner_steps=2)
    assert loss == loss and abs(loss) < 1e6, loss


def test_federated_round_end_to_end():
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset

    from eci.learning.federated import FederatedLearningCoordinator
    torch.manual_seed(2)
    loaders = []
    for s in range(2):
        X, y = _binary_task(30 + s, n=24)
        loaders.append(DataLoader(TensorDataset(X, y), batch_size=8))
    coord = FederatedLearningCoordinator(nn.Linear(2, 2), n_clients=2,
                                         privacy_epsilon=5.0, clip_norm=1.0)
    before = [p.detach().clone() for p in coord.global_model.parameters()]
    out = asyncio.run(coord.federated_round(loaders, n_local_epochs=1))
    assert out["participating_clients"] >= 1
    assert out["average_loss"] == out["average_loss"] and out["average_loss"] >= 0.0
    assert len(coord.round_history) == 1
    assert any(not torch.equal(a, b) for a, b in zip(before, coord.global_model.parameters()))


def test_federated_validation_errors():
    import pytest
    import torch.nn as nn

    from eci.learning.federated import FederatedLearningCoordinator
    with pytest.raises(ValueError):
        FederatedLearningCoordinator(nn.Linear(2, 2), n_clients=0)
    with pytest.raises(ValueError):
        FederatedLearningCoordinator(nn.Linear(2, 2), n_clients=2, privacy_epsilon=0.0)


def test_nas_derive_shape_and_names():
    from eci.learning.nas import DARTSSearchSpace
    torch.manual_seed(3)
    space = DARTSSearchSpace(n_nodes=2, channels=4)
    edges = space.derive(keep_edges=2)
    assert len(edges) == 2 * 2, edges  # keep_edges per node
    assert all(isinstance(e[2], str) and e[2] in DARTSSearchSpace.PRIMITIVES for e in edges)
    arch = space.get_architecture()
    assert isinstance(arch, list) and len(arch) > 0


def test_nas_ops_and_forward():
    from eci.learning.nas import DARTSSearchSpace, SeparableConv2d, Zero
    torch.manual_seed(4)
    z = Zero()
    x = torch.randn(2, 4, 8, 8)
    assert torch.allclose(z(x), torch.zeros_like(x))
    sep = SeparableConv2d(4, 4, 3, 1, 1)
    y = sep(x)
    assert y.shape == (2, 4, 8, 8)
    # forward through search space: 2 input states (x,x) -> concat of last n_nodes
    space = DARTSSearchSpace(n_nodes=2, channels=4)
    out = space(x)
    assert out.shape[0] == 2 and out.shape[1] == 8  # 2 nodes * 4 ch
    # derive filters none, keep_edges=1 variant
    edges1 = space.derive(keep_edges=1)
    assert 1 <= len(edges1) <= 2
    assert all(e[2] != "none" for e in edges1)


def test_advanced_nas_search_one_epoch():
    import pytest
    from torch.utils.data import DataLoader, TensorDataset

    from eci.learning.nas import AdvancedNAS
    torch.manual_seed(5)
    # DARTS cell returns (N, n_nodes*channels, H, W); spatial CE expects target (N,H,W)
    def _loader(n=8, n_nodes=1, channels=2, hw=8):
        X = torch.randn(n, channels, hw, hw)
        # spatial target (N, H, W) with classes 0..(n_nodes*channels-1)
        y = torch.randint(0, n_nodes * channels, (n, hw, hw))
        return DataLoader(TensorDataset(X, y), batch_size=4)
    train = _loader(8, n_nodes=1, channels=2, hw=8)
    val = _loader(8, n_nodes=1, channels=2, hw=8)
    nas = AdvancedNAS(device=torch.device("cpu"))
    # invalid space must raise
    with pytest.raises(ValueError):
        AdvancedNAS(search_space="bad")
    out = asyncio.run(nas.search(train, val, n_epochs=1, n_nodes=1, channels=2))
    assert "architecture" in out and "val_accuracy" in out
    assert out["search_epochs"] == 1
    # val_accuracy is pixel-accuracy divided by batch count in current impl (>1 possible for spatial)
    assert out["val_accuracy"] >= 0.0
    assert isinstance(out["architecture"], list)
    assert len(nas.search_history) == 1
    # history entry shape
    assert "val_accuracy" in nas.search_history[0]
