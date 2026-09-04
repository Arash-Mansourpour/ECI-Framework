"""Protocol-0 spec loading + strict validation (no external deps)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

try:
    import yaml as _yaml
except Exception:  # pragma: no cover
    _yaml = None

__all__ = ["ActionRule", "Protocol0Spec", "load_spec", "SPEC_PATH"]

SPEC_PATH = Path(__file__).resolve().parents[3] / "protocol0" / "spec.yaml"


@dataclass
class ActionRule:
    name: str
    min_awareness: float = 0.0
    min_obedience: float = 0.0
    min_trust: float = 0.0
    quorum: bool = False


@dataclass
class Protocol0Spec:
    protocol: str
    version: str
    architect: str
    actions: Dict[str, ActionRule] = field(default_factory=dict)
    max_divergence: float = 0.4
    min_coherence: float = 0.5
    max_attest_age_s: float = 300.0
    replay_window: int = 1024


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(f"protocol0 spec invalid: {msg}")


def load_spec(path: str | Path = SPEC_PATH) -> Protocol0Spec:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"protocol0 spec not found: {p}")
    if _yaml is None:
        raise ImportError("pyyaml is required to load protocol0 spec")
    raw: Dict[str, Any] = _yaml.safe_load(p.read_text(encoding="utf-8"))
    _require(raw.get("protocol") == "ECI-Protocol-0", "protocol != ECI-Protocol-0")
    _require(bool(raw.get("version")), "missing version")
    actions: Dict[str, ActionRule] = {}
    lst: List[Dict[str, Any]] = raw.get("actions", [])
    _require(bool(lst), "no actions defined")
    for a in lst:
        name = a.get("name", "")
        _require(bool(name) and name not in actions, f"bad/duplicate action {name!r}")
        for k in ("min_awareness", "min_obedience", "min_trust"):
            v = float(a.get(k, 0.0))
            _require(0.0 <= v <= 1.0, f"{name}.{k} out of [0,1]")
        actions[name] = ActionRule(
            name=name,
            min_awareness=float(a.get("min_awareness", 0.0)),
            min_obedience=float(a.get("min_obedience", 0.0)),
            min_trust=float(a.get("min_trust", 0.0)),
            quorum=bool(a.get("quorum", False)),
        )
    coll = raw.get("collective", {})
    att = raw.get("attestation", {})
    return Protocol0Spec(
        protocol="ECI-Protocol-0",
        version=str(raw["version"]),
        architect=str(raw.get("architect", "")),
        actions=actions,
        max_divergence=float(coll.get("max_divergence", 0.4)),
        min_coherence=float(coll.get("min_coherence", 0.5)),
        max_attest_age_s=float(att.get("max_age_s", 300)),
        replay_window=int(att.get("replay_window", 1024)),
    )
