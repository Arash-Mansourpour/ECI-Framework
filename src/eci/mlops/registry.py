"""Model registry: versioned artifacts with lineage + stage promotion."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

__all__ = ["ModelVersion", "ModelRegistry"]


@dataclass
class ModelVersion:
    name: str
    version: int
    params_hash: str
    metrics: Dict[str, float]
    lineage: Dict[str, Any]
    stage: str = "staging"  # staging | production | archived
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ModelRegistry:
    name = "model-registry"

    def __init__(self) -> None:
        self._models: Dict[str, List[ModelVersion]] = {}

    @staticmethod
    def _hash(params: Any) -> str:
        return hashlib.sha256(json.dumps(params, sort_keys=True, default=str).encode()).hexdigest()[:16]

    def register(self, name: str, params: Any, metrics: Dict[str, float],
                 lineage: Dict[str, Any] | None = None) -> ModelVersion:
        vers = self._models.setdefault(name, [])
        mv = ModelVersion(name=name, version=len(vers) + 1, params_hash=self._hash(params),
                          metrics=dict(metrics), lineage=lineage or {})
        vers.append(mv)
        return mv

    def promote(self, name: str, version: int, stage: str = "production") -> ModelVersion:
        for mv in self._models.get(name, []):
            if mv.version == version:
                if stage == "production":
                    for other in self._models[name]:
                        if other.stage == "production":
                            other.stage = "archived"
                mv.stage = stage
                return mv
        raise KeyError(f"{name} v{version} not found")

    def latest(self, name: str, stage: str = "") -> Optional[ModelVersion]:
        vers = [m for m in self._models.get(name, []) if not stage or m.stage == stage]
        return vers[-1] if vers else None

    def start(self) -> None: ...
    def stop(self) -> None: ...
    def health(self) -> Dict[str, Any]:
        return {"ok": True, "models": {k: len(v) for k, v in self._models.items()}}
