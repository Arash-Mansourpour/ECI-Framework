"""RBAC store: roles, permissions, grants with wildcard resources."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from typing import Dict, List, Set

__all__ = ["Permission", "Role", "RBAC"]


@dataclass(frozen=True)
class Permission:
    action: str   # e.g. "ledger.append", "tool.*"
    resource: str = "*"  # e.g. "mesh/*", "agent/alice"


@dataclass
class Role:
    name: str
    permissions: List[Permission] = field(default_factory=list)


class RBAC:
    def __init__(self) -> None:
        self.roles: Dict[str, Role] = {}
        self.grants: Dict[str, Set[str]] = {}  # subject -> role names

    def add_role(self, role: Role) -> None:
        self.roles[role.name] = role

    def grant(self, subject: str, role: str) -> None:
        if role not in self.roles:
            raise KeyError(f"unknown role {role!r}")
        self.grants.setdefault(subject, set()).add(role)

    def revoke(self, subject: str, role: str) -> None:
        self.grants.get(subject, set()).discard(role)

    def allows(self, subject: str, action: str, resource: str = "*") -> bool:
        for role_name in self.grants.get(subject, ()):  # type: ignore[union-attr]
            role = self.roles.get(role_name)
            if role is None:
                continue
            for p in role.permissions:
                if fnmatch.fnmatchcase(action, p.action) and fnmatch.fnmatchcase(resource, p.resource):
                    return True
        return False

    def roles_of(self, subject: str) -> List[str]:
        return sorted(self.grants.get(subject, set()))
