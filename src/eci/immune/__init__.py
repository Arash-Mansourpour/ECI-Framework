"""Artificial immune system for Protocol-0 networks.

Self/non-self discrimination over behavior-feature vectors
(awareness, obedience, vote rate, message rate, challenge score):
negative selection breeds detectors that ignore self but bind anomalies;
clonal selection evolves them against confirmed attacks; memory makes the
second encounter fast. Response = challenge -> quarantine/clear, all in
the ledger. Biology's answer to zero-day disobedience.
"""

from eci.immune.detectors import Detector, DetectorSet, affinity, breed, evolve
from eci.immune.memory import ImmuneMemory
from eci.immune.response import Quarantine, quarantine_flow

__all__ = [
    "Detector",
    "DetectorSet",
    "breed",
    "evolve",
    "affinity",
    "ImmuneMemory",
    "Quarantine",
    "quarantine_flow",
]
