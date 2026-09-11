"""Neuromorphic computing subsystem (LIF neurons + SNN with STDP).
Validation note: research-prototype dynamics at 22% test coverage —
treat outputs as exploratory (see docs/VALIDATION_STATUS.md)."""

from eci.neuromorphic.neurons import LIFNeuron
from eci.neuromorphic.snn import SpikingNeuralNetwork

__all__ = ["LIFNeuron", "SpikingNeuralNetwork"]
