from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from backend.app.core.roles import Role


class UserAdminResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    role: Role
    active: bool
    created_at: datetime
    last_login: datetime | None = None


class UserCreateRequest(BaseModel):
    email: EmailStr
    first_name: str = Field(default="", max_length=100)
    last_name: str = Field(default="", max_length=100)
    role: Role = Role.COMMERCIAL


class UserUpdateRequest(BaseModel):
    role: Role | None = None
    active: bool | None = None


class AuditResponse(BaseModel):
    id: uuid.UUID
    action: str
    actor_email: str = ""
    entity_type: str
    entity_id: str
    occurred_at: datetime
    ip_address: str
    device_id: str
