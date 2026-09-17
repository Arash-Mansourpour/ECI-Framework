"""Neuron atlas: advanced models spike sanely; atlas maps populations."""

import pytest
import torch


def test_adlif_spikes_and_adapts():
    from eci.neuromorphic.advanced import AdaptiveLIFNeuron

    n = AdaptiveLIFNeuron(4, batch_size=2)
    n.reset_state(2)
    strong = torch.full((2, 4), 5.0)
    fired = False
    for _ in range(50):
        if bool((n(strong) > 0).any()):
            fired = True
    assert fired
    assert bool((n.adaptation >= 0).all())
    with pytest.raises(ValueError):
        AdaptiveLIFNeuron(0)
    with pytest.raises(ValueError):
        AdaptiveLIFNeuron(4, tau_m=0.0)


def test_izhikevich_spikes_on_drive():
    from eci.neuromorphic.advanced import IzhikevichNeuron

    n = IzhikevichNeuron(3, batch_size=1)
    n.reset_state(1)
    drive = torch.full((1, 3), 20.0)
    fired = False
    for _ in range(60):
        if bool((n(drive) > 0).any()):
            fired = True
    assert fired
    with pytest.raises(ValueError):
        IzhikevichNeuron(0)


def test_homeostatic_threshold_tracks_rate():
    from eci.neuromorphic.advanced import HomeostaticLIFNeuron

    n = HomeostaticLIFNeuron(2, batch_size=1, target_rate=0.05)
    n.reset_state(1)
    before = n.threshold.clone()
    for _ in range(30):
        n(torch.full((1, 2), 5.0))
    assert not torch.equal(before, n.threshold)
    assert bool((n.threshold >= 0.2).all())


def test_homeostatic_reset_restores_initial_threshold():
    from eci.neuromorphic.advanced import HomeostaticLIFNeuron

    n = HomeostaticLIFNeuron(2, batch_size=1, target_rate=0.5, v_threshold_init=1.7)
    with torch.no_grad():
        n.weight.zero_()
    for _ in range(10):
        n(torch.zeros(1, 2))
    assert not torch.allclose(n.threshold, torch.full_like(n.threshold, 1.7))
    n.reset_state()
    assert torch.equal(n.threshold, torch.full_like(n.threshold, 1.7))
    n.reset_state(3)
    assert n.threshold.shape == (3, 2)
    assert torch.equal(n.threshold, torch.full_like(n.threshold, 1.7))


def test_homeostatic_reset_preserves_dtype():
    from eci.neuromorphic.advanced import HomeostaticLIFNeuron

    n = HomeostaticLIFNeuron(2, batch_size=1).double()
    n.reset_state()
    assert n.membrane_potential.dtype == torch.float64
    assert n.threshold.dtype == torch.float64
    assert n.spike_history.dtype == torch.float64
    out = n(torch.zeros(1, 2, dtype=torch.float64))
    assert out.dtype == torch.float64


def test_snn_neuron_types_backward_compat():
    from eci.neuromorphic.snn import SpikingNeuralNetwork

    torch.manual_seed(0)
    legacy = SpikingNeuralNetwork(4, 6, 2)
    assert legacy.neuron_type == "lif"
    for kind in ("adlif", "izhikevich", "homeostatic"):
        net = SpikingNeuralNetwork(4, 6, 2, neuron_type=kind)
        out = net(torch.rand(2, 4), n_steps=10)
        assert out.shape == (2, 2)
    with pytest.raises(ValueError):
        SpikingNeuralNetwork(4, 6, 2, neuron_type="hodgkin-huxley")


def test_atlas_register_summarize_export():
    from eci.neuromorphic.atlas import NeuronAtlas

    atlas = NeuronAtlas()
    atlas.register("snn-h", "neuromorphic", "snn.hidden", "hidden", "lif", 6)
    atlas.register("snn-o", "neuromorphic", "snn.output", "output", "adlif", 2)
    atlas.register("qn-o", "bridges.qn", "qn.output", "output", "izhikevich", 2)
    atlas.record_spikes("snn-h", 12)
    atlas.record_spikes("snn-o", 3)
    summary = atlas.summarize()
    assert summary["populations"] == 3
    assert summary["total_neurons"] == 10
    assert summary["total_spikes"] == 15
    assert summary["by_model"]["lif"] == 6
    d = atlas.to_dict()
    assert len(d["entries"]) == 3
    with pytest.raises(ValueError):
        atlas.register("bad", "x", "y", "z", "hh", 4)
    with pytest.raises(KeyError):
        atlas.record_spikes("missing", 1)
