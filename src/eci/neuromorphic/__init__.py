"""Neuromorphic computing subsystem (LIF neurons + SNN with STDP)."""

from eci.neuromorphic.neurons import LIFNeuron
from eci.neuromorphic.snn import SpikingNeuralNetwork

__all__ = ["LIFNeuron", "SpikingNeuralNetwork"]
