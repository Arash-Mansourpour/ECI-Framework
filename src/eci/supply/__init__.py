"""Supply-chain: CycloneDX-lite SBOM + source-tree fingerprint.

SBOM lists name/version for installed ECI-relevant distributions plus a
sha256 fingerprint over src/eci (first 4k files) for tamper-evidence.
No new dependencies: importlib.metadata + hashlib only. Output feeds
releases, audit and the transparency log.
"""

from __future__ import annotations

import hashlib
import importlib.metadata as _md
from pathlib import Path
from typing import Any

__all__ = ["sbom", "tree_fingerprint"]

_TRACKED = ("torch", "numpy", "scipy", "pyyaml", "cryptography", "pytest",
            "reportlab", "matplotlib", "stim", "pymatching", "networkx", "mne", "liboqs-python",
            "pyphi")


def sbom(root: Path | str | None = None) -> dict[str, Any]:
    comps: list[dict[str, Any]] = []
    for name in _TRACKED:
        try:
            comps.append({"name": name, "version": _md.version(name)})
        except _md.PackageNotFoundError:
            comps.append({"name": name, "version": None})
    fp = tree_fingerprint(root or Path(__file__).resolve().parents[2])
    return {"bomFormat": "CycloneDX-lite", "components": comps, "tree_sha256": fp,
            "count": len([c for c in comps if c["version"]])}


def tree_fingerprint(root: Path | str) -> str:
    h = hashlib.sha256()
    files = sorted(Path(root).rglob("*.py"))[:4000]
    for p in files:
        try:
            h.update(p.name.encode() + b"\0" + hashlib.sha256(p.read_bytes()).digest())
        except Exception:  # noqa: BLE001
            continue
    return h.hexdigest()
