"""Typed, validated configuration system (dataclasses + YAML/JSON)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

__all__ = [
    "QuantumConfig",
    "ConsciousnessConfig",
    "NetworkConfig",
    "LearningConfig",
    "ExperimentConfig",
    "ECIConfig",
]


@dataclass
class QuantumConfig:
    """Quantum core settings (v5: full-stack fault tolerance)."""

    n_qubits: int = 8
    dtype: str = "complex64"  # or "complex128"
    shots: int = 1024
    vqe_steps: int = 120
    vqe_lr: float = 0.05
    qaoa_depth: int = 2
    trotter_steps: int = 10
    # v5 additions: topological / metrology / field
    surface_distance: int = 3
    qec_code: str = "surface"  # surface | bb | shor | bitflip
    metrology_entangled: bool = True
    field_J: float = 0.25
    field_lambda_phi: float = 0.15
    field_consensus_J: float = 0.1

    def __post_init__(self) -> None:
        if not (1 <= self.n_qubits <= 24):
            raise ValueError(f"n_qubits must be in [1, 24], got {self.n_qubits}")
        if self.dtype not in ("complex64", "complex128"):
            raise ValueError(f"unsupported dtype: {self.dtype}")
        if self.qec_code not in ("surface", "bb", "shor", "bitflip"):
            raise ValueError(f"unknown qec_code: {self.qec_code}")


@dataclass
class ConsciousnessConfig:
    """Consciousness measurement settings (v5: multi-theory)."""

    phi_method: str = "gaussian"  # gaussian | discrete | quantum
    complexity_window: int = 1000
    mi_bins: int = 10
    measurement_frequency: float = 1000.0  # Hz (paper section 3.2.1)
    intervention_threshold: float = 10.0  # bits, Level 4 escalation
    gnwt_beta: float = 4.0
    gnwt_theta: float = 0.6
    free_energy_lr: float = 0.05

    def __post_init__(self) -> None:
        if self.phi_method not in ("gaussian", "discrete", "quantum"):
            raise ValueError(f"unknown phi method: {self.phi_method}")


@dataclass
class NetworkConfig:
    """Distributed network settings."""

    byzantine_rate: float = 0.05
    consensus_seed: int = 7
    min_join_phi: float = 0.05
    heartbeat_timeout_s: float = 300.0
    participation_fraction: float = 0.3

    def __post_init__(self) -> None:
        if not (0.0 <= self.byzantine_rate <= 1.0):
            raise ValueError("byzantine_rate must be in [0, 1]")


@dataclass
class LearningConfig:
    """Learning engines settings."""

    federated_privacy_epsilon: float = 1.0
    federated_clip_norm: float = 1.0
    federated_participation: float = 0.3
    maml_inner_lr: float = 0.01
    maml_outer_lr: float = 0.001
    maml_first_order: bool = False
    ewc_lambda: float = 0.4
    nas_search_epochs: int = 10


@dataclass
class ExperimentConfig:
    """Configuration for research experiments."""

    experiment_name: str = "ECI_Research_v5"
    random_seed: int = 42
    num_epochs: int = 100
    batch_size: int = 32
    learning_rate: float = 1e-3
    device: str = "auto"
    mixed_precision: bool = True
    gradient_accumulation_steps: int = 1
    checkpoint_frequency: int = 10
    early_stopping_patience: int = 20
    metrics: List[str] = field(default_factory=lambda: ["accuracy", "loss"])

    def __post_init__(self) -> None:
        if not self.experiment_name:
            raise ValueError("experiment_name must be non-empty")
        if self.gradient_accumulation_steps < 1:
            raise ValueError("gradient_accumulation_steps must be >= 1")


@dataclass
class ECIConfig:
    """Aggregate configuration for the whole framework."""

    quantum: QuantumConfig = field(default_factory=QuantumConfig)
    consciousness: ConsciousnessConfig = field(default_factory=ConsciousnessConfig)
    network: NetworkConfig = field(default_factory=NetworkConfig)
    learning: LearningConfig = field(default_factory=LearningConfig)
    experiment: ExperimentConfig = field(default_factory=ExperimentConfig)

    # ------------------------------------------------------------------
    # (de)serialization
    # ------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, path: Optional[Path] = None) -> str:
        text = json.dumps(self.to_dict(), indent=2, sort_keys=True)
        if path is not None:
            path = Path(path)
            path.write_text(text, encoding="utf-8")
        return text

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ECIConfig":
        return cls(
            quantum=QuantumConfig(**data.get("quantum", {})),
            consciousness=ConsciousnessConfig(**data.get("consciousness", {})),
            network=NetworkConfig(**data.get("network", {})),
            learning=LearningConfig(**data.get("learning", {})),
            experiment=ExperimentConfig(**data.get("experiment", {})),
        )

    @classmethod
    def from_yaml(cls, path: Path | str) -> "ECIConfig":
        path = Path(path)
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return cls.from_dict(data)

    @classmethod
    def from_json(cls, path: Path | str) -> "ECIConfig":
        path = Path(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(data)
