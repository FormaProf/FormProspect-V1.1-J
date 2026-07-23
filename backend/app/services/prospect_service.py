from __future__ import annotations

import uuid
from typing import Literal

from fastapi import HTTPException
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from backend.app.core.roles import Permission, has_permission
from backend.app.core.security import AuthContext
from backend.app.models.identity import OrganizationMembership
from backend.app.models.prospect import Prospect
from backend.app.schemas.prospect import ProspectCreate, ProspectUpdate

SortField = Literal["updated_at", "created_at", "company_name", "city", "priority", "next_action_at"]
SortDirection = Literal["asc", "desc"]


def can_read_all(context: AuthContext) -> bool:
    return has_permission(context.role, Permission.PROSPECT_READ_ALL)


def can_update(context: AuthContext, prospect: Prospect) -> bool:
    if has_permission(context.role, Permission.PROSPECT_UPDATE_ALL):
        return True
    return (
        prospect.owner_user_id == context.user_id
        and has_permission(context.role, Permission.PROSPECT_UPDATE_ASSIGNED)
    )


def visible_statement(statement: Select, context: AuthContext) -> Select:
    if can_read_all(context):
        return statement
    if has_permission(context.role, Permission.PROSPECT_READ_ASSIGNED):
        return statement.where(Prospect.owner_user_id == context.user_id)
    raise HTTPException(status_code=403, detail="Permission insuffisante.")


def validate_owner(db: Session, context: AuthContext, owner_id: uuid.UUID) -> None:
    membership = db.scalar(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == context.organization_id,
            OrganizationMembership.user_id == owner_id,
            OrganizationMembership.is_active.is_(True),
        )
    )
    if membership is None:
        raise HTTPException(
            status_code=422,
            detail="Le commercial affecté n'appartient pas à cette organisation.",
        )


def _filtered_statement(
    context: AuthContext,
    *,
    search: str = "",
    include_archived: bool = False,
    status: str | None = None,
    pipeline_stage: str | None = None,
    priority: str | None = None,
    city: str | None = None,
    naf_code: str | None = None,
    source: str | None = None,
    owner_user_id: uuid.UUID | None = None,
) -> Select:
    statement = select(Prospect).where(Prospect.organization_id == context.organization_id)
    statement = visible_statement(statement, context)

    if status and status.strip():
        statement = statement.where(Prospect.status == status.strip().lower())
    elif not include_archived:
        statement = statement.where(Prospect.status == "active")
    if pipeline_stage and pipeline_stage.strip():
        statement = statement.where(Prospect.pipeline_stage == pipeline_stage.strip())
    if priority and priority.strip():
        statement = statement.where(Prospect.priority == priority.strip().lower())
    if city and city.strip():
        statement = statement.where(Prospect.city.ilike(city.strip()))
    if naf_code and naf_code.strip():
        statement = statement.where(Prospect.naf_code == naf_code.strip().upper())
    if source and source.strip():
        statement = statement.where(Prospect.source.ilike(source.strip()))
    if owner_user_id is not None:
        if not can_read_all(context) and owner_user_id != context.user_id:
            raise HTTPException(status_code=403, detail="Filtre propriétaire interdit.")
        statement = statement.where(Prospect.owner_user_id == owner_user_id)
    if search.strip():
        term = f"%{search.strip()}%"
        statement = statement.where(
            or_(
                Prospect.company_name.ilike(term),
                Prospect.contact_name.ilike(term),
                Prospect.contact_first_name.ilike(term),
                Prospect.contact_last_name.ilike(term),
                Prospect.job_title.ilike(term),
                Prospect.email.ilike(term),
                Prospect.phone.ilike(term),
                Prospect.mobile.ilike(term),
                Prospect.siren.ilike(term),
                Prospect.siret.ilike(term),
                Prospect.naf_code.ilike(term),
                Prospect.city.ilike(term),
                Prospect.activity.ilike(term),
            )
        )
    return statement


def list_prospects(
    db: Session,
    context: AuthContext,
    *,
    search: str = "",
    include_archived: bool = False,
    status: str | None = None,
    pipeline_stage: str | None = None,
    priority: str | None = None,
    city: str | None = None,
    naf_code: str | None = None,
    source: str | None = None,
    owner_user_id: uuid.UUID | None = None,
    sort_by: SortField = "updated_at",
    sort_direction: SortDirection = "desc",
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[Prospect], int]:
    statement = _filtered_statement(
        context,
        search=search,
        include_archived=include_archived,
        status=status,
        pipeline_stage=pipeline_stage,
        priority=priority,
        city=city,
        naf_code=naf_code,
        source=source,
        owner_user_id=owner_user_id,
    )
    count_statement = select(func.count()).select_from(statement.order_by(None).subquery())
    total = int(db.scalar(count_statement) or 0)

    sort_column = getattr(Prospect, sort_by)
    ordering = sort_column.asc() if sort_direction == "asc" else sort_column.desc()
    statement = statement.order_by(ordering, Prospect.id.asc()).offset(offset).limit(limit)
    return list(db.scalars(statement)), total


def get_prospect(db: Session, context: AuthContext, prospect_id: uuid.UUID) -> Prospect:
    statement = select(Prospect).where(
        Prospect.id == prospect_id,
        Prospect.organization_id == context.organization_id,
    )
    prospect = db.scalar(visible_statement(statement, context))
    if prospect is None:
        raise HTTPException(status_code=404, detail="Prospect introuvable.")
    return prospect


def create_prospect(db: Session, context: AuthContext, payload: ProspectCreate) -> Prospect:
    owner_id = payload.owner_user_id or context.user_id
    if owner_id != context.user_id and not has_permission(context.role, Permission.PROSPECT_ASSIGN):
        raise HTTPException(
            status_code=403,
            detail="Vous ne pouvez pas affecter un prospect à un autre utilisateur.",
        )
    validate_owner(db, context, owner_id)

    prospect = Prospect(
        **payload.model_dump(exclude={"owner_user_id"}),
        organization_id=context.organization_id,
        owner_user_id=owner_id,
        created_by=context.user_id,
    )
    db.add(prospect)
    db.flush()
    return prospect


def update_prospect(
    db: Session,
    context: AuthContext,
    prospect: Prospect,
    payload: ProspectUpdate,
) -> tuple[dict, dict]:
    if not can_update(context, prospect):
        raise HTTPException(status_code=403, detail="Modification interdite.")

    changes = payload.model_dump(exclude_unset=True)
    owner_id = changes.pop("owner_user_id", None)
    if owner_id is not None and owner_id != prospect.owner_user_id:
        if not has_permission(context.role, Permission.PROSPECT_ASSIGN):
            raise HTTPException(status_code=403, detail="Réaffectation interdite.")
        validate_owner(db, context, owner_id)
        changes["owner_user_id"] = owner_id

    before = {key: getattr(prospect, key) for key in changes}
    for key, value in changes.items():
        setattr(prospect, key, value)
    after = {key: getattr(prospect, key) for key in changes}
    db.flush()
    return before, after


def set_archived(
    db: Session,
    context: AuthContext,
    prospect: Prospect,
    *,
    archived: bool,
) -> None:
    if not has_permission(context.role, Permission.PROSPECT_ARCHIVE):
        raise HTTPException(status_code=403, detail="Archivage interdit.")
    if not can_update(context, prospect):
        raise HTTPException(status_code=403, detail="Archivage interdit.")
    prospect.status = "archived" if archived else "active"
    db.flush()
