"""Node lifecycle: architect-signed node creation and quantum signatures."""

from __future__ import annotations

import hashlib
import time
from typing import Dict, Optional

import torch

from eci.core.identity import ARCHITECT
from eci.core.types import ConsciousnessProfile, NetworkNode, NetworkRole
from eci.quantum.statevector import StatevectorSimulator

__all__ = ["NodeFactory"]


class NodeFactory:
    """Creates network nodes whose identity is bound to the sovereign architect."""

    def __init__(self, n_signature_qubits: int = 8, seed: Optional[int] = None) -> None:
        self.n_signature_qubits = n_signature_qubits
        self.seed = seed

    # ------------------------------------------------------------------
    def quantum_signature(self) -> str:
        """SHA-512 fingerprint of a random pure quantum state.

        The randomness comes from the quantum core's statevector simulator,
        tying node identity to the framework's quantum layer.
        """
        sim = StatevectorSimulator(self.n_signature_qubits)
        gen = torch.Generator().manual_seed(self.seed) if self.seed is not None else None
        state = sim.random_state(generator=gen)[0].detach()
        amplitudes = state.numpy().tobytes()
        return hashlib.sha512(amplitudes).hexdigest()

    # ------------------------------------------------------------------
    def create_node(
        self,
        role: NetworkRole,
        capabilities: Optional[Dict[str, float]] = None,
        consciousness_profile: Optional[ConsciousnessProfile] = None,
        trust_score: float = 1.0,
        reputation_score: float = 1.0,
        stake: float = 1.0,
        computational_power: float = 1.0,
        memory_capacity: float = 8.0,
        network_bandwidth: float = 100.0,
        seed: Optional[int] = None,
    ) -> NetworkNode:
        """Create a new node with architect-signed identity."""
        node_seed = seed if seed is not None else (self.seed if self.seed is not None else int(time.time() * 1e6) % (2 ** 31))
        node_id = ARCHITECT.derive_id("node", {"role": role.value, "seed": node_seed})
        signature = self.quantum_signature()
        return NetworkNode(
            node_id=node_id,
            role=role,
            consciousness_profile=consciousness_profile,
            quantum_signature=signature,
            capabilities=capabilities or {},
            trust_score=trust_score,
            reputation_score=reputation_score,
            stake=stake,
            contribution_history=[],
            model_weights_hash=None,
            last_heartbeat=time.time(),
            computational_power=computational_power,
            memory_capacity=memory_capacity,
            network_bandwidth=network_bandwidth,
            architect_stamp=ARCHITECT.stamp({"kind": "node_registration", "node_id": node_id}),
        )
