"""Consciousness measurement subsystem (IIT 4.0 + GNWT + FEP + iPDF + quantum-mind)."""

from eci.consciousness.adherence import AdherenceTracker, calibration_tasks
from eci.consciousness.analyzer import AdvancedConsciousnessAnalyzer
from eci.consciousness.challenge import Transcript, grade
from eci.consciousness.challenge import issue as issue_challenges
from eci.consciousness.collective import CollectiveState, collective_awareness
from eci.consciousness.eeg import bandpower, load_timeseries
from eci.consciousness.free_energy import FreeEnergyAgent, expected_free_energy
from eci.consciousness.gnwt import GNWTWorkspace, gnwt_ignition_curve
from eci.consciousness.iit import IntegratedInformationTheory, sample_neural_state
from eci.consciousness.iit4 import (
    DiscreteSubstrate,
    cause_repertoire,
    crosscheck_pyphi,
    distinction,
    effect_repertoire,
    intrinsic_information,
    phi_structure,
    relation_phi,
)
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

__all__ = [
    "IntegratedInformationTheory",
    "sample_neural_state",
    "DiscreteSubstrate",
    "cause_repertoire",
    "effect_repertoire",
    "intrinsic_information",
    "distinction",
    "relation_phi",
    "phi_structure",
    "crosscheck_pyphi",
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
    "Transcript",
    "grade",
    "issue_challenges",
    "lempel_ziv_complexity",
    "sample_entropy",
    "spectral_entropy",
    "mutual_information",
    "autocorrelation",
]
