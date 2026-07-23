from __future__ import annotations

import uuid

from pydantic import BaseModel

from backend.app.core.roles import Permission, Role, ROLE_PERMISSIONS


class CurrentUserResponse(BaseModel):
    user_id: uuid.UUID
    organization_id: uuid.UUID
    email: str
    role: Role
    permissions: list[Permission]

    @classmethod
    def from_context(cls, context):
        return cls(
            user_id=context.user_id,
            organization_id=context.organization_id,
            email=context.email,
            role=context.role,
            permissions=sorted(ROLE_PERMISSIONS[context.role], key=str),
        )


class MembershipResponse(BaseModel):
    user_id: uuid.UUID
    organization_id: uuid.UUID
    organization_name: str
    organization_slug: str
    email: str
    first_name: str
    last_name: str
    role: Role


class OrganizationResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    status: str
    subscription_plan: str
    subscription_status: str

    model_config = {"from_attributes": True}
