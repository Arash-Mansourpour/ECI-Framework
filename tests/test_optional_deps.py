"""Optional-dependency missing paths: mne / liboqs / networkx fallbacks.

No new dependencies: absence is simulated with monkeypatch (sys.modules
blocking, ``_OQS_AVAILABLE`` forcing), following the mock style of
tests/test_aikernel_phase10.py, so these pass whether or not the
optional extras are installed.
"""
import sys

import pytest

from eci.consciousness.eeg import read_mne_raw
from eci.protocol0.attest import architect_anchor_available
from eci.quantum.topological import SurfaceCode
from eci.security import pqc as pqc_module
from eci.supply import sbom


def test_mne_missing_raises_informative_importerror(monkeypatch):
    """read_mne_raw without the `eeg` extra refuses with an ImportError naming mne."""
    monkeypatch.setitem(sys.modules, "mne", None)
    with pytest.raises(ImportError, match="mne"):
        read_mne_raw("dummy.fif")


def test_pqc_without_oqs_reports_honest_fallback(monkeypatch):
    """Without liboqs, PQCSuite advertises hash-based only + HMAC anchor fallback."""
    monkeypatch.setattr(pqc_module, "_OQS_AVAILABLE", False)
    caps = pqc_module.PQCSuite().capabilities
    assert caps["hash_based_signatures"] is True
    assert caps["ml_kem_adapter"] is False
    assert caps["ml_dsa_adapter"] is False
    anchor = architect_anchor_available()
    assert anchor["available"] is False
    assert "HMAC" in anchor["mechanism"]


def test_topological_decoder_without_networkx_falls_back(monkeypatch):
    """mwpm without networkx still decodes via scipy Hungarian (<=8 triggers)."""
    monkeypatch.setitem(sys.modules, "networkx", None)
    s = SurfaceCode(3)
    syn = {"x_syndrome": [0, 1], "z_syndrome": [0, 1]}
    out = s.decode_correction(syn, decoder="mwpm")
    assert set(out) >= {"x_correction", "z_correction"}
    assert isinstance(out["x_correction"], list)
    assert isinstance(out["z_correction"], list)
    assert out["x_correction_hints"] == [0, 1]
    assert out["z_correction_hints"] == [0, 1]
    # Greedy path never needed networkx; still works while blocked.
    greedy = s.decode_correction(syn, decoder="greedy")
    assert isinstance(greedy["x_correction"], list)


def test_sbom_tracks_declared_optional_extras():
    """SBOM component list covers the optional extras (networkx/pyphi drift guard)."""
    names = {c["name"] for c in sbom()["components"]}
    assert {"networkx", "pyphi", "stim", "pymatching", "mne", "liboqs-python"} <= names
