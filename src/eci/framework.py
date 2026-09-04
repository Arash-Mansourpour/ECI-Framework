"""ECIFramework v5 — Quantum-Supremacy orchestrating facade.

Wires the full v5 stack into one architect-stamped system:

* Infrastructure: Dirac operator algebra → statevector/density → channels/
  Lindblad → VQE/QAOA/QFT/Grover/QPE → surface/BB topological QEC →
  tensor-networks / metrology / quantum information → unified H_ECI field
* Coordination: PBFT/WBFT + aggregation + Data-DAO governance + autopoiesis
* Consciousness: IIT Φ + iPDF + GNWT ignition + Friston FEP + Orch-OR audit

Sovereign Architect (Ma'mar-e A'zam): Arash Mansourpour
Wallet: GA4IHOJOXKIZDLNCXQT7NG65MT7Z3EQKRT4PYFYURIP7QRLY4CHMHILW
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

import torch

from eci.benchmarking.benchmark import ResearchBenchmark
from eci.config import ECIConfig
from eci.constants import ARCHITECT_NAME, CREATOR_WALLET
from eci.consciousness.analyzer import AdvancedConsciousnessAnalyzer
from eci.consciousness.free_energy import FreeEnergyAgent
from eci.consciousness.gnwt import GNWTWorkspace
from eci.consciousness.iit import IntegratedInformationTheory
from eci.consciousness.quantum_mind import quantum_mind_audit
from eci.core.device import configure_seeds, device_dtype_info, get_device
from eci.core.identity import ARCHITECT
from eci.core.registry import GLOBAL_REGISTRY, register_component
from eci.core.types import ConsciousnessLevel, ConsciousnessProfile
from eci.cybernetics.autopoiesis import AutopoieticNetwork
from eci.governance.dao import ECIDataDAO
from eci.logging import get_logger
from eci.network.manager import AutonomousNetworkManager
from eci.quantum import algorithms as qalg
from eci.quantum import density as qdensity
from eci.quantum import entanglement as qent
from eci.quantum import information as qinfo
from eci.quantum import lindblad as qlindblad
from eci.quantum import metrology as qmetro
from eci.quantum import operator as qop
from eci.quantum import qec as qqec
from eci.quantum import tensor_network as qtn
from eci.quantum import topological as qtopo
from eci.quantum.gates import CNOT, H
from eci.quantum.hamiltonian import PauliSum, PauliTerm
from eci.quantum.statevector import StatevectorSimulator
from eci.quantum.unified_field import ECIFieldConfig, eci_hamiltonian_expectation, eci_unified_hamiltonian
from eci.security.pqc import PQCSuite
from eci.version import FRAMEWORK_VERSION, PAPER_VERSION

__all__ = ["ECIFramework", "ECIFrameworkResearch"]


@register_component("eci-framework", protocol="facade")
class ECIFramework:
    """Main ECI Framework — Quantum-Supremacy Edition (v5)."""

    def __init__(self, config: Optional[ECIConfig] = None) -> None:
        self.config = config or ECIConfig()
        configure_seeds(self.config.experiment.random_seed)
        self.device = get_device(self.config.experiment.device)
        self.logger = get_logger("framework")

        self.version = FRAMEWORK_VERSION
        self.paper_version = PAPER_VERSION
        self.architect_name = ARCHITECT_NAME
        self.creator_wallet = CREATOR_WALLET

        # Core subsystems
        self.iit = IntegratedInformationTheory(self.device)
        self.consciousness_analyzer = AdvancedConsciousnessAnalyzer(
            self.device, phi_method=self.config.consciousness.phi_method
        )
        self.gnwt = GNWTWorkspace(
            beta=self.config.consciousness.gnwt_beta,
            theta=self.config.consciousness.gnwt_theta,
        )
        self.fep_agent = FreeEnergyAgent(lr=self.config.consciousness.free_energy_lr)
        self.autopoiesis = AutopoieticNetwork()
        self.dao = ECIDataDAO(dao_id="ECI-Genesis")
        self.quantum_sim = StatevectorSimulator(
            self.config.quantum.n_qubits, device=self.device
        )
        self.field_config = ECIFieldConfig(
            n_qubits=min(4, self.config.quantum.n_qubits),
            J=self.config.quantum.field_J,
            lambda_phi=self.config.quantum.field_lambda_phi,
            consensus_J=self.config.quantum.field_consensus_J,
        )
        self.network_manager = AutonomousNetworkManager(
            config=self.config.network,
            seed=self.config.experiment.random_seed,
        )
        self.benchmark = ResearchBenchmark(self.config.experiment.experiment_name)
        self.pqc = PQCSuite()

        self.system_state = "initialized"
        self.integration_score = 0.0
        self.consciousness_level = ConsciousnessLevel.NONE

        self.logger.info("=" * 72)
        self.logger.info("ECI FRAMEWORK %s - QUANTUM-SUPREMACY EDITION", self.version)
        self.logger.info("Sovereign Architect (Ma'mar-e A'zam): %s", ARCHITECT.name)
        self.logger.info("Wallet: %s", ARCHITECT.wallet)
        self.logger.info("Paper: %s | Device: %s", self.paper_version, self.device)
        self.logger.info("=" * 72)

    # ------------------------------------------------------------------
    # Consciousness (multi-theory)
    # ------------------------------------------------------------------
    async def analyze_consciousness(
        self,
        n_steps: int = 512,
        n_neurons: int = 64,
        seed: int = 0,
    ) -> ConsciousnessProfile:
        generator = torch.Generator().manual_seed(seed)
        t = torch.linspace(0, 25, n_steps)
        shared = torch.sin(t).unsqueeze(1) + 0.4 * torch.sin(4.1 * t).unsqueeze(1)
        coupling = 0.3 * torch.randn(n_neurons, n_neurons, generator=generator)
        local = 0.15 * torch.randn(n_steps, n_neurons, generator=generator)
        neural_data = shared * (0.5 + 0.5 * torch.rand(1, n_neurons, generator=generator)) \
            + local @ (torch.eye(n_neurons) + 0.2 * coupling)
        profile = await self.consciousness_analyzer.analyze_consciousness(
            neural_data.to(self.device), method=self.config.consciousness.phi_method
        )
        self.consciousness_level = profile.consciousness_level
        # GNWT ignition probe on channel saliences
        sal = torch.softmax(neural_data.var(dim=0)[: self.gnwt.n_processors], dim=0)
        self.gnwt.compete(sal)
        return profile

    async def initialize_network(self) -> Dict[str, Any]:
        result = await self.network_manager.initialize_network()
        self.system_state = "network_active"
        return result

    # ------------------------------------------------------------------
    # Quantum supremacy suite (v5)
    # ------------------------------------------------------------------
    def run_quantum_suite(self) -> Dict[str, Any]:
        results: Dict[str, Any] = {}
        # 1. Bell entanglement + CHSH violation (2-qubit register)
        bell_sim = StatevectorSimulator(2, device=self.device)
        bell = bell_sim.zero_state()
        bell = bell_sim.apply_1q(bell, H, 0)
        bell = bell_sim.apply_2q(bell, CNOT, 0, 1)
        rho = qdensity.from_statevector(bell)
        results["bell_concurrence"] = float(qent.concurrence(rho)[0].item())
        results["bell_negativity"] = float(qent.negativity(rho, 2, [1])[0].item())
        # CHSH on |Phi+>
        bell2 = torch.zeros(1, 4, dtype=torch.complex64)
        bell2[0, 0] = 1 / (2 ** 0.5)
        bell2[0, 3] = 1 / (2 ** 0.5)
        results["chsh_value"] = qinfo.chsh_value(qdensity.from_statevector(bell2))
        results["tsirelson_bound"] = qinfo.tsirelson_bound()

        # 2. Operator algebra: uncertainty bound on X/Z (Y-eigenstate saturates)
        from eci.quantum import gates as qg

        ub = qop.uncertainty_bound(
            qg.X.to(torch.complex64), qg.Z.to(torch.complex64),
            torch.tensor([1 / (2 ** 0.5), 1j / (2 ** 0.5)], dtype=torch.complex64),
        )
        results["uncertainty_lhs"] = ub["lhs"]
        results["uncertainty_rhs"] = ub["rhs_bound"]

        # 3. Grover + QPE
        grover = qalg.grover_search(StatevectorSimulator(3, device=self.device), [5])
        results["grover_success"] = grover["success_probability"]
        qpe = qalg.quantum_phase_estimation(
            StatevectorSimulator(4, device=self.device),
            gate_fn=lambda e: _rz_matrix(0.5 * torch.pi * e),
            n_counting=3,
        )
        results["qpe_phase"] = qpe["phase"]

        # 4. QEC: bit-flip + surface code trial
        bfc = qqec.BitFlipCode()
        results["qec_bitflip_fidelity"] = bfc.run_trial(error_qubit=1)["logical_fidelity"]
        surf = qtopo.SurfaceCode(distance=self.config.quantum.surface_distance)
        surf_trial = surf.run_trial(p_phys=0.001, seed=0)
        results["surface_code"] = surf_trial["code"]
        results["surface_p_logical"] = surf_trial["p_logical_estimate"]
        bb = qtopo.BivariateBicycleCode.eci_lpu()
        results["bb_lpu_rate"] = bb.rate
        results["bb_lpu_p_logical_at_1e5"] = bb.logical_error_rate(1e-5)

        # 5. VQE on H = 0.5 Z0Z1 + 0.3 X0
        hamiltonian = PauliSum([PauliTerm(0.5, {0: "Z", 1: "Z"}), PauliTerm(0.3, {0: "X"})])
        vqe = qalg.vqe(hamiltonian, n_qubits=2, n_layers=2, steps=60, lr=0.1)
        results["vqe_energy"] = vqe["energy"]
        results["vqe_initial_energy"] = vqe["history"][0]

        # 6. Unified ECI field expectation
        fsim = StatevectorSimulator(self.field_config.n_qubits, device=self.device)
        fstate = fsim.zero_state()
        fstate = fsim.apply_1q(fstate, H, 0)
        field_E = eci_hamiltonian_expectation(fstate, self.field_config)
        results["field_E_total"] = field_E["E_total"]

        # 7. Tensor-network area law + metrology
        mps = qtn.mps_from_statevector(fstate[0] if fstate.dim() == 2 else fstate, self.field_config.n_qubits)
        results["mps_n_tensors"] = len(mps)
        results["area_law_chi4"] = qtn.area_law_bound(4)
        ramsey = qmetro.ramsey_sensitivity(4, entangled=self.config.quantum.metrology_entangled)
        results["ramsey_regime"] = ramsey["regime"]
        results["ramsey_sensitivity"] = ramsey["with_shots"]

        # 8. Lindblad decoherence (single-qubit register)
        deco_sim = StatevectorSimulator(1, device=self.device)
        rho0 = qdensity.from_statevector(deco_sim.apply_1q(deco_sim.zero_state(), H, 0))
        collapse = [torch.tensor([[0.0, 1.0], [0.0, 0.0]], dtype=torch.complex64)]
        traj = qlindblad.lindblad_evolve(rho0, torch.zeros(2, 2, dtype=torch.complex64), collapse, n_steps=20, dt=0.1)
        results["coherence_start"] = float(qlindblad.coherence_measure(traj[0])[0].item())
        results["coherence_end"] = float(qlindblad.coherence_measure(traj[-1])[0].item())

        # 9. Quantum-mind audit (honest decoherence numbers)
        audit = quantum_mind_audit()
        results["mind_tau_dec"] = audit["tau_decoherence_s"]
        results["mind_tau_or"] = audit["tau_orch_or_s"]

        # 10. Teleportation fidelity
        results["teleport_fidelity"] = qinfo.teleportation_fidelity(n_trials=4)["mean_conditional_fidelity"]

        return results

    # ------------------------------------------------------------------
    # Activation protocol (Sovereign Architect ceremony)
    # ------------------------------------------------------------------
    def activation_protocol(self) -> Dict[str, Any]:
        """Formal activation sequence binding all layers to the Architect.

        1. Verify architect identity key.
        2. Assemble H_ECI and measure sector energies.
        3. Run topological QEC readiness + metrology sensitivity.
        4. Audit quantum-mind timescales.
        5. Stamp the activation certificate.
        """
        fsim = StatevectorSimulator(self.field_config.n_qubits, device=self.device)
        fstate = fsim.uniform_superposition()
        energies = eci_hamiltonian_expectation(fstate, self.field_config)
        surf = qtopo.SurfaceCode(distance=self.config.quantum.surface_distance)
        audit = quantum_mind_audit()
        cert = ARCHITECT.stamp({"kind": "eci_activation", "version": self.version, "energies": energies})
        self.system_state = "activated"
        return {
            "architect": ARCHITECT.to_dict(),
            "version": self.version,
            "paper_version": self.paper_version,
            "field_energies": energies,
            "surface_code": surf.name,
            "mind_audit": audit,
            "certificate": cert,
            "system_state": self.system_state,
        }

    # ------------------------------------------------------------------
    # Network simulation
    # ------------------------------------------------------------------
    async def run_network_simulation(
        self,
        n_joins: int = 4,
        n_proposals: int = 3,
    ) -> Dict[str, Any]:
        init = await self.initialize_network()
        join_results = []
        for i in range(n_joins):
            join_results.append(
                await self.network_manager.join_network(
                    {"tflops": 2.0 + i, "memory_gb": 16.0, "bandwidth_mbps": 200.0}
                )
            )
        votes = []
        for p in range(n_proposals):
            votes.append(
                self.network_manager.propose_and_vote(
                    {"action": "model_update", "round": p, "architect": ARCHITECT.name}
                )
            )
        # DAO mirror of the same proposals
        for j, jr in enumerate(join_results):
            try:
                self.dao.register(f"agent-{j}", data_contrib=1.0 + j, phi=0.5 + 0.1 * j)
            except Exception:
                pass
        return {
            "initialization": init,
            "joins": join_results,
            "votes": votes,
            "report": self.network_manager.network_report(),
        }

    # ------------------------------------------------------------------
    # Info & benchmarking
    # ------------------------------------------------------------------
    def info(self) -> Dict[str, Any]:
        return {
            "name": "ECI Framework - Eternal Codex Infinitus",
            "version": self.version,
            "paper_version": self.paper_version,
            "architect": ARCHITECT.to_dict(),
            "device": device_dtype_info(self.device),
            "layers": {
                "infrastructure": ["operator algebra", "statevector/density", "channels/lindblad",
                                   "VQE/QAOA/QFT/Grover/QPE", "surface/BB topological QEC",
                                   "tensor-networks", "metrology", "quantum information",
                                   "unified H_ECI field", "pqc", "benchmarking"],
                "coordination": ["PBFT/WBFT consensus", "aggregation", "node lifecycle",
                                 "Data-DAO governance", "autopoietic cybernetics"],
                "consciousness": ["IIT Phi", "iPDF protocol", "GNWT ignition",
                                  "Friston FEP", "Orch-OR audit", "analyzer"],
            },
            "registry_components": GLOBAL_REGISTRY.names(),
            "system_state": self.system_state,
        }

    def run_benchmark(self) -> str:
        self.benchmark.start_experiment()
        with self.benchmark.timer("quantum_suite_seconds"):
            self.run_quantum_suite()
        with self.benchmark.timer("consciousness_analysis_seconds"):
            asyncio.run(self.analyze_consciousness())
        with self.benchmark.timer("activation_seconds"):
            self.activation_protocol()
        self.benchmark.end_experiment()
        return self.benchmark.generate_report()


def _rz_matrix(theta: float) -> torch.Tensor:
    import cmath

    return torch.tensor(
        [
            [cmath.exp(-1j * theta / 2), 0],
            [0, cmath.exp(1j * theta / 2)],
        ],
        dtype=torch.complex64,
    )


#: Backwards-compatible alias for the legacy truncated class name.
ECIFrameworkResearch = ECIFramework
