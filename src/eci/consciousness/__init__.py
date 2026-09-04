"""Consciousness measurement subsystem (IIT 4.0 + GNWT + FEP + iPDF + quantum-mind)."""

from eci.consciousness.analyzer import AdvancedConsciousnessAnalyzer
from eci.consciousness.free_energy import FreeEnergyAgent, expected_free_energy
from eci.consciousness.gnwt import GNWTWorkspace, gnwt_ignition_curve
from eci.consciousness.iit import IntegratedInformationTheory
from eci.consciousness.metrics import (
    autocorrelation,
    lempel_ziv_complexity,
    mutual_information,
    sample_entropy,
    spectral_entropy,
)
from eci.consciousness.protocol import (
    ConsciousnessMeasurement,
    ConsciousnessProtocol,
    awareness_index_from_bits,
)
from eci.consciousness.quantum_mind import OrchORConfig, quantum_mind_audit
from eci.consciousness.eeg import load_timeseries, bandpower
from eci.consciousness.collective import CollectiveState, collective_awareness
from eci.consciousness.adherence import AdherenceTracker, calibration_tasks

__all__ = [
    "IntegratedInformationTheory",
    "AdvancedConsciousnessAnalyzer",
    "ConsciousnessProtocol",
    "ConsciousnessMeasurement",
    "awareness_index_from_bits",
    "GNWTWorkspace",
    "gnwt_ignition_curve",
    "FreeEnergyAgent",
    "expected_free_energy",
    "OrchORConfig",
    "quantum_mind_audit",
    "load_timeseries",
    "bandpower",
    "CollectiveState",
    "collective_awareness",
    "AdherenceTracker",
    "calibration_tasks",
    "lempel_ziv_complexity",
    "sample_entropy",
    "spectral_entropy",
    "mutual_information",
    "autocorrelation",
]
