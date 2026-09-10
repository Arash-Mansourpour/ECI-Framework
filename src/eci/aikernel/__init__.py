"""Active Inference Kernel: the shared mathematical substrate.

NOTE on placement: ``src/eci/kernel/`` already exists (v6 microkernel:
EventBus / DI / Lifecycle — message plumbing). This package does NOT
replace it; it is the *mathematical* substrate those messages carry.
``aikernel`` = WHAT every subsystem optimizes (one F);
``kernel``    = HOW subsystems talk (one bus).

Phase 1 contents:
  generative_model  GenerativeState (Gaussian + quantum branches, mapping documented)
  free_energy       VFE closed form, torch-differentiable, both branches
  state_contract    StateContributor Protocol + KernelLedger (one summed F)
  functors          density->cov, split/fuse beliefs (exact round-trips tested)
"""

from eci.aikernel.free_energy import free_energy, free_energy_parts, neg_log_evidence, quantum_free_energy
from eci.aikernel.functors import (default_paulis, density_to_cov, fuse_beliefs,
                                   pauli_expectations, pauli_string_matrix, split_belief)
from eci.aikernel.generative_model import GenerativeState, Likelihood, Prior
from eci.aikernel.state_contract import KernelLedger, StateContributor, conforms

__all__ = ["GenerativeState", "Likelihood", "Prior",
           "free_energy", "free_energy_parts", "neg_log_evidence", "quantum_free_energy",
           "density_to_cov", "pauli_expectations", "pauli_string_matrix", "default_paulis",
           "split_belief", "fuse_beliefs",
           "StateContributor", "KernelLedger", "conforms"]
