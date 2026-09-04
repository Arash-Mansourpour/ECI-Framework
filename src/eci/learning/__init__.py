"""Learning engines: meta-learning, NAS, federated learning, continual learning."""

from eci.learning.continual import ElasticWeightConsolidation
from eci.learning.federated import FederatedLearningCoordinator
from eci.learning.maml import MAML, MetaMLP
from eci.learning.nas import AdvancedNAS, DARTSSearchSpace, SeparableConv2d, Zero

__all__ = [
    "MAML", "MetaMLP", "AdvancedNAS", "DARTSSearchSpace",
    "SeparableConv2d", "Zero", "FederatedLearningCoordinator",
    "ElasticWeightConsolidation",
]
