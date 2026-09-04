"""Protocol-0: machine-readable obedience layer for autonomous AI.

SPEC (protocol0/spec.yaml) → ATTEST (signed capability claim) →
POLICY (execution gate) → LEDGER (hash-chained audit).

An autonomous agent reads the spec, attests (agent key + architect
stamp + fresh nonce), and every sensitive call passes policy.check().
"""

from eci.protocol0.spec import Protocol0Spec, check_compatible, load_spec
from eci.protocol0.attest import (
    Attestation,
    ReplayWindow,
    architect_anchor_available,
    issue_attestation,
    verify_attestation,
)
from eci.protocol0.policy import PolicyDecision, check
from eci.protocol0.middleware import Middleware
from eci.protocol0 import keys as keys
from eci.protocol0 import transparency as transparency
from eci.protocol0.ledger import Ledger
from eci.protocol0.gates import gated_consensus, gated_dao_vote

__all__ = [
    "Protocol0Spec",
    "load_spec",
    "check_compatible",
    "Attestation",
    "ReplayWindow",
    "architect_anchor_available",
    "issue_attestation",
    "verify_attestation",
    "PolicyDecision",
    "check",
    "Middleware",
    "keys",
    "transparency",
    "Ledger",
    "gated_consensus",
    "gated_dao_vote",
]
