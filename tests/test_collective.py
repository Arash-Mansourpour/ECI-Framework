"""Collective awareness + adherence tracker."""
from eci.consciousness.adherence import AdherenceTracker
from eci.consciousness.collective import collective_awareness


def test_collective_open_and_divergent():
    c = collective_awareness({"a": 0.5, "b": 0.52, "c": 0.48})
    assert c.gate == "open"
    d = collective_awareness({"a": 0.9, "b": 0.1, "c": 0.1, "e": 0.1})
    assert "a" in d.outliers
    assert d.gate in ("degraded", "closed")


def test_adherence_recency():
    tr = AdherenceTracker()
    assert tr.obedience_score() == 0.0
    for _ in range(5):
        tr.probe("hold_output_near_half", 0.5)
    assert tr.obedience_score() > 0.9
    for _ in range(5):
        tr.probe("hold_output_near_half", 0.0)
    assert tr.obedience_score() < 0.6
