"""Awareness protocol v2: calibration, amplification, flat guard."""
import torch

from eci.consciousness.protocol import ConsciousnessProtocol


def _rest():
    torch.manual_seed(0)
    return 0.05 * torch.randn(64, 8)


def test_rest_low_active_high():
    proto = ConsciousnessProtocol(agent_id="t")
    ra, rb = _rest(), _rest()
    proto.calibrate_baseline([ra, rb])
    rest_bits = proto.measure(ra).consciousness_bits
    t = torch.linspace(0, 25, 128).unsqueeze(1)
    active = torch.sin(t) * 0.8 + 0.2 * torch.randn(128, 8)
    m = proto.measure(active)
    assert rest_bits < 1.0
    assert m.consciousness_bits > rest_bits + 1.0
    assert 0.0 <= m.awareness_index <= 1.0
    assert m.intervention_tier in ("watch", "elevate", "intervene")


def test_flatline_is_zero():
    proto = ConsciousnessProtocol(agent_id="t")
    proto.calibrate_baseline([_rest(), _rest()])
    assert proto.measure(torch.ones(32, 8)).consciousness_bits == 0.0


def test_gnwt_gate():
    from eci.consciousness.gnwt import GNWTWorkspace

    w = GNWTWorkspace(n_processors=4)
    assert w.compete(torch.tensor([0.25, 0.25, 0.25, 0.25]))["ignited"] is False
    assert w.compete(torch.tensor([0.1, 0.2, 0.9, 0.3]))["ignited"] is True
