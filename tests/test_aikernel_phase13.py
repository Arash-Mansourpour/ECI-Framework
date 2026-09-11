"""Phase 13 — EWC full cycle: two tasks, batch vs online Fisher semantics.

Measured (seeded, Linear(2,2), 64 samples/task): batch Fisher task1
0.8077 -> task2-only 15.7922; online accumulates 8.3399 -> 40.9218.
"""
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset


def _task(shift, n=64, seed=0):
    g = torch.Generator().manual_seed(seed)
    X = torch.randn(n, 2, generator=g) + shift
    return DataLoader(TensorDataset(X, (X[:, 0] > 0).long()), batch_size=16)


def test_batch_fisher_is_task_only():
    """Non-online mode replaces: Fisher after task2 == fresh Fisher on task2."""
    from eci.learning.continual import ElasticWeightConsolidation
    torch.manual_seed(0)
    e = ElasticWeightConsolidation(nn.Linear(2, 2), lambda_ewc=0.4, online=False)
    e.compute_fisher(_task(0.0))
    e.update_optimal_params()
    e.compute_fisher(_task(2.0))
    torch.manual_seed(0)
    ref = ElasticWeightConsolidation(nn.Linear(2, 2), lambda_ewc=0.4, online=False)
    ref.compute_fisher(_task(2.0))
    for k in e.fisher_dict:
        assert torch.allclose(e.fisher_dict[k], ref.fisher_dict[k], atol=1e-6), k


def test_online_fisher_accumulates_with_decay():
    """Online mode: F <- gamma*F + RAW SUM of squared grads (no /n mean).

    Finding (not assumption): online and batch Fisher live on different
    scales — batch divides by n_samples (mean), online accumulates raw
    sums. So λ_ewc is NOT comparable across modes; the identity below
    uses the unnormalized ref (x64 samples). Reported, not hidden.
    """
    from eci.learning.continual import ElasticWeightConsolidation
    torch.manual_seed(0)
    e = ElasticWeightConsolidation(nn.Linear(2, 2), lambda_ewc=0.4, online=True, gamma=0.5)
    e.compute_fisher(_task(0.0))
    f1 = {k: v.clone() for k, v in e.fisher_dict.items()}
    e.compute_fisher(_task(2.0))
    torch.manual_seed(0)
    ref = ElasticWeightConsolidation(nn.Linear(2, 2), lambda_ewc=0.4, online=False)
    ref.compute_fisher(_task(2.0))
    for k in e.fisher_dict:
        expect = 0.5 * f1[k] + 64.0 * ref.fisher_dict[k]  # 64 samples, mean->sum
        assert torch.allclose(e.fisher_dict[k], expect, atol=1e-4), k


def test_contributor_tracks_cycle_in_ledger():
    """Contributor share follows consolidate(); ledger stays exact."""
    from eci.aikernel.state_contract import KernelLedger
    from eci.governance.aikernel_adapter import AgentContributor
    from eci.learning.aikernel_adapter import EWCContributor
    from eci.learning.continual import ElasticWeightConsolidation
    torch.manual_seed(0)
    c = EWCContributor(ElasticWeightConsolidation(nn.Linear(2, 2)))
    ag = AgentContributor("gov-13", 1, obs_noise=0.5)
    led = KernelLedger()
    led.register("ewc", c)
    led.register("gov", ag)
    assert float(c.free_energy_contribution().item()) == 0.0
    rep = c.consolidate(_task(0.0))
    assert rep["fisher_total"] > 0.0
    flat = torch.cat([p.detach().reshape(-1) for p in c.ewc.model.parameters()])
    with torch.no_grad():
        for p in c.ewc.model.parameters():
            p.add_(0.25)
    # perturbed WITHOUT update: deviation priced (> 0, == engine loss)
    assert led.shares()["ewc"] > 0.0
    assert abs(led.shares()["ewc"] - float(c.ewc.ewc_loss().item())) < 1e-9
    # update() ADOPTS the perturbed params as the new optimum -> share resets
    c.update(flat + 0.25)
    assert float(c.free_energy_contribution().item()) == 0.0
    ag.update(torch.tensor([0.1]))
    total = float(led.total_free_energy().detach().item())
    assert abs(total - sum(led.shares().values())) < 1e-6
