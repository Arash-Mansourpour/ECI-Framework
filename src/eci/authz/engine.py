"""ABAC policy engine layered over RBAC + Protocol-0 attestations.

Decision = DENY by default; ALLOW requires (a) RBAC grant, (b) attribute
predicates (tenant match, consciousness/trust floors, time window), and
(c) optional Protocol-0 attestation thresholds. Every decision returns a
structured verdict suitable for audit + provenance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from eci.authz.rbac import RBAC

__all__ = ["PolicyRule", "Decision", "PolicyEngine"]


@dataclass
class PolicyRule:
    name: str
    action: str            # fnmatch pattern
    resource: str = "*"    # fnmatch pattern
    require_attrs: dict[str, Any] = field(default_factory=dict)
    min_awareness: float = 0.0
    min_obedience: float = 0.0
    min_trust: float = 0.0


@dataclass
class Decision:
    allow: bool
    rule: str = ""
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"allow": self.allow, "rule": self.rule, "reasons": self.reasons}


class PolicyEngine:
    name = "authz"

    def __init__(self, rbac: RBAC | None = None) -> None:
        self.rbac = rbac or RBAC()
        self.rules: list[PolicyRule] = []
        self.decisions = 0
        self.allows = 0

    def add_rule(self, rule: PolicyRule) -> None:
        self.rules.append(rule)

    def decide(self, subject: str, action: str, resource: str = "*",
               attrs: dict[str, Any] | None = None,
               attestation: dict[str, float] | None = None) -> Decision:
        import fnmatch
        attrs = attrs or {}
        attestation = attestation or {}
        self.decisions += 1
        if not self.rbac.allows(subject, action, resource):
            return Decision(False, "", ["rbac: no grant"])
        for rule in self.rules:
            if not (fnmatch.fnmatchcase(action, rule.action) and fnmatch.fnmatchcase(resource, rule.resource)):
                continue
            reasons: list[str] = [f"rule:{rule.name}"]
            ok = True
            for k, v in rule.require_attrs.items():
                if attrs.get(k) != v:
                    ok = False
                    reasons.append(f"attr {k}={attrs.get(k)!r} != {v!r}")
            for key, floor in (("awareness", rule.min_awareness), ("obedience", rule.min_obedience), ("trust", rule.min_trust)):
                if attestation.get(key, 1.0) < floor:
                    ok = False
                    reasons.append(f"attestation {key} {attestation.get(key, 0.0)} < {floor}")
            if ok:
                self.allows += 1
                return Decision(True, rule.name, reasons)
        # RBAC granted but no ABAC rule matched => deny-closed (safe default)
        return Decision(False, "", ["abac: no rule matched (deny-closed)"])

    def start(self) -> None: ...
    def stop(self) -> None: ...
    def health(self) -> dict[str, Any]:
        return {"ok": True, "rules": len(self.rules), "decisions": self.decisions, "allows": self.allows}
