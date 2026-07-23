from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base
from backend.app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Prospect(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "prospects"
    __table_args__ = (
        Index("ix_prospects_org_status", "organization_id", "status"),
        Index("ix_prospects_org_stage", "organization_id", "pipeline_stage"),
        Index("ix_prospects_org_priority", "organization_id", "priority"),
        Index("ix_prospects_org_next_action", "organization_id", "next_action_at"),
        Index("ix_prospects_org_updated", "organization_id", "updated_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_profiles.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_profiles.id", ondelete="RESTRICT"), nullable=False
    )

    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    contact_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    contact_first_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    contact_last_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    job_title: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    email: Mapped[str] = mapped_column(String(320), nullable=False, default="")
    phone: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    mobile: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    website: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    siren: Mapped[str] = mapped_column(String(9), nullable=False, default="")
    siret: Mapped[str] = mapped_column(String(14), nullable=False, default="")
    naf_code: Mapped[str] = mapped_column(String(10), nullable=False, default="")
    activity: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    workforce: Mapped[int | None] = mapped_column(Integer, nullable=True)
    annual_revenue: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    address: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    postal_code: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    city: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    country: Mapped[str] = mapped_column(String(120), nullable=False, default="France")
    pipeline_stage: Mapped[str] = mapped_column(String(80), nullable=False, default="nouveau")
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="normal")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    source: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    next_action: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    next_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    owner = relationship("UserProfile", foreign_keys=[owner_user_id])
