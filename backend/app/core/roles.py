from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    MANAGER = "manager"
    COMMERCIAL = "commercial"
    TRAINER = "trainer"
    ADMIN_ASSISTANT = "admin_assistant"


class Permission(StrEnum):
    ORGANIZATION_READ = "organization:read"
    USER_READ = "user:read"
    USER_MANAGE = "user:manage"
    AUDIT_READ = "audit:read"
    PROSPECT_READ_ALL = "prospect:read_all"
    PROSPECT_READ_ASSIGNED = "prospect:read_assigned"
    PROSPECT_CREATE = "prospect:create"
    PROSPECT_UPDATE_ALL = "prospect:update_all"
    PROSPECT_UPDATE_ASSIGNED = "prospect:update_assigned"
    PROSPECT_ASSIGN = "prospect:assign"
    PROSPECT_ARCHIVE = "prospect:archive"
    SALE_READ_ALL = "sale:read_all"
    SALE_READ_OWN = "sale:read_own"
    DOCUMENT_MANAGE = "document:manage"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.ADMIN: frozenset(Permission),
    Role.MANAGER: frozenset(
        {
            Permission.ORGANIZATION_READ,
            Permission.USER_READ,
            Permission.AUDIT_READ,
            Permission.PROSPECT_READ_ALL,
            Permission.PROSPECT_CREATE,
            Permission.PROSPECT_UPDATE_ALL,
            Permission.PROSPECT_ASSIGN,
            Permission.PROSPECT_ARCHIVE,
            Permission.SALE_READ_ALL,
            Permission.DOCUMENT_MANAGE,
        }
    ),
    Role.COMMERCIAL: frozenset(
        {
            Permission.ORGANIZATION_READ,
            Permission.PROSPECT_READ_ASSIGNED,
            Permission.PROSPECT_CREATE,
            Permission.PROSPECT_UPDATE_ASSIGNED,
            Permission.PROSPECT_ARCHIVE,
            Permission.SALE_READ_OWN,
        }
    ),
    Role.TRAINER: frozenset({Permission.ORGANIZATION_READ}),
    Role.ADMIN_ASSISTANT: frozenset(
        {
            Permission.ORGANIZATION_READ,
            Permission.USER_READ,
            Permission.PROSPECT_READ_ALL,
            Permission.PROSPECT_CREATE,
            Permission.PROSPECT_UPDATE_ALL,
            Permission.DOCUMENT_MANAGE,
        }
    ),
}


def has_permission(role: Role, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, frozenset())

