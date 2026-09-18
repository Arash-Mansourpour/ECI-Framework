"""Adaptive vigilance: bounded, future-proof, no false positives on warmup."""

from eci.protocol_vigilance import AdaptiveVigilance


def test_vigilance_warmup_no_false_positive():
    v = AdaptiveVigilance(alpha=0.2, k=3.0)
    # first 5 updates should never flag (warmup)
    for i in range(5):
        rep = v.update({"phi": 0.5 + i * 0.01})
        assert rep["phi"]["anomaly"] is False
        assert rep["phi"]["predictive_anomaly"] is False


def test_vigilance_detects_spike():
    v = AdaptiveVigilance(alpha=0.2, k=3.0)
    for _ in range(10):
        v.update({"phi": 0.5})
    rep = v.update({"phi": 5.0})
    assert rep["phi"]["anomaly"] is True
    assert v.is_global_anomaly(rep, min_flags=1) is True


def test_vigilance_predictive():
    v = AdaptiveVigilance(alpha=0.2, k=2.0)
    for val in [0.5, 0.6, 0.7, 0.8, 0.9]:
        v.update({"lz": val})
    rep = v.update({"lz": 10.0})
    assert rep["lz"]["predictive_anomaly"] is True


def test_vigilance_bounded_history():
    v = AdaptiveVigilance(history=10)
    for i in range(20):
        v.update({"x": float(i)})
    assert len(v._states["x"].history) == 10
    assert v._states["x"].count == 20


def test_vigilance_global_threshold():
    v = AdaptiveVigilance()
    for _ in range(10):
        v.update({"a": 0.5, "b": 0.5})
    rep = v.update({"a": 5.0, "b": 5.0})
    assert v.is_global_anomaly(rep, min_flags=2) is True
    assert v.is_global_anomaly(rep, min_flags=3) is False
