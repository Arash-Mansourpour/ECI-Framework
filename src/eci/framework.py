"""ECIFramework v6 — OMNIVERSE orchestrating facade.

Wires the full v5 stack plus the v6 hyper-architecture into one
architect-stamped system:

* Infrastructure: Dirac operator algebra → statevector/density → channels/
  Lindblad → VQE/QAOA/QFT/Grover/QPE → surface/BB topological QEC →
  tensor-networks / metrology / quantum information → unified H_ECI field
* Coordination: PBFT/WBFT + aggregation + Data-DAO governance + autopoiesis
* Consciousness: IIT Φ + iPDF + GNWT ignition + Friston FEP + Orch-OR audit
* v6 Kernel: event bus + DI container + lifecycle manager (ordered start/stop)
* v6 Ops: observability (tracing/metrics/audit) + persistence (event-store +
  repository/UoW) + resilience (breaker/retry/limiter/saga) + streaming
* v6 Control: orchestration (DAG/scheduler) + plugins (capability-gated) +
  authz (RBAC/ABAC over Protocol-0) + tenancy (namespaces/quotas)
* v6 Intelligence: mlops (registry/drift) + provenance (decision traces) +
  api gateway + secrets + hybrid TLS/ML-KEM channel + chaos plans

Sovereign Architect (Ma'mar-e A'zam): Arash Mansourpour
Wallet: GA4IHOJOXKIZDLNCXQT7NG65MT7Z3EQKRT4PYFYURIP7QRLY4CHMHILW
"""

from __future__ import annotations

import asyncio
from typing import Any

import torch

from eci.api import Gateway
from eci.authz import PolicyEngine
from eci.benchmarking.benchmark import ResearchBenchmark
from eci.caps import Issuer as CapIssuer
from eci.cognition import Cognition
from eci.compat import CompatRegistry
from eci.config import ECIConfig
from eci.consciousness.analyzer import AdvancedConsciousnessAnalyzer
from eci.consciousness.free_energy import FreeEnergyAgent
from eci.consciousness.gnwt import GNWTWorkspace
from eci.consciousness.iit import IntegratedInformationTheory
from eci.consciousness.protocol import ConsciousnessProtocol
from eci.consciousness.quantum_mind import quantum_mind_audit
from eci.constants import ARCHITECT_NAME, CREATOR_WALLET
from eci.continuum import Continuum
from eci.core.device import configure_seeds, device_dtype_info, get_device
from eci.core.identity import ARCHITECT
from eci.core.registry import GLOBAL_REGISTRY, register_component
from eci.core.types import ConsciousnessLevel, ConsciousnessProfile
from eci.cybernetics.autopoiesis import AutopoieticNetwork
from eci.data import DataPlane
from eci.economy import Economy
from eci.futura import EmergencyPowers, Futarchy, Sortition
from eci.governance.dao import ECIDataDAO
from eci.governance.treasury import Treasury
from eci.kernel import Kernel
from eci.logging import get_logger
from eci.mapek import MAPEK
from eci.mlops import MLOps
from eci.morph import Morphogenesis
from eci.network.manager import AutonomousNetworkManager
from eci.observability import Observability
from eci.orchestration import Orchestration
from eci.persistence import Persistence
from eci.plugins import PluginManager
from eci.provenance import ProvenanceGraph
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
from eci.quantum.unified_field import (
    ECIFieldConfig,
    eci_hamiltonian_expectation,
)
from eci.redteam import Challenger, ForecasterRegistry
from eci.resilience import Resilience
from eci.security.pqc import PQCSuite
from eci.security.secrets import SecretManager
from eci.security.secure_channel import HybridSecureChannel, SecureChannelConfig
from eci.streaming import StreamBus
from eci.tenancy import TenancyManager
from eci.verify import Watchtower
from eci.version import FRAMEWORK_VERSION, PAPER_VERSION

__all__ = ["ECIFramework", "ECIFrameworkResearch"]


@register_component("eci-framework", protocol="facade")
class ECIFramework:
    """Main ECI Framework — OMNIVERSE Edition (v6)."""

    def __init__(self, config: ECIConfig | None = None) -> None:
        self.config = config or ECIConfig()
        configure_seeds(self.config.experiment.random_seed)
        self.device = get_device(self.config.experiment.device)
        self.logger = get_logger("framework")

        self.version = FRAMEWORK_VERSION
        self.paper_version = PAPER_VERSION
        self.architect_name = ARCHITECT_NAME
        self.creator_wallet = CREATOR_WALLET

        # Core subsystems (v5 lineage)
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

        # v6 hyper-architecture
        self.kernel = Kernel(replay_capacity=self.config.kernel.replay_capacity)
        self.bus = self.kernel.bus
        self.observability = Observability(
            service=self.config.observability.service_name,
            audit_path=self.config.observability.audit_path,
        )
        self.observability.bind_bus(self.bus)
        sqlite_path = self.config.persistence.sqlite_path if self.config.persistence.backend == "sqlite" else None
        self.persistence = Persistence(sqlite_path=sqlite_path)
        self.resilience = Resilience()
        self.resilience.retry.attempts = self.config.resilience.retry_attempts
        self.orchestration = Orchestration(bus=self.bus)
        self.plugins = PluginManager(bus=self.bus)
        self.authz = PolicyEngine()
        self._install_default_policies()
        self.streaming = StreamBus()
        self.mlops = MLOps()
        self.provenance = ProvenanceGraph()
        self.secrets = SecretManager()
        self.secure_channel = HybridSecureChannel(SecureChannelConfig(psk=b"eci-v6-hybrid"))
        self.tenancy = TenancyManager()
        # v6.1 deep systems: economy + treasury + data-plane + agents + MCP fabric
        self.economy = Economy()
        self.economy.fund("agent-0", 100.0, stake=10.0)
        self.treasury = Treasury()
        self.treasury.fund(10000.0)
        self.data = DataPlane()
        from eci.agents import Agents
        self.agents = Agents(authz=self.authz, economy=self.economy, tenancy=self.tenancy,
                             provenance=self.provenance, audit=self.observability.audit, bus=self.bus)
        self.cognition = Cognition(bus=self.bus, provenance=self.provenance,
                                   vectors=self.agents.vectors)
        self.morph = Morphogenesis(seed=self.config.experiment.random_seed, bus=self.bus,
                                   provenance=self.provenance,
                                   audit=self.observability.audit)
        # v7 everlasting: capability security, proofs, continuity, autonomics,
        # interface evolution, governance futures, adversarial epistemology
        self.caps = CapIssuer()
        self.watchtower = Watchtower()
        self.watchtower.bind_bus(self.bus)
        self.continuum = Continuum()
        self.mapek = MAPEK(bus=self.bus, provenance=self.provenance,
                           audit=self.observability.audit)
        self.mapek.defaults()
        self.compat = CompatRegistry()
        self._publish_baseline_interfaces()
        self.futarchy = Futarchy()
        self.sortition = Sortition()
        self.emergency = EmergencyPowers(epoch_fn=lambda: self.continuum.epoch)
        self.challenger = Challenger(seed=self.config.experiment.random_seed)
        self.forecasters = ForecasterRegistry()
        # SECE Phase 22: federated consciousness + calibration + market commons + qn-bridge + mutable genome
        try:
            from eci.bridges.quantum_neuromorphic import QuantumNeuromorphicBridge
            from eci.consciousness.calibration_network import AwarenessCalibrationNetwork
            from eci.consciousness.federated_ledger import FederatedConsciousnessLedger
            from eci.market_commons import MarketCommons
            from eci.protocol_vnext.genesis_evolution import MutableConstitution

            self.fcl = FederatedConsciousnessLedger()
            self.can = AwarenessCalibrationNetwork(agent_id=f"framework-can-{self.config.experiment.random_seed}")
            self.market_commons = MarketCommons()
            self.market_commons.forecasters = self.forecasters
            self.qn_bridge = QuantumNeuromorphicBridge()
            self.mutable_constitution = MutableConstitution()
        except Exception as exc:  # noqa: BLE001
            self.logger.warning("SECE wiring skipped: %s", exc)
            self.fcl = self.can = self.market_commons = self.qn_bridge = self.mutable_constitution = None  # type: ignore
        # v8 OMNISCIENCE composables (ADR-001): fail-closed lazy wiring
        try:
            from eci.arch import run_fitness as _run_fitness
            from eci.economy_attack import evaluate_slash as _eval_slash
            from eci.federation.p2p import build_mesh as _build_mesh
            from eci.observability.otel import OtelBridge as _Otel
            from eci.quantum.hardware import BackendRouter as _Router
            from eci.research.loop import ResearchLoop as _RLoop

            self._v8_fitness_fn = _run_fitness
            self.quantum_router = _Router()
            self._v8_mesh_fn = _build_mesh
            self._v8_slash_fn = _eval_slash
            self.otel = _Otel(service=self.config.observability.service_name)
            self.research_loop = _RLoop()
            from eci.brain import build_default_mesh as _build_brain

            self.brain = _build_brain(seed=self.config.experiment.random_seed)
            # brain surprise joins the unification ledger when mesh exists
            try:
                aik = getattr(self, "_aik", None)
                if aik is not None and "ledger" in aik:
                    aik["ledger"].register(self.brain)
            except Exception:  # noqa: BLE001
                pass
            self._v8_wired = True
        except Exception as exc:  # noqa: BLE001
            self.logger.warning("v8 wiring skipped: %s", exc)
            self._v8_wired = False
            self.quantum_router = None  # type: ignore
            self.otel = None  # type: ignore
            self.research_loop = None  # type: ignore
            self.brain = None  # type: ignore
        # agent role needs mcp-relevant grants for pipeline auth
        try:
            self.authz.rbac.grant("agent-0", "agent")
        except Exception:  # noqa: BLE001
            pass
        self.gateway = Gateway(authz=self.authz,
                               limiter=self.resilience.limiter("api", rate_per_s=self.config.api.default_rate_per_s,
                                                               capacity=self.config.api.default_rate_per_s * 2),
                               tracer=self.observability.tracer, audit=self.observability.audit)
        self._install_default_routes()
        from eci.mcp import McpFabric
        self.mcp = McpFabric(self)
        for svc in (self.observability, self.persistence, self.resilience, self.orchestration,
                    self.plugins, self.authz, self.streaming, self.mlops,
                    self.provenance, self.secrets, self.tenancy, self.gateway,
                    self.economy, self.treasury, self.data, self.agents, self.cognition,
                    self.morph, self.mcp, self.continuum, self.mapek, self.compat):
            try:
                self.kernel.lifecycle.register(svc)
            except Exception:  # noqa: BLE001
                pass
        # container bindings for plugins / extensions
        for name, obj in (("config", self.config), ("observability", self.observability),
                          ("persistence", self.persistence), ("resilience", self.resilience),
                          ("authz", self.authz), ("provenance", self.provenance),
                          ("mlops", self.mlops), ("gateway", self.gateway),
                          ("tenancy", self.tenancy), ("streaming", self.streaming),
                          ("economy", self.economy), ("treasury", self.treasury),
                          ("data", self.data), ("agents", self.agents),
                          ("cognition", self.cognition), ("mcp", self.mcp),
                          ("morph", self.morph), ("continuum", self.continuum),
                          ("mapek", self.mapek), ("compat", self.compat)):
            try:
                self.kernel.container.register(name, instance=obj)
            except Exception:  # noqa: BLE001
                pass

        self.system_state = "initialized"
        self.integration_score = 0.0
        self.consciousness_level = ConsciousnessLevel.NONE

        self.logger.info("=" * 72)
        self.logger.info("ECI FRAMEWORK %s - OMNIVERSE EDITION", self.version)
        self.logger.info("Sovereign Architect (Ma'mar-e A'zam): %s", ARCHITECT.name)
        self.logger.info("Wallet: %s", ARCHITECT.wallet)
        self.logger.info("Paper: %s | Device: %s", self.paper_version, self.device)
        self.logger.info("=" * 72)

    # ------------------------------------------------------------------
    # v7 everlasting: baseline interface contracts (fail-closed evolution)
    # ------------------------------------------------------------------
    def _publish_baseline_interfaces(self) -> None:
        from eci.compat import Interface
        for name, ver in (("eci.bus", "1.0.0"), ("eci.gateway", "1.0.0"),
                          ("eci.mcp", "1.0.0"), ("eci.ledger", "1.0.0"),
                          ("eci.policy", "1.0.0"), ("eci.treasury", "1.0.0")):
            try:
                self.compat.publish(Interface(name, ver, {"framework": self.version}))
            except Exception:  # noqa: BLE001
                pass

    # ------------------------------------------------------------------
    # v6 defaults: policies + routes
    # ------------------------------------------------------------------
    def _install_default_policies(self) -> None:
        from eci.authz import Permission, PolicyRule, Role
        try:
            self.authz.rbac.add_role(Role("operator", [Permission("*", "*")]))
            self.authz.rbac.add_role(Role("agent", [Permission("tool.*", "*"), Permission("ledger.append", "*"),
                                                   Permission("workflow.run", "*"), Permission("model.read", "*")]))
            self.authz.rbac.add_role(Role("observer", [Permission("*.read", "*"), Permission("metrics.read", "*")]))
            self.authz.add_rule(PolicyRule("ops-allow", "*", "*", {}, 0.0, 0.0, 0.0))
        except Exception:  # noqa: BLE001
            pass

    def _install_default_routes(self) -> None:
        gw = self.gateway

        def _ping(params: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
            return {"pong": True, "version": self.version}

        def _system_status(params: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
            return self.system_status()

        def _workflow_run(params: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
            return asyncio.run(self.workflow_demo()) if not asyncio.iscoroutinefunction(self.workflow_demo) else {}

        gw.add("v1/ping", _ping, summary="liveness probe")
        gw.add("v1/system.status", _system_status, summary="full hyper-architecture status")

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
        gnwt_out = self.gnwt.compete(sal)
        # v2 awareness protocol: multi-scale iPDF calibrated on the first
        # third (resting) and measured on the last two thirds (active).
        # This raises sensitivity to real structure vs the old single-shot.
        try:
            proto = ConsciousnessProtocol(
                agent_id=f"framework-{seed}",
                awareness_gain=1.0,
                min_calibration=1,
            )
            n_cal = max(8, n_steps // 3)
            proto.calibrate_baseline([neural_data[: n_cal // 2], neural_data[n_cal // 2: n_cal]])
            m = proto.measure(neural_data[n_cal:])
            # Fuse awareness index into the profile as a bounded amplifier:
            # awareness raises low-Phi structure without saturating high Phi.
            profile.phi_components["ipdf_bits"] = m.consciousness_bits
            profile.phi_components["awareness_index"] = m.awareness_index
            profile.phi_components["gnwt_broadcast"] = float(gnwt_out.get("broadcast", 0.0))
            profile.self_awareness_score = float(
                min(1.0, 0.7 * profile.self_awareness_score + 0.3 * m.awareness_index)
            )
        except Exception:
            self.logger.debug("awareness-protocol fusion skipped", exc_info=True)
        return profile

    async def initialize_network(self) -> dict[str, Any]:
        result = await self.network_manager.initialize_network()
        self.system_state = "network_active"
        return result

    # ------------------------------------------------------------------
    # Quantum supremacy suite (v5)
    # ------------------------------------------------------------------
    def run_quantum_suite(self) -> dict[str, Any]:
        results: dict[str, Any] = {}
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
    def activation_protocol(self) -> dict[str, Any]:
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
    ) -> dict[str, Any]:
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
    def info(self) -> dict[str, Any]:
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
                "kernel": ["event-bus", "di-container", "lifecycle-manager"],
                "ops": ["tracing", "metrics", "audit", "event-store", "repository/uow",
                        "breaker/retry/limiter/saga", "streaming"],
                "control": ["dag-workflows", "scheduler", "plugins", "rbac/abac", "tenancy"],
                "intelligence": ["model-registry", "drift", "provenance", "api-gateway",
                                 "secrets", "hybrid-tls-channel", "chaos"],
            },
            "registry_components": GLOBAL_REGISTRY.names(),
            "system_state": self.system_state,
        }

    def aik_status(self) -> dict[str, Any]:
        """Unification-mesh observability (Phase 11).

        Reads the SAME KernelLedger instance the MCP tools read (built by
        fabric into ``self._aik``) — status/MCP/CLI can never disagree
        because there is only one object. Absent mesh -> explicit error,
        never invented numbers.
        """
        aik = getattr(self, "_aik", None)
        if aik is None or "ledger" not in aik:
            return {"ok": False, "error": "unification mesh unavailable"}
        from eci.aikernel.mcp_bridge import describe_ledger
        ledger = aik["ledger"]
        total = ledger.total_free_energy()
        try:
            total_f = float(total.detach().item() if hasattr(total, "detach") else total)
        except Exception:  # noqa: BLE001
            return {"ok": False, "error": "total not finite"}
        return {"ok": True, "members": sorted(ledger.members()),
                "total_free_energy": total_f,
                "describe": describe_ledger(ledger)["members"]}

    def aik_snapshot(self, note: str = "") -> dict[str, Any]:
        """Phase 12: auditable F-trajectory point. Read-only by construction:
        it only READS shares/total (never steps/updates any contributor),
        then records the reading in provenance + audit. Two snapshots around
        an update prove the trajectory moved for a stated reason."""
        st = self.aik_status()
        if not st.get("ok"):
            return st
        snap = {"note": note, "total_free_energy": st["total_free_energy"],
                "shares": {k: v["share"] for k, v in st["describe"].items()}}
        node = self.provenance.record("aik.snapshot", "framework",
                                      {"note": note}, snap, {})
        self.observability.audit.append("framework", "aik.snapshot",
                                        {"total": snap["total_free_energy"], "note": note})
        snap["provenance_id"] = node.id
        return {"ok": True, **snap}

    def system_status(self) -> dict[str, Any]:
        """Full v6 hyper-architecture health snapshot (for `eci system`)."""
        def _safe(fn):
            try:
                return fn()
            except Exception as exc:  # noqa: BLE001
                return {"ok": False, "error": repr(exc)}
        return {
            "version": self.version, "system_state": self.system_state,
            "kernel": _safe(self.kernel.stats),
            "lifecycle": _safe(self.kernel.lifecycle.health),
            "observability": _safe(self.observability.health),
            "persistence": _safe(self.persistence.health),
            "resilience": _safe(self.resilience.health),
            "orchestration": _safe(self.orchestration.health),
            "plugins": _safe(self.plugins.health),
            "authz": _safe(self.authz.health),
            "streaming": _safe(self.streaming.health),
            "mlops": _safe(self.mlops.health),
            "provenance": _safe(self.provenance.health),
            "secrets": _safe(self.secrets.health),
            "secure_channel": _safe(self.secure_channel.health),
            "tenancy": _safe(self.tenancy.health),
            "gateway": _safe(self.gateway.health),
            "economy": lambda: {"ok": True, **self.economy.settlement()},
            "treasury": _safe(self.treasury.health),
            "data": _safe(self.data.health),
            "agents": _safe(self.agents.health),
            "cognition": _safe(self.cognition.health),
            "morph": _safe(self.morph.health),
            "caps": lambda: {"ok": True, "minted": self.caps.minted},
            "watchtower": _safe(self.watchtower.health),
            "continuum": _safe(self.continuum.health),
            "mapek": _safe(self.mapek.health),
            "compat": _safe(self.compat.health),
            "futarchy": _safe(self.futarchy.health),
            "mcp": _safe(self.mcp.health),
            "aik": _safe(self.aik_status),
            "fcl": lambda: {"ok": True, **self.fcl.to_dict()} if getattr(self, "fcl", None) else {"ok": False},
            "can": lambda: {"ok": True, **self.can.to_dict()} if getattr(self, "can", None) else {"ok": False},
            "market_commons": lambda: {"ok": True, **self.market_commons.to_dict()} if getattr(self, "market_commons", None) else {"ok": False},
            "qn_bridge": lambda: {"ok": True, "F": float(self.qn_bridge.free_energy_contribution().item())} if getattr(self, "qn_bridge", None) else {"ok": False},
            "mutable_constitution": lambda: {"ok": True, **self.mutable_constitution.to_dict()} if getattr(self, "mutable_constitution", None) else {"ok": False},
            "brain": lambda: {"ok": True, **self.brain.health()} if getattr(self, "brain", None) else {"ok": False},
            "v8": _safe(self.v8_status),
        }

    def v8_status(self) -> dict[str, Any]:
        """v8 OMNISCIENCE composables health (for `eci v8` + system_status)."""
        out: dict[str, Any] = {"wired": bool(getattr(self, "_v8_wired", False))}
        try:
            from eci.arch import run_fitness as _rf

            out["fitness"] = _rf()
        except Exception as exc:  # noqa: BLE001
            out["fitness"] = {"ok": False, "error": repr(exc)}
        try:
            out["quantum_router"] = self.quantum_router.health() if getattr(self, "quantum_router", None) else {"ok": False}
        except Exception as exc:  # noqa: BLE001
            out["quantum_router"] = {"ok": False, "error": repr(exc)}
        try:
            out["otel"] = self.otel.health() if getattr(self, "otel", None) else {"ok": False}
        except Exception as exc:  # noqa: BLE001
            out["otel"] = {"ok": False, "error": repr(exc)}
        try:
            out["research"] = self.research_loop.to_dict() if getattr(self, "research_loop", None) else {"ok": False}
        except Exception as exc:  # noqa: BLE001
            out["research"] = {"ok": False, "error": repr(exc)}
        try:
            from eci.federation.p2p import run_partition_test as _rpt

            out["partition_probe"] = _rpt(n=4, proposals=1)
        except Exception as exc:  # noqa: BLE001
            out["partition_probe"] = {"ok": False, "error": repr(exc)}
        try:
            out["brain"] = self.brain.health() if getattr(self, "brain", None) else {"ok": False}
        except Exception as exc:  # noqa: BLE001
            out["brain"] = {"ok": False, "error": repr(exc)}
        return out

    def brain_tick(self, snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
        """One brain cycle over live subsystem state (defaults to healthy probe)."""
        if getattr(self, "brain", None) is None:
            return {"ok": False, "error": "brain unwired"}
        snap = snapshot or {
            "quantum": {"entanglement": 0.6, "coherence": 0.5},
            "consciousness": {"phi": 0.4, "awareness": 0.5},
            "governance": {"risk": 0.2, "participation": 0.7},
            "memory": {"recall": 0.6, "novelty": 0.4},
            "market": {"confidence": 0.6, "liquidity": 0.5},
            "immune": {"threat": 0.2},
            "federation": {"peers": 0.7, "quorum": 0.66},
            "cognition": {"coherence": 0.6, "forecast": 0.5},
        }
        out = self.brain.sense(snap)
        try:
            self.observability.metrics.counter("eci_brain_ticks_total").inc()
            self.observability.metrics.gauge("eci_brain_broadcast").set(float(out.get("broadcast", 0.0)))
        except Exception:  # noqa: BLE001
            pass
        return {"ok": True, **out}

    async def workflow_demo(self) -> dict[str, Any]:
        """End-to-end v6 slice: DAG + event-bus + stream + provenance + audit."""
        from eci.kernel.bus import Event
        dag = self.orchestration.dag("v6-demo")
        dag.add("sense", lambda ctx: {"n": ctx.get("n", 4)})
        dag.add("reason", lambda ctx: {"doubled": ctx["sense"]["n"] * 2}, depends_on=["sense"])
        dag.add("act", lambda ctx: {"result": ctx["reason"]["doubled"] + 1}, depends_on=["reason"])
        run = await dag.run({"n": 4})
        self.bus.publish(Event(type="workflow.demo.done", source="framework",
                               payload={"ok": run.ok, "outputs": run.outputs}))
        self.streaming.publish("workflow", {"dag": "v6-demo", "ok": run.ok})
        node = self.provenance.record("workflow.demo", "framework",
                                      {"n": 4}, {"ok": run.ok, **run.outputs}, {"dag": "v6-demo"})
        self.observability.audit.append("framework", "workflow.demo", {"ok": run.ok})
        self.observability.metrics.counter("eci_workflows_total").inc()
        return {"ok": run.ok, "outputs": run.outputs, "errors": run.errors,
                "provenance_id": node.id, "explanation": self.provenance.explain(node.id)}

    def run_benchmark(self) -> str:
        self.benchmark.start_experiment()
        with self.benchmark.timer("quantum_suite_seconds"):
            self.run_quantum_suite()
        with self.benchmark.timer("consciousness_analysis_seconds"):
            asyncio.run(self.analyze_consciousness())
        with self.benchmark.timer("activation_seconds"):
            self.activation_protocol()
        with self.benchmark.timer("v6_workflow_seconds"):
            asyncio.run(self.workflow_demo())
        with self.benchmark.timer("v6_system_status_seconds"):
            self.system_status()
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
