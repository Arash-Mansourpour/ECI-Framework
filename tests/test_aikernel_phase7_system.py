"""Phase 7, Part 3 — system-wide ledger: all 7 adapters, one total.

Members: vqe + noisy (quantum), phi + fep (consciousness), gov
(governance), world + sci (cognition). Mixed cadence throughout; total
must equal the sum of shares at every checkpoint.
"""
import torch


def _build():
    from eci.aikernel.state_contract import KernelLedger
    from eci.cognition.aikernel_adapter import ScientistContributor, WorldModelContributor
    from eci.cognition.world_model import WorldModelConfig
    from eci.consciousness.aikernel_adapter import FEPContributor, PhiContributor
    from eci.governance.aikernel_adapter import AgentContributor
    from eci.quantum.aikernel_adapter import VQEContributor, tfi_hamiltonian
    from eci.quantum.mitigation import NoisyVQEContributor
    torch.manual_seed(0)
    H = tfi_hamiltonian(2)
    members = {
        "vqe": VQEContributor(H, 2, e_target=-3.2),
        "noisy": NoisyVQEContributor(H, 2, e_target=-3.2, mode="noisy", noise_q=0.02),
        "phi": PhiContributor(dim=2),
        "fep": FEPContributor(2, 2, perceive_steps=5),
        "gov": AgentContributor("gov-7", 1, obs_noise=0.5),
        "world": WorldModelContributor(WorldModelConfig(4, 2, 16, 4)),
        "sci": ScientistContributor("h7", "y=a*x+b", 2),
    }
    led = KernelLedger()
    for name, m in members.items():
        led.register(name, m)
    return led, members


def test_system_ledger_coheres_across_cadences():
    led, m = _build()
    assert set(led.shares()) == {"vqe", "noisy", "phi", "fep", "gov", "world", "sci"}
    tr = torch.cat([torch.randn(4), torch.zeros(2), torch.tensor([0.2]), torch.randn(4)])
    traj = []
    for step in range(4):
        m["vqe"].step()                                   # every step
        m["noisy"].step()                                 # every step
        if step % 2 == 0:
            m["phi"].update(torch.randn(8, 2))            # medium
            m["world"].update(tr)                         # medium
            m["fep"].update(torch.randn(2, dtype=torch.float64))  # medium
        if step % 3 == 0:
            m["gov"].update(torch.tensor([0.3]))          # slow (rounds)
            m["sci"].update(torch.tensor([0.5, -0.5, 0.0, 0.0]))
        total = float(led.total_free_energy().detach().item())
        s = sum(led.shares().values())
        assert abs(total - s) < 1e-4, (total, s)
        traj.append(round(total, 4))
    assert all(t == t and abs(t) < 1e6 for t in traj)
    print("system F trajectory:", traj)


def test_mcp_describe_reports_meanings():
    """aik.ledger.describe: numbers + audit category + what each share is."""
    from eci.aikernel.mcp_bridge import register_ledger
    from eci.mcp.registry import McpRegistry
    led, _ = _build()
    reg = McpRegistry()
    assert "aik.ledger.describe" in register_ledger(reg, led)
    out = reg.get("aik.ledger.describe").handler({}, {})
    members = out["members"]
    assert set(members) == {"vqe", "noisy", "phi", "fep", "gov", "world", "sci"}
    assert members["phi"]["category"] == "adaptable"
    assert all(m["category"] == "good-fit" for k, m in members.items() if k != "phi")
    assert all(m["note"] for m in members.values())
    assert all(abs(m["share"] - led.shares()[k]) < 1e-9 for k, m in members.items())
    # unknown member class reports unlisted, never a guess
    from eci.aikernel.generative_model import GenerativeState
    from eci.aikernel.mcp_bridge import register_ledger as _reg_ledger
    from eci.aikernel.state_contract import KernelLedger
    from eci.mcp.registry import McpRegistry as _Reg

    class Mystery:
        def posterior(self):
            return GenerativeState(torch.zeros(1), torch.eye(1))

        def update(self, observation):
            return self.posterior()

        def free_energy_contribution(self):
            return torch.tensor(1.0)

    led2, reg2 = KernelLedger(), _Reg()
    led2.register("mystery", Mystery())
    _reg_ledger(reg2, led2)
    assert reg2.get("aik.ledger.describe").handler({}, {})["members"]["mystery"] == {
        "share": 1.0, "category": "unlisted", "note": ""}
