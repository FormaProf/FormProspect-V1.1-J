from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.roles import Permission
from backend.app.core.security import AuthContext, get_auth_context, require_permission
from backend.app.schemas.prospect import ProspectCreate, ProspectResponse, ProspectUpdate
from backend.app.services import prospect_service
from backend.app.services.audit_service import record_audit

router = APIRouter(prefix="/prospects", tags=["prospects"])


def _audit_value(value: object) -> object:
    if isinstance(value, (uuid.UUID, datetime, Decimal)):
        return str(value)
    return value


def _audit_dict(values: dict) -> dict:
    return {key: _audit_value(value) for key, value in values.items()}


@router.get("", response_model=list[ProspectResponse])
def list_prospects(
    response: Response,
    search: str = Query(default="", max_length=200),
    include_archived: bool = False,
    prospect_status: str | None = Query(default=None, alias="status", max_length=30),
    pipeline_stage: str | None = Query(default=None, max_length=80),
    priority: str | None = Query(default=None, max_length=20),
    city: str | None = Query(default=None, max_length=120),
    naf_code: str | None = Query(default=None, max_length=10),
    source: str | None = Query(default=None, max_length=120),
    owner_user_id: uuid.UUID | None = None,
    sort_by: Literal[
        "updated_at", "created_at", "company_name", "city", "priority", "next_action_at"
    ] = "updated_at",
    sort_direction: Literal["asc", "desc"] = "desc",
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    context: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    items, total = prospect_service.list_prospects(
        db,
        context,
        search=search,
        include_archived=include_archived,
        status=prospect_status,
        pipeline_stage=pipeline_stage,
        priority=priority,
        city=city,
        naf_code=naf_code,
        source=source,
        owner_user_id=owner_user_id,
        sort_by=sort_by,
        sort_direction=sort_direction,
        limit=limit,
        offset=offset,
    )
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)
    return items


@router.get("/{prospect_id}", response_model=ProspectResponse)
def get_prospect(
    prospect_id: uuid.UUID,
    context: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    return prospect_service.get_prospect(db, context, prospect_id)


@router.post("", response_model=ProspectResponse, status_code=status.HTTP_201_CREATED)
def create_prospect(
    payload: ProspectCreate,
    request: Request,
    context: AuthContext = Depends(require_permission(Permission.PROSPECT_CREATE)),
    db: Session = Depends(get_db),
):
    prospect = prospect_service.create_prospect(db, context, payload)
    record_audit(
        db,
        request,
        "prospect.created",
        context=context,
        entity_type="prospect",
        entity_id=str(prospect.id),
        after_data={"company_name": prospect.company_name, "owner_user_id": str(prospect.owner_user_id)},
    )
    db.commit()
    db.refresh(prospect)
    return prospect


@router.patch("/{prospect_id}", response_model=ProspectResponse)
def update_prospect(
    prospect_id: uuid.UUID,
    payload: ProspectUpdate,
    request: Request,
    context: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    prospect = prospect_service.get_prospect(db, context, prospect_id)
    before, after = prospect_service.update_prospect(db, context, prospect, payload)
    record_audit(
        db,
        request,
        "prospect.updated",
        context=context,
        entity_type="prospect",
        entity_id=str(prospect.id),
        before_data=_audit_dict(before),
        after_data=_audit_dict(after),
    )
    db.commit()
    db.refresh(prospect)
    return prospect


@router.post("/{prospect_id}/archive", response_model=ProspectResponse)
def archive_prospect(
    prospect_id: uuid.UUID,
    request: Request,
    context: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    prospect = prospect_service.get_prospect(db, context, prospect_id)
    prospect_service.set_archived(db, context, prospect, archived=True)
    record_audit(
        db,
        request,
        "prospect.archived",
        context=context,
        entity_type="prospect",
        entity_id=str(prospect.id),
    )
    db.commit()
    db.refresh(prospect)
    return prospect


@router.delete("/{prospect_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_prospect(
    prospect_id: uuid.UUID,
    request: Request,
    context: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    prospect = prospect_service.get_prospect(db, context, prospect_id)
    prospect_service.set_archived(db, context, prospect, archived=True)
    record_audit(
        db,
        request,
        "prospect.archived",
        context=context,
        entity_type="prospect",
        entity_id=str(prospect.id),
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{prospect_id}/restore", response_model=ProspectResponse)
def restore_prospect(
    prospect_id: uuid.UUID,
    request: Request,
    context: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    prospect = prospect_service.get_prospect(db, context, prospect_id)
    prospect_service.set_archived(db, context, prospect, archived=False)
    record_audit(
        db,
        request,
        "prospect.restored",
        context=context,
        entity_type="prospect",
        entity_id=str(prospect.id),
    )
    db.commit()
    db.refresh(prospect)
    return prospect
