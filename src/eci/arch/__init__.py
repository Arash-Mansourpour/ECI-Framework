"""ECI Architecture Governance (v8 OMNISCIENCE).

Fitness functions + ADR registry. The architect's ratchet:
every new feature must keep these green.
"""

from eci.arch.adr import ADR_REGISTRY, get_adr, list_adrs
from eci.arch.fitness import FitnessResult, run_fitness

__all__ = ["ADR_REGISTRY", "FitnessResult", "get_adr", "list_adrs", "run_fitness"]
