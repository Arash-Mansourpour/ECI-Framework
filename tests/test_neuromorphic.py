"""Neuromorphic smoke (Phase 18): least-tested dynamics in the tree (22%).

Locks: LIF spiking semantics, reset, validation, surrogate gradients;
SNN shapes, STDP hand-check, weight clamps, input validation.
"""
import pytest
import torch


def test_lif_spikes_on_strong_current_silent_on_weak():
    from eci.neuromorphic.neurons import LIFNeuron
    n = LIFNeuron(4, batch_size=2)
    n.reset_state(2)
    strong = torch.full((2, 4), 5.0)
    fired = False
    for _ in range(50):  # membrane integrates: v -> ~5, crossing threshold 1.0
        if bool((n(strong) > 0).any()):
            fired = True
    assert fired, "sustained strong current must spike"
    n.reset_state(2)
    quiet = torch.zeros(2, 4)
    for _ in range(50):
        assert bool((n(quiet) == 0).all()), "no input must mean no spikes"
    with pytest.raises(ValueError):
        LIFNeuron(0)
    with pytest.raises(ValueError):
        LIFNeuron(4, tau_m=0.0)


def test_lif_surrogate_gradient_flows():
    from eci.neuromorphic.neurons import LIFNeuron
    n = LIFNeuron(3, batch_size=1, surrogate=True)
    n.reset_state(1)
    out = n(torch.full((1, 3), 0.9))
    out.sum().backward()
    assert n.weight.grad is not None


def test_snn_shapes_counts_and_validation():
    from eci.neuromorphic.snn import SpikingNeuralNetwork
    torch.manual_seed(0)
    net = SpikingNeuralNetwork(4, 6, 2)
    with pytest.raises(ValueError):
        SpikingNeuralNetwork(0, 6, 2)
    x = torch.rand(3, 4)
    counts = net(x, n_steps=20)
    assert counts.shape == (3, 2)
    assert bool((counts >= 0).all())
    with pytest.raises(ValueError):
        net(torch.rand(3, 5), n_steps=5)


def test_snn_stdp_hand_check_and_clamp():
    """pre=[1,0], post=[1,0], zero traces:
    dw = a+*[[1,0],[0,0]] - a-*[[1,0],[0,0]] = [[-0.002,0],[0,0]]."""
    from eci.neuromorphic.snn import SpikingNeuralNetwork
    net = SpikingNeuralNetwork(2, 2, 1)
    net.reset_state(1)
    dw = net.stdp_step(torch.tensor([1.0, 0.0]), torch.tensor([1.0, 0.0]))
    assert torch.allclose(dw, torch.tensor([[-0.002, 0.0], [0.0, 0.0]]), atol=1e-9), dw
    assert bool(((net.input_weights >= net.w_min) & (net.input_weights <= net.w_max)).all())


def test_snn_learn_mode_moves_weights():
    from eci.neuromorphic.snn import SpikingNeuralNetwork
    torch.manual_seed(1)
    net = SpikingNeuralNetwork(3, 4, 2)
    before = net.input_weights.detach().clone()
    net(torch.rand(2, 3), n_steps=15, learn=True)
    assert not torch.equal(before, net.input_weights)
    assert bool(((net.input_weights >= net.w_min) & (net.input_weights <= net.w_max)).all())
