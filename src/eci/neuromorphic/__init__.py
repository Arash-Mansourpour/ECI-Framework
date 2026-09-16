"""Neuromorphic computing subsystem (LIF/AdLIF/Izhikevich + SNN with STDP + atlas).
Validation note: research-prototype dynamics — treat outputs as exploratory
(see docs/VALIDATION_STATUS.md). Atlas maps populations; it never claims
biological equivalence."""

from eci.neuromorphic.advanced import AdaptiveLIFNeuron, HomeostaticLIFNeuron, IzhikevichNeuron
from eci.neuromorphic.atlas import MODEL_FAMILY, AtlasEntry, NeuronAtlas
from eci.neuromorphic.neurons import LIFNeuron
from eci.neuromorphic.snn import SpikingNeuralNetwork

__all__ = [
    "AdaptiveLIFNeuron",
    "AtlasEntry",
    "HomeostaticLIFNeuron",
    "IzhikevichNeuron",
    "LIFNeuron",
    "MODEL_FAMILY",
    "NeuronAtlas",
    "SpikingNeuralNetwork",
]
