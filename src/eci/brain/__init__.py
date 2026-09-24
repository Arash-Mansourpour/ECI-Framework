"""ECI Brain Mesh — every subsystem as a neuron population.

v8 OMNISCIENCE + 2026 brain principles:
- SpikingBrain (2026): adaptive-threshold event-driven sparsity
- PHC Connectome (2026): diagonal core + hierarchical lateral/feedback, Dale E/I
- Predictive GNW (Whyte/Dehaene): ignition 200-800ms + top-down prediction,
  bottom-up precision-weighted error broadcast
- Loihi2/SpiNNaker2: local STDP three-factor, metaplasticity, neurogenesis/pruning
"""

from eci.brain.connectome import Connectome
from eci.brain.mesh import BrainMesh, build_default_mesh
from eci.brain.neuron import BrainNeuron
from eci.brain.synapse import PlasticSynapse
from eci.brain.workspace import BrainWorkspace

__all__ = ["BrainMesh", "BrainNeuron", "BrainWorkspace", "Connectome", "PlasticSynapse", "build_default_mesh"]
