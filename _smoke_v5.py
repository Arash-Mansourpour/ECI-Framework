"""v5 supremacy smoke: every new module + activation + CLI paths."""
import asyncio
import torch

import eci
print("eci", eci.__version__, eci.FRAMEWORK_VERSION, eci.PAPER_VERSION)

# operator algebra
from eci.quantum import operator as qop
from eci.quantum import gates as qg
ub = qop.uncertainty_bound(qg.X.to(torch.complex64), qg.Z.to(torch.complex64),
                           torch.tensor([1/2**0.5, 1j/2**0.5], dtype=torch.complex64))
print("uncertainty saturated:", round(ub["lhs"],3), round(ub["rhs_bound"],3))
H2 = torch.kron(qg.Z, qg.Z).to(torch.complex64)
U = qop.matrix_exponential_hermitian(H2, 0.5)
print("unitary check:", qop.is_unitary(U), "hermitian H:", qop.is_hermitian(H2))

# information
from eci.quantum import information as qi, density as qd
bell = torch.zeros(1,4,dtype=torch.complex64); bell[0,0]=bell[0,3]=1/2**0.5
print("CHSH (expect ~2.828):", round(qi.chsh_value(qd.from_statevector(bell)),4))
print("teleport F (expect 1):", round(qi.teleportation_fidelity(4)["mean_conditional_fidelity"],4))
print("superdense:", qi.superdense_coding_capacity())

# topological
from eci.quantum.topological import SurfaceCode, BivariateBicycleCode, code_parameters_table
s = SurfaceCode(3).run_trial(p_phys=0.001, seed=0)
print("surface:", s["code"], "pL=", f"{s['p_logical_estimate']:.2e}")
bb = BivariateBicycleCode.eci_lpu()
print("BB-LPU rate:", bb.rate, "pL@1e-5=", f"{bb.logical_error_rate(1e-5):.2e}", "saving x", round(bb.overhead_vs_surface,1))
print("code table rows:", len(code_parameters_table()))

# tensor network + metrology
from eci.quantum import tensor_network as qtn, metrology as qm
from eci.quantum.statevector import StatevectorSimulator
sim = StatevectorSimulator(4); st = sim.uniform_superposition()
mps = qtn.mps_from_statevector(st[0], 4)
rt = qtn.mps_to_statevector(mps)
print("mps tensors:", len(mps), "roundtrip fid:", round(float(sim.fidelity(st, rt)[0]),4))
print("ramsey:", qm.ramsey_sensitivity(4, True)["regime"], "GHZ QFI:", qm.ghz_phase_qfi(4)["qfi"])

# unified field
from eci.quantum.unified_field import ECIFieldConfig, eci_unified_hamiltonian, eci_hamiltonian_expectation
cfg = ECIFieldConfig(n_qubits=4)
H = eci_unified_hamiltonian(cfg)
print("H_ECI terms:", H.n_terms, "E:", eci_hamiltonian_expectation(st, cfg)["E_total"])

# consciousness trinity
from eci.consciousness.gnwt import GNWTWorkspace
from eci.consciousness.free_energy import FreeEnergyAgent
from eci.consciousness.quantum_mind import quantum_mind_audit
w = GNWTWorkspace(n_processors=4)
print("gnwt:", w.compete(torch.tensor([0.1,0.2,0.9,0.3])))
a = FreeEnergyAgent(n_hidden=2, n_obs=2)
print("fep:", a.perceive(torch.tensor([0.5,-0.3]))["F"])
print("mind audit keys:", sorted(quantum_mind_audit().keys()))

# governance + cybernetics
from eci.governance.dao import ECIDataDAO
from eci.cybernetics.autopoiesis import AutopoieticNetwork
dao = ECIDataDAO("test"); dao.register("a",1.0,1.0); dao.register("b",2.0,0.2)
pid = dao.propose("upgrade", {"x":1}, "a")
dao.vote(pid,"a",1,True); dao.vote(pid,"b",1,False)
print("dao tally:", dao.tally(pid))
auto = AutopoieticNetwork()
print("autopoiesis:", auto.step(), auto.step())

# facade
from eci.framework import ECIFramework
fw = ECIFramework()
r = fw.run_quantum_suite()
print("suite keys:", len(r), "teleport:", round(r["teleport_fidelity"],4))
print("activation:", fw.activation_protocol()["system_state"])
prof = asyncio.run(fw.analyze_consciousness(n_steps=128, n_neurons=16, seed=1))
print("phi:", round(prof.phi_value,3), prof.consciousness_level.name)
print("ALL V5 SMOKE CHECKS DONE")
