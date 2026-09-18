"""Pin exact/tolerance values for metrics (Phase 6 weak-assertion fix)."""

import numpy as np
import torch

from eci.consciousness.metrics import (
    lempel_ziv_complexity,
    mutual_information,
    sample_entropy,
    spectral_entropy,
)


def test_lempel_ziv_pinned():
    data = np.tile([0, 1], 500)
    v = lempel_ziv_complexity(data)
    assert 0.0 <= v <= 1.0
    assert abs(v - 0.0299) < 0.01
    const = np.ones(1000)
    assert 0.0 <= lempel_ziv_complexity(const) <= 0.05
    assert lempel_ziv_complexity(np.array([])) == 0.0


def test_sample_entropy_pinned():
    torch.manual_seed(0)
    sine = torch.sin(torch.linspace(0, 20, 1000))
    v = sample_entropy(sine, m=2, r=0.2)
    assert abs(v - 0.024) < 0.01
    const = torch.ones(1000)
    assert sample_entropy(const) < 0.01
    rand = torch.randn(1000)
    vr = sample_entropy(rand)
    assert vr > v
    assert abs(vr - 1.0) < 1e-6


def test_spectral_entropy_pinned():
    torch.manual_seed(1)
    # pure sine → low entropy (peaked spectrum)
    t = torch.linspace(0, 10, 512)
    sine = torch.sin(2 * torch.pi * 5 * t).unsqueeze(1)
    vs = spectral_entropy(sine)
    assert 0.0 <= vs <= 1.0
    assert vs < 0.5
    # white noise → high entropy
    noise = torch.randn(512, 1)
    vn = spectral_entropy(noise)
    assert vn > vs


def test_mutual_information_pinned():
    torch.manual_seed(2)
    x = torch.randn(500)
    y = x.clone()  # perfect correlation
    mi_same = mutual_information(x, y)
    assert mi_same > 1.0
    z = torch.randn(500)
    mi_rand = mutual_information(x, z)
    assert mi_rand < mi_same
    assert mi_rand >= 0.0
