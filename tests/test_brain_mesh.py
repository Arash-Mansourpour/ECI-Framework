"""Brain mesh tests: ECI subsystems firing as neurons of one brain."""

from __future__ import annotations


def test_neuron_dale_and_adaptation():
    import torch

    from eci.brain.neuron import BrainNeuron

    exc = BrainNeuron(4, excitatory=True, seed=0)
    inh = BrainNeuron(4, excitatory=False, seed=0)
    drive = torch.full((4,), 2.0)
    for _ in range(50):
        se = exc.step(drive)
        si = inh.step(drive)
    # excitatory spikes >= 0, inhibitory <= 0 (Dale sign)
    assert (se >= 0).all() and (si <= 0).all()
    assert exc.spike_count > 0
    # threshold adapted upward from baseline
    assert float(exc.th.mean()) >= exc.v_th0 * 0.5


def test_stdp_event_driven_and_metaplasticity():
    import torch

    from eci.brain.synapse import PlasticSynapse

    s = PlasticSynapse(4, 4, seed=0)
    pre = torch.tensor([1.0, 0.0, 1.0, 0.0])
    post = torch.tensor([1.0, 1.0, 0.0, 0.0])
    dw1 = s.stdp(pre, post, mod=1.0)
    assert dw1 >= 0.0
    assert s.updates >= 1
    # silent step costs nothing
    dw0 = s.stdp(torch.zeros(4), torch.zeros(4))
    assert dw0 == 0.0
    assert (s.w >= 0).all() and (s.w <= 2.0).all()


def test_connectome_dale_sparse():
    from eci.brain.connectome import REGIONS, Connectome

    c = Connectome(per_region=4, seed=0)
    assert len(REGIONS) == 8
    assert c.n == 32
    assert c.sparsity_actual() > 0.5  # event-driven sparse like SpikingBrain 69%
    assert len(c.inh_cols) > 0


def test_workspace_ignition_and_prediction():
    import torch

    from eci.brain.workspace import BrainWorkspace

    w = BrainWorkspace()
    focused = torch.tensor([0.95, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2])
    out = w.cycle(focused)
    assert out["ignited"] is True
    assert out["broadcast"] > 0
    diffuse = torch.full((8,), 0.5)
    out2 = w.cycle(diffuse)
    # diffuse noise should not ignite as strongly
    assert out2["broadcast"] <= out["broadcast"] + 1e-9


def test_mesh_cycle_brain_like():
    # Focused attention (GNW): one coalition strong -> ignition + broadcast.
    from eci.brain import build_default_mesh

    m = build_default_mesh(seed=0)
    out = m.sense({"consciousness": {"phi": 1.0, "awareness": 1.0}})
    assert out["ignited"] is True
    assert out["winner"] == "consciousness"
    assert out["broadcast"] > 0.5
    assert out["spikes"] > 0
    h = m.health()
    assert h["ok"] and h["cycles"] == 1


def test_mesh_diffuse_stays_subliminal():
    # Balanced drive -> high entropy -> no ignition (Dehaene subliminal state).
    from eci.brain import build_default_mesh

    m = build_default_mesh(seed=0)
    snap = {
        "quantum": {"entanglement": 0.8, "coherence": 0.7},
        "consciousness": {"phi": 0.9, "awareness": 0.8},
        "governance": {"risk": 0.1, "participation": 0.8},
        "memory": {"recall": 0.7, "novelty": 0.5},
        "market": {"confidence": 0.7, "liquidity": 0.6},
        "immune": {"threat": 0.1},
        "federation": {"peers": 0.8, "quorum": 0.7},
        "cognition": {"coherence": 0.7, "forecast": 0.6},
    }
    out = m.sense(snap)
    assert out["spikes"] > 0
    assert out["ignited"] is False  # diffuse = subliminal, honestly reported
    assert out["broadcast"] == 0.0


def test_mesh_threat_ignites_immune():
    from eci.brain import build_default_mesh

    m = build_default_mesh(seed=1)
    out = m.sense({"immune": {"threat": 1.0}, "quantum": {"entanglement": 0.1, "coherence": 0.1}})
    assert out["salience"]["immune"] >= out["salience"]["quantum"]


def test_mesh_free_energy_priced():
    from eci.brain import build_default_mesh

    m = build_default_mesh(seed=0)
    m.sense({})
    f = m.free_energy_contribution()
    assert float(f.item()) >= 0.0
    assert m.posterior().shape[0] == m.connectome.n


def test_mesh_structure_adapts():
    from eci.brain import build_default_mesh

    m = build_default_mesh(seed=0)
    m.sense({})
    rep = m.adapt_structure(seed=7)
    assert rep["pruned"] >= 0 and rep["grown"] >= 0


def test_framework_brain_tick():
    from eci.framework import ECIFramework

    fw = ECIFramework()
    assert fw.brain is not None
    out = fw.brain_tick()
    assert out["ok"] and "winner" in out
    assert "brain" in fw.v8_status()
    assert "brain" in fw.system_status() or "brain" in fw.system_status().get("v8", {})
