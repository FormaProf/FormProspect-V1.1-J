from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.security import AuthContext, get_auth_context
from backend.app.schemas.crm import ActivityComplete, ActivityCreate, ActivityResponse, ActivityUpdate, PipelineStageResponse, StageChange, StageHistoryResponse, StageChangeResponse
from backend.app.schemas.prospect import ProspectResponse
from backend.app.services import crm_service
from backend.app.services.audit_service import record_audit
from backend.app.services.prospect_service import get_prospect

router = APIRouter(tags=["crm"])

@router.get("/pipeline/stages", response_model=list[PipelineStageResponse])
def stages(context: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    items = crm_service.list_stages(db, context); db.commit(); return items

@router.post("/prospects/{prospect_id}/stage", response_model=StageChangeResponse)
def change_stage(prospect_id: uuid.UUID, payload: StageChange, request: Request,
                 context: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    prospect = get_prospect(db, context, prospect_id)
    history = crm_service.transition_stage(db, context, prospect, payload.pipeline_stage, payload.note)
    record_audit(db, request, "prospect.stage_changed", context=context, entity_type="prospect",
                 entity_id=str(prospect.id), before_data={"pipeline_stage": history.from_stage},
                 after_data={"pipeline_stage": history.to_stage, "note": history.note})
    db.commit(); db.refresh(prospect)
    data = {column.name: getattr(prospect, column.name) for column in prospect.__table__.columns}
    data.update({"from_stage": history.from_stage, "to_stage": history.to_stage, "note": history.note})
    return data

@router.get("/prospects/{prospect_id}/stage-history", response_model=list[StageHistoryResponse])
def history(prospect_id: uuid.UUID, context: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    return crm_service.list_history(db, context, prospect_id)

@router.get("/prospects/{prospect_id}/activities", response_model=list[ActivityResponse])
def activities(prospect_id: uuid.UUID, status_filter: str | None = Query(default=None, alias="status"),
               context: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    return crm_service.list_activities(db, context, prospect_id, status_filter)

@router.post("/prospects/{prospect_id}/activities", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
def create(prospect_id: uuid.UUID, payload: ActivityCreate, request: Request,
           context: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    item = crm_service.create_activity(db, context, prospect_id, payload)
    record_audit(db, request, "activity.created", context=context, entity_type="prospect_activity",
                 entity_id=str(item.id), after_data={"subject": item.subject, "type": item.activity_type})
    db.commit(); db.refresh(item); return item

@router.patch("/activities/{activity_id}", response_model=ActivityResponse)
def update(activity_id: uuid.UUID, payload: ActivityUpdate, request: Request,
           context: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    item = crm_service.update_activity(db, context, activity_id, payload)
    record_audit(db, request, "activity.updated", context=context, entity_type="prospect_activity", entity_id=str(item.id))
    db.commit(); db.refresh(item); return item

@router.post("/activities/{activity_id}/complete", response_model=ActivityResponse)
def complete(activity_id: uuid.UUID, payload: ActivityComplete, request: Request,
             context: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    item = crm_service.update_activity(db, context, activity_id, ActivityUpdate(status="completed", outcome=payload.outcome))
    record_audit(db, request, "activity.completed", context=context, entity_type="prospect_activity", entity_id=str(item.id))
    db.commit(); db.refresh(item); return item

@router.get("/activities/due", response_model=list[ActivityResponse])
def due(overdue_only: bool = False, context: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    return crm_service.due_activities(db, context, overdue_only)
