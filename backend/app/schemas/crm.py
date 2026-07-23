from __future__ import annotations
import uuid
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

ActivityType = Literal["call", "email", "meeting", "task", "note"]
ActivityStatus = Literal["planned", "completed", "cancelled"]
Priority = Literal["basse", "normal", "haute", "urgente"]

class PipelineStageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    slug: str
    key: str = Field(validation_alias="slug")
    position: int
    is_won: bool
    is_lost: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

class StageChange(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    pipeline_stage: str = Field(min_length=1, max_length=80, alias="stage")
    note: str = Field(default="", max_length=500)
    @field_validator("pipeline_stage", mode="before")
    @classmethod
    def normalize_stage(cls, value: object) -> str:
        return str(value or "").strip().lower()
    @field_validator("note", mode="before")
    @classmethod
    def trim_note(cls, value: object) -> str:
        return str(value or "").strip()

class StageHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    prospect_id: uuid.UUID
    changed_by: uuid.UUID
    from_stage: str
    to_stage: str
    note: str
    created_at: datetime

class ActivityCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    activity_type: ActivityType
    subject: str = Field(min_length=1, max_length=200, alias="title")
    description: str = Field(default="", max_length=5000)
    outcome: str = Field(default="", max_length=300)
    status: ActivityStatus = "planned"
    priority: Priority = "normal"
    scheduled_at: datetime | None = None
    assigned_to: uuid.UUID | None = None
    @field_validator("subject", "description", "outcome", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> str:
        return str(value or "").strip()

class ActivityUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    subject: str | None = Field(default=None, min_length=1, max_length=200, alias="title")
    description: str | None = Field(default=None, max_length=5000)
    outcome: str | None = Field(default=None, max_length=300)
    status: ActivityStatus | None = None
    priority: Priority | None = None
    scheduled_at: datetime | None = None
    assigned_to: uuid.UUID | None = None

class ActivityComplete(BaseModel):
    outcome: str = Field(default="", max_length=300)

class ActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    organization_id: uuid.UUID
    prospect_id: uuid.UUID
    created_by: uuid.UUID
    assigned_to: uuid.UUID
    activity_type: str
    subject: str
    title: str = Field(validation_alias="subject")
    description: str
    outcome: str
    status: str
    priority: str
    scheduled_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class StageChangeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    organization_id: uuid.UUID
    owner_user_id: uuid.UUID
    created_by: uuid.UUID
    company_name: str
    contact_name: str
    contact_first_name: str
    contact_last_name: str
    job_title: str
    email: str
    phone: str
    mobile: str
    website: str
    siren: str
    siret: str
    naf_code: str
    activity: str
    workforce: int | None
    annual_revenue: object | None
    address: str
    postal_code: str
    city: str
    country: str
    pipeline_stage: str
    priority: str
    status: str
    source: str
    next_action: str
    next_action_at: datetime | None
    notes: str
    created_at: datetime
    updated_at: datetime
    from_stage: str
    to_stage: str
    note: str
