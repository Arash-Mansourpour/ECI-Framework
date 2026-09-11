"""MLOps facade.
Validation note: drift statistics are exact, their thresholds conventional;
drift is not wrongness (see docs/VALIDATION_STATUS.md)."""

from eci.mlops.drift import drift_report, ks_distance, psi
from eci.mlops.registry import ModelRegistry, ModelVersion

__all__ = ["ModelRegistry", "ModelVersion", "psi", "ks_distance", "drift_report", "MLOps"]


class MLOps:
    name = "mlops"

    def __init__(self) -> None:
        self.registry = ModelRegistry()

    def start(self) -> None: ...
    def stop(self) -> None: ...
    def health(self) -> dict:
        return {"ok": True, "registry": self.registry.health()}
