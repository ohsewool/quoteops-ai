from __future__ import annotations

from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    MANAGER = "manager"
    VIEWER = "viewer"


ROLE_RANK = {
    UserRole.VIEWER: 10,
    UserRole.MANAGER: 20,
    UserRole.ADMIN: 30,
}


def has_minimum_role(actual: UserRole, required: UserRole) -> bool:
    return ROLE_RANK[actual] >= ROLE_RANK[required]
