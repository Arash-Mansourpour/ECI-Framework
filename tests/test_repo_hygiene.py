"""Repo hygiene ratchet (Phase 17 §4): lock today's wins, bless nothing else.

What this gates: F401 (unused imports), I001 (import sorting), B011
(assert-False) are ZERO repo-wide as of this phase — this test fails if
any come back. Everything else (UP006/UP035 modernization ~1700 sites,
mypy 76 errors, E741/B007 style) is RECORDED in docs/CODEBASE_AUDIT.md
as backlog, deliberately NOT gated: retroactive full-tree gating would
force a disruptive clean sweep for zero behavior gain.

If you intentionally add a flagged pattern, update this test with a
comment explaining why — the gate tracks decisions, not just counts.
"""
import shutil
import subprocess
import sys


def _ruff():
    exe = shutil.which("ruff")
    if exe:
        return [exe]
    return [sys.executable, "-m", "ruff"]


def test_no_new_f401_i001_b011():
    try:
        out = subprocess.run([*_ruff(), "check", "--select", "F401,I001,B011",
                              "src", "tests", "--output-format", "concise"],
                             capture_output=True, text=True, timeout=300)
    except (FileNotFoundError, OSError):
        import pytest
        pytest.skip("ruff not installed")
        return
    lines = [l for l in out.stdout.splitlines() if l.strip() and "-->" not in l and "|" not in l[:2]]
    errors = [l for l in lines if ": F401" in l or ": I001" in l or ": B011" in l]
    assert errors == [], "\n".join(errors[:20])


def test_mypy_total_does_not_grow():
    """Ratchet on the mypy total (72 at Phase 17 audit, down from 76 after
    fixing the Envelope collision, pqc seed annotation, and 2 stale
    type-ignores): new errors fail, fixes just work. Slow (~1-2 min) —
    runs the real checker, no mocks."""
    try:
        out = subprocess.run([sys.executable, "-m", "mypy", "src/eci"],
                             capture_output=True, text=True, timeout=590)
    except (FileNotFoundError, OSError):
        import pytest
        pytest.skip("mypy not installed")
        return
    import re
    m = re.search(r"Found (\d+) errors?", out.stdout + out.stderr)
    assert m, "could not parse mypy output"
    assert int(m.group(1)) <= 72, out.stdout[-2000:]
