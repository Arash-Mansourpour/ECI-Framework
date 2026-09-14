"""Protocol vNext — ECI Evolving Collective Intelligence: nervous system demo."""

from eci.protocol_vnext.capability import CapabilityManifest, CapabilityVector
from eci.protocol_vnext.cognitive import CognitiveRuntime
from eci.protocol_vnext.collective import CollectiveLearningLoop, OutcomeReceipt
from eci.protocol_vnext.epistemic import EvidenceKeeper, TruthGuardian
from eci.protocol_vnext.evolution import GovernedEvolution
from eci.protocol_vnext.genesis import ArchitectBeacon, ConstitutionalGenome
from eci.protocol_vnext.identity import ECIIdentity, NodeLifecycle
from eci.protocol_vnext.memory import DreamEngine, LivingMemory
from eci.protocol_vnext.messaging import ECIMessage, MessageFabric
from eci.protocol_vnext.ontology import FederatedOntology
from eci.protocol_vnext.reasoning import ReasoningLandscape


def test_genesis_and_lifecycle():
    beacon = ArchitectBeacon()
    genome = ConstitutionalGenome()
    from eci.protocol_vnext.genesis import GENESIS_ROOT as GR
    assert beacon.verify_genesis(beacon.presence()["genesis_root"] + "0" * 48) is False  # wrong (prefix only)
    assert beacon.verify_genesis(GR) is True
    # correct lifecycle: verify then advance
    node = ECIIdentity.create()
    lc = NodeLifecycle(node)
    assert lc.current() == "DISCOVER"
    lc.genesis_ok = True
    lc.genome_ok = True
    lc.advance(check=False)
    assert lc.current() == "VERIFY_GENESIS"


def test_capability_observed_verified():
    m = CapabilityManifest(node_id="n1", capabilities=CapabilityVector(python=0.9))
    assert m.observed.python == 0.5
    m.observe("python", 0.95)
    assert m.observed.python > 0.5
    assert m.verified.python > 0.5


def test_messaging_fabric():
    fabric = MessageFabric()
    fabric.subscribe("nodeA", ["TASK"])
    msg = ECIMessage(type="TASK", sender="nodeB", recipient="nodeA", payload={"q": "hi"})
    msg.sign()
    fabric.publish(msg)
    assert len(fabric.poll("nodeA")) == 1
    assert fabric.stats()["history"] == 1


def test_cognitive_gating_and_degradation():
    cog = CognitiveRuntime()
    out = cog.cycle({"perception": "test"}, task="test", complexity=0.2)
    assert "Reasoning" in out["faculties"]
    assert out["verified"] is True
    # high complexity activates all
    out2 = cog.cycle({"perception": "hard"}, task="hard", complexity=0.9)
    assert len(out2["faculties"]) > len(out["faculties"])


def test_memory_salience_and_dream():
    mem = LivingMemory()
    mem.store("exp1", kind="episodic", salience=0.9)
    mem.store("exp2", kind="episodic", salience=0.1)
    top = mem.recall(kind="episodic", top_k=1)
    assert top[0].content == "exp1" or top[0].salience >= 0.5
    dream = DreamEngine()
    mem.store("exp1_dup", kind="episodic", salience=0.8)
    result = dream.consolidate(mem)
    assert "skills" in result


def test_ontology_propose_only():
    onto = FederatedOntology()
    prop = onto.propose("ConceptX", "test concept", proposer="node1")
    assert prop.status == "pending"
    onto.verify(prop.id, "node2", "verify")
    onto.verify(prop.id, "node3", "verify")
    assert prop.status == "accepted"
    assert "ConceptX" in onto.accepted
    st = onto.snapshot()
    assert st.hash is not None


def test_truth_guardian_separation():
    ek = EvidenceKeeper()
    claim = ek.assert_claim("CIG > 1", source="node1", evidence=["benchmark"])
    assert claim.level.value == "provisional"
    ek.add_evidence(claim.id, "replicated", supporting=True)
    ek.add_evidence(claim.id, "replicated2", supporting=True)
    ek.add_evidence(claim.id, "replicated3", supporting=True)
    ek.add_evidence(claim.id, "replicated4", supporting=True)
    guardian = TruthGuardian()
    verdict = guardian.evaluate(claim, threshold=0.6)
    assert verdict["emit"] is True
    # disputed claim is not emitted
    claim.level = claim.level.__class__.DISPUTED
    assert guardian.evaluate(claim)["emit"] is False


def test_collective_learning_and_pareto():
    loop = CollectiveLearningLoop()
    receipt = OutcomeReceipt(task="t1", agents=["A", "B"], predicted_success=0.6, actual_quality=0.9, agreement=0.8)
    loop.ingest(receipt)
    assert loop.team_intel.cig(["A", "B"]) > 0
    land = ReasoningLandscape(problem="test", dimensions=["cost", "quality"])
    land.propose({"cost": 0.2, "quality": 0.8})
    land.propose({"cost": 0.1, "quality": 0.6})
    assert len(land.pareto()) >= 1


def test_governed_evolution():
    evo = GovernedEvolution()
    cand = evo.reflect({"task": "routing", "error": "latency"})
    assert cand.status == "proposed"
    assert evo.twin_test(cand.id, simulated_improvement=0.2) is True
    assert evo.canary(cand.id, success=True) is True
    assert evo.govern(cand.id, approved=True) is True
    assert cand.status == "deployed"
    evo.rollback(cand.id)
    assert cand.status == "rolled_back"
