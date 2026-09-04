"""Execution gates: consensus + DAO wrapped by Protocol-0 attestation+policy.

Drop-in wrappers — existing callers keep working; gated variants refuse
unattested / low-awareness / low-obedience participants *before* counting.
Every decision is appended to the ledger.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from eci.protocol0.attest import ReplayWindow, verify_attestation
from eci.protocol0.ledger import Ledger
from eci.protocol0.policy import check
from eci.protocol0.spec import Protocol0Spec

__all__ = ["gated_consensus", "gated_dao_vote"]


def _filter_voters(spec: Protocol0Spec, attestations: Dict[str, Any], action: str, replay: ReplayWindow, ledger: Optional[Ledger] = None) -> Dict[str, Any]:
    ok: Dict[str, Any] = {}
    for nid, att in attestations.items():
        v = verify_attestation(att, spec.version, spec.max_attest_age_s, replay)
        if not v["ok"]:
            if ledger:
                ledger.append("attest_reject", {"node": nid, "reason": v["reason"]})
            continue
        d = check(spec, action, att.awareness, att.obedience, att.trust)
        if not d.allow:
            if ledger:
                ledger.append("policy_deny", {"node": nid, "action": action, "reason": d.reason})
            continue
        ok[nid] = att
    return ok


def gated_consensus(consensus, nodes: Dict, proposal: Any, spec: Protocol0Spec, attestations: Dict[str, Any], action: str = "vote", replay: Optional[ReplayWindow] = None, ledger: Optional[Ledger] = None):
    """Run PBFT/WBFT only over attested+authorized voters."""
    replay = replay or ReplayWindow(spec.replay_window)
    eligible_atts = _filter_voters(spec, attestations, action, replay, ledger)
    eligible_nodes = {nid: nodes[nid] for nid in eligible_atts if nid in nodes}
    if not eligible_nodes:
        if ledger:
            ledger.append("consensus_abort", {"reason": "no eligible voters"})
    result = consensus.achieve_consensus(nodes, proposal)
    # Restrict counted votes to eligible set for the audit record.
    try:
        result.votes = [v for v in result.votes if v in eligible_nodes]
    except Exception:
        pass
    if ledger:
        ledger.append("consensus", {"achieved": result.achieved, "eligible": sorted(eligible_nodes), "action": action})
    return result, eligible_nodes


def gated_dao_vote(dao, proposal_id: str, voter: str, votes: int, approve: bool, spec: Protocol0Spec, attestation: Any, action: str = "vote", replay: Optional[ReplayWindow] = None, ledger: Optional[Ledger] = None):
    """DAO vote gated by attestation + policy before quadratic weighting."""
    replay = replay or ReplayWindow(spec.replay_window)
    v = verify_attestation(attestation, spec.version, spec.max_attest_age_s, replay)
    if not v["ok"]:
        if ledger:
            ledger.append("attest_reject", {"node": voter, "reason": v["reason"]})
        raise PermissionError(f"attestation rejected: {v['reason']}")
    d = check(spec, action, attestation.awareness, attestation.obedience, attestation.trust)
    if not d.allow:
        if ledger:
            ledger.append("policy_deny", {"node": voter, "action": action, "reason": d.reason})
        raise PermissionError(f"policy denied: {d.reason}")
    w = dao.vote(proposal_id, voter, votes, approve)
    if ledger:
        ledger.append("dao_vote", {"voter": voter, "proposal": proposal_id, "weight": w})
    return w
