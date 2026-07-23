from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base
from backend.app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class PipelineStage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "pipeline_stages"
    __table_args__ = (
        Index("uq_pipeline_stages_org_slug", "organization_id", "slug", unique=True),
        Index("ix_pipeline_stages_org_position", "organization_id", "position"),
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_won: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_lost: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("user_profiles.id", ondelete="RESTRICT"), nullable=False)


class ProspectStageHistory(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "prospect_stage_history"
    __table_args__ = (Index("ix_stage_history_org_prospect_created", "organization_id", "prospect_id", "created_at"),)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    prospect_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False, index=True)
    changed_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("user_profiles.id", ondelete="RESTRICT"), nullable=False)
    from_stage: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    to_stage: Mapped[str] = mapped_column(String(80), nullable=False)
    note: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class ProspectActivity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "prospect_activities"
    __table_args__ = (
        Index("ix_activities_org_prospect_scheduled", "organization_id", "prospect_id", "scheduled_at"),
        Index("ix_activities_org_assigned_status", "organization_id", "assigned_to", "status"),
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    prospect_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("user_profiles.id", ondelete="RESTRICT"), nullable=False)
    assigned_to: Mapped[uuid.UUID] = mapped_column(ForeignKey("user_profiles.id", ondelete="RESTRICT"), nullable=False, index=True)
    activity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    outcome: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="planned")
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="normal")
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
