"""Repo hygiene ratchet (Phase 17 §4, Phase 18 version pin): lock today's wins.

What this gates: F401 (unused imports), I001 (import sorting), B011
(assert-False) are ZERO repo-wide — this test fails if any come back.
Everything else (UP006/UP035 modernization ~1700 sites, mypy 72 errors,
E741/B007 style) is RECORDED in docs/CODEBASE_AUDIT.md as backlog,
deliberately NOT gated: retroactive full-tree gating would force a
disruptive clean sweep for zero behavior gain.

Phase 18 addition: README version must match src/eci/version.py
(single source of truth, 7.1.0-PROTOCOL-vNext). The gate tracks
decisions, not just counts — if you intentionally add a flagged pattern,
update this test with a comment explaining why.
"""
import pathlib
import re
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
    m = re.search(r"Found (\d+) errors?", out.stdout + out.stderr)
    assert m, "could not parse mypy output"
    assert int(m.group(1)) <= 72, out.stdout[-2000:]


def test_readme_version_matches_code():
    """Phase 18: README title/badge must match src/eci/version.py."""
    root = pathlib.Path(__file__).resolve().parents[1]
    ver_file = root / "src" / "eci" / "version.py"
    text = ver_file.read_text(encoding="utf-8")
    m = re.search(r'__version__\s*=\s*"([^"]+)"', text)
    assert m, "could not parse __version__ from src/eci/version.py"
    ver = m.group(1).strip()
    # also check FRAMEWORK_VERSION major matches?
    readme = (root / "README.md").read_text(encoding="utf-8")
    # README title: "# 🌌 ECI Framework v7.1" — must contain ver or major.minor
    assert ver in readme, f"README does not mention code version {ver!r}"
    # badge must also contain ver
    assert f"version-{ver}" in readme or f"version-{ver.split('.')[0]}.{ver.split('.')[1]}" in readme, \
        f"README badge does not contain version {ver!r}"
    # title line must match
    title_m = re.search(r"#.*ECI Framework v([\d\.]+)", readme)
    assert title_m, "could not find README title version"
    title_ver = title_m.group(1)
    # allow v7.1 title for 7.1.0 code (minor match)
    assert ver.startswith(title_ver) or title_ver.startswith(ver) or ver.split(".")[:2] == title_ver.split(".")[:2], \
        f"README title v{title_ver} diverges from code v{ver}"
