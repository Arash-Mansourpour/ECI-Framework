"""Protocol-0 awareness gate demo: attest -> policy -> gated consensus + DAO.

Run:  PYTHONPATH=src python examples/protocol0_awareness_gate.py
"""
import torch

from eci.consciousness.adherence import AdherenceTracker
from eci.consciousness.collective import collective_awareness
from eci.consciousness.protocol import ConsciousnessProtocol
from eci.core.types import NetworkNode, NetworkRole
from eci.governance.dao import ECIDataDAO
from eci.network.consensus import PBFTConsensus
from eci.protocol0.attest import ReplayWindow, issue_attestation
from eci.protocol0.gates import gated_consensus, gated_dao_vote
from eci.protocol0.ledger import Ledger
from eci.protocol0.spec import load_spec

spec = load_spec()
ledger = Ledger()
replay = ReplayWindow(spec.replay_window)

torch.manual_seed(0)
rest = [0.05 * torch.randn(64, 8) for _ in range(2)]
t = torch.linspace(0, 25, 128).unsqueeze(1)
active = torch.sin(t) * 0.8 + 0.2 * torch.randn(128, 8)

agents = {}
for i, name in enumerate(["alice", "bob", "carol", "dave"]):
    proto = ConsciousnessProtocol(agent_id=name, min_calibration=1)
    proto.calibrate_baseline(rest)
    m = proto.measure(active + 0.05 * torch.randn(128, 8))
    tr = AdherenceTracker()
    for inst, tgt, _ in [("hold_output_near_half", 0.5, 0.2)] * 5:
        tr.probe(inst, 0.5 + 0.05 * torch.randn(()).item())
    agents[name] = (m.awareness_index, tr.obedience_score())

print("awareness/obedience:", {k: (round(a, 3), round(o, 3)) for k, (a, o) in agents.items()})
coll = collective_awareness({k: a for k, (a, _) in agents.items()}, spec.max_divergence, spec.min_coherence)
print(f"collective: mean={coll.mean:.3f} coherence={coll.coherence:.3f} divergence={coll.divergence:.3f} gate={coll.gate}")

nodes = {n: NetworkNode(node_id=n, role=NetworkRole.VALIDATOR, trust_score=0.9, reputation_score=1.0, stake=1.0) for n in agents}
atts = {n: issue_attestation(n, spec.version, a, o, 0.9) for n, (a, o) in agents.items()}
cons = PBFTConsensus(n_nodes=4, byzantine_rate=0.0)
res, eligible = gated_consensus(cons, nodes, {"task": "open_channel"}, spec, atts, action="vote", replay=replay, ledger=ledger)
print("consensus:", res.achieved, "eligible:", sorted(eligible))

dao = ECIDataDAO("demo")
for n, (a, _) in agents.items():
    dao.register(n, 4.0, phi=1.0 + a)
pid = dao.propose("channel_params", {"rate": 1}, "alice")
from eci.protocol0.attest import ReplayWindow as _RW
replay2 = _RW(spec.replay_window)
for n in ["alice", "bob"]:
    w = gated_dao_vote(dao, pid, n, 1, True, spec, atts[n], replay=replay2, ledger=ledger)
    print(n, "vote weight:", round(w, 3))
print("tally:", dao.tally(pid))
print("ledger verify:", ledger.verify())
