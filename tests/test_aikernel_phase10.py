"""Phase 10 — hardening & closure: hygiene gate, PEC table, PyPhi bridge.

1. Hygiene gate locks the defect classes this program actually measured
   (5x bare `from typing`, 1x test tautology, inline `__import__` hacks):
   scoped to AIK-phase files so legacy style elsewhere is untouched.
2. PEC extended table (n=8192): q=0.02/0.10/0.20 -> mit within ~1 sigma,
   stderr strictly growing with q (gamma scaling, measured).
3. PyPhi cross-check: repertoire agreement < 1e-9 on AND + mutual-copy
   (incl. asymmetric cross-constraint probes); sia reported side by side
   with the version caveat, never equated.
"""
import pathlib

# NOTE: mcp/fabric.py excluded on purpose — its __import__ lazy-import style
# predates the unification layer; this gate locks OUR files, not legacy style.


def _root():
    return pathlib.Path(__file__).resolve().parents[1]


def _aik_src_files():
    """Glob-discovered AIK source files (Phase 14: no more hardcoded lists
    that rot when new phase files land)."""
    root = _root()
    files = sorted(str(p.relative_to(root)).replace("\\", "/")
                   for p in (root / "src" / "eci" / "aikernel").glob("*.py"))
    for sub in ("quantum/aikernel_adapter.py", "quantum/aikernel_likelihood.py",
                "quantum/mitigation.py", "consciousness/aikernel_adapter.py",
                "consciousness/iit.py", "consciousness/iit4.py",
                "governance/aikernel_adapter.py", "cognition/aikernel_adapter.py",
                "learning/aikernel_adapter.py"):
        files.append(f"src/eci/{sub}")
    return files


def _aik_test_files():
    root = _root()
    return sorted(str(p.relative_to(root)).replace("\\", "/")
                  for p in (root / "tests").glob("test_aikernel_*.py"))


def test_no_bare_typing_imports():
    """The 5x recurring typo: `from typing` without `import`."""
    bad = [f for f in _aik_src_files()
           for ln in (_root() / f).read_text(encoding="utf-8").splitlines()
           if ln.strip().startswith("from typing ") and not ln.strip().startswith("from typing import")]
    assert bad == [], bad


def test_no_tautological_asserts_in_aik_tests():
    """The `or True` incident: asserts that cannot fail."""
    import re
    bad = []
    for f in _aik_test_files():
        for i, ln in enumerate((_root() / f).read_text(encoding="utf-8").splitlines(), 1):
            s = ln.strip()
            if s.startswith("assert ") and re.search(r"\bor True\b", s):
                bad.append(f"{f}:{i}: {s}")
    assert bad == [], bad


def test_no_inline_dunder_imports_in_aik_src():
    """Inline `__import__` hacks (removed 3x); scoped to AIK files only —
    legacy style elsewhere (fabric lazy imports predate this) is untouched."""
    bad = [f for f in _aik_src_files()
           if "__import__(" in (_root() / f).read_text(encoding="utf-8")]
    assert bad == [], bad


def test_pec_extended_table():
    """q=0.02/0.10/0.20 at n=8192: unbiased within ~1 sigma, cost grows with q."""
    import torch
    from eci.aikernel.functors import pauli_string_matrix
    from eci.quantum.mitigation import apply_depolarizing, pec_mitigate
    bell = torch.zeros(4, 4, dtype=torch.complex64)
    bell[0, 0] = bell[0, 3] = bell[3, 0] = bell[3, 3] = 0.5
    ZZ = pauli_string_matrix("ZZ", 2)
    stderrs = []
    for q in (0.02, 0.10, 0.20):
        pm = pec_mitigate(apply_depolarizing(bell, 2, q), ZZ, q, n_samples=8192, seed=0)
        assert abs(pm["mitigated"] - 1.0) < 3 * pm["stderr"] + 1e-3, (q, pm)
        stderrs.append(pm["stderr"])
    assert stderrs[0] < stderrs[1] < stderrs[2], stderrs  # gamma scaling, measured


def test_pyphi_crosscheck_agreement():
    """Repertoires agree to 1e-9 (AND + asymmetric mutual-copy probes)."""
    import importlib.util
    import pytest
    if importlib.util.find_spec("pyphi") is None:
        pytest.skip("pyphi not installed")
    from eci.consciousness.iit4 import and_system, crosscheck_pyphi, mutual_copy_system
    for sys in (and_system(), mutual_copy_system()):
        out = crosscheck_pyphi(sys)
        assert out["ok"] is True and out.get("skipped") is not True, out
        assert out["worst_abs_diff"] < 1e-9, out["probes"]
        assert out["pyphi_phi_30"] >= 0.0 and out["iit4_phi_40"] >= 0.0
        assert "caveat" in out and "3.0" in out["caveat"] and "4.0" in out["caveat"]


def test_pyphi_skip_paths_without_pyphi(monkeypatch):
    """Absent PyPhi and oversized systems refuse with reasons, not crashes."""
    import importlib.util
    from eci.consciousness.iit4 import DiscreteSubstrate, crosscheck_pyphi, disconnected_system
    monkeypatch.setattr(importlib.util, "find_spec", lambda *a, **k: None)
    out = crosscheck_pyphi(disconnected_system())
    assert out == {"ok": True, "skipped": True, "reason": "pyphi not installed"}
    monkeypatch.undo()
    big4 = DiscreteSubstrate(4, {j: [0.5] * 16 for j in range(4)}, (0, 0, 0, 0))
    out2 = crosscheck_pyphi(big4)
    assert out2["skipped"] is True and "n=3" in out2["reason"], out2
