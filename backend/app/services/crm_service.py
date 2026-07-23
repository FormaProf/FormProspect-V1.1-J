from __future__ import annotations
import uuid
from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.core.roles import Permission, has_permission
from backend.app.core.security import AuthContext
from backend.app.models.crm import PipelineStage, ProspectActivity, ProspectStageHistory
from backend.app.models.prospect import Prospect
from backend.app.schemas.crm import ActivityCreate, ActivityUpdate
from backend.app.services.prospect_service import can_update, get_prospect, validate_owner

DEFAULT_STAGES = [
("Nouveau","nouveau",10,False,False),("À contacter","a_contacter",20,False,False),
("Contacté","contacte",30,False,False),("RDV planifié","rdv_planifie",40,False,False),
("Proposition envoyée","proposition_envoyee",50,False,False),("Négociation","negociation",60,False,False),
("Gagné","gagne",70,True,False),("Perdu","perdu",80,False,True)]

def ensure_default_stages(db: Session, context: AuthContext):
    if db.scalar(select(PipelineStage.id).where(PipelineStage.organization_id==context.organization_id).limit(1)): return
    for name,slug,pos,won,lost in DEFAULT_STAGES:
        db.add(PipelineStage(organization_id=context.organization_id,name=name,slug=slug,position=pos,is_won=won,is_lost=lost,is_active=True,created_by=context.user_id))
    db.flush()

def list_stages(db, context):
    ensure_default_stages(db,context)
    return list(db.scalars(select(PipelineStage).where(PipelineStage.organization_id==context.organization_id,PipelineStage.is_active.is_(True)).order_by(PipelineStage.position)))

def transition_stage(db, context, prospect, slug, note):
    if not can_update(context,prospect): raise HTTPException(403,"Modification interdite.")
    ensure_default_stages(db,context)
    stage=db.scalar(select(PipelineStage).where(PipelineStage.organization_id==context.organization_id,PipelineStage.slug==slug,PipelineStage.is_active.is_(True)))
    if stage is None: raise HTTPException(422,"Étape de pipeline inconnue ou inactive.")
    history=ProspectStageHistory(organization_id=context.organization_id,prospect_id=prospect.id,changed_by=context.user_id,from_stage=prospect.pipeline_stage,to_stage=slug,note=note)
    prospect.pipeline_stage=slug; db.add(history); db.flush(); return history

def list_history(db,context,prospect_id):
    get_prospect(db,context,prospect_id)
    return list(db.scalars(select(ProspectStageHistory).where(ProspectStageHistory.organization_id==context.organization_id,ProspectStageHistory.prospect_id==prospect_id).order_by(ProspectStageHistory.created_at.desc())))

def list_activities(db,context,prospect_id,status=None):
    get_prospect(db,context,prospect_id)
    stmt=select(ProspectActivity).where(ProspectActivity.organization_id==context.organization_id,ProspectActivity.prospect_id==prospect_id)
    if status: stmt=stmt.where(ProspectActivity.status==status)
    return list(db.scalars(stmt.order_by(ProspectActivity.scheduled_at.desc(),ProspectActivity.created_at.desc())))

def create_activity(db,context,prospect_id,payload:ActivityCreate):
    prospect=get_prospect(db,context,prospect_id)
    if not can_update(context,prospect): raise HTTPException(403,"Création d'activité interdite.")
    assigned=payload.assigned_to or prospect.owner_user_id
    if assigned!=context.user_id and not has_permission(context.role,Permission.PROSPECT_ASSIGN): raise HTTPException(403,"Affectation interdite.")
    validate_owner(db,context,assigned)
    item=ProspectActivity(**payload.model_dump(exclude={"assigned_to"}),organization_id=context.organization_id,prospect_id=prospect_id,assigned_to=assigned,created_by=context.user_id)
    if item.status=="completed": item.completed_at=datetime.now(timezone.utc)
    db.add(item);db.flush();return item

def get_activity(db,context,activity_id):
    item=db.scalar(select(ProspectActivity).where(ProspectActivity.id==activity_id,ProspectActivity.organization_id==context.organization_id))
    if item is None: raise HTTPException(404,"Activité introuvable.")
    get_prospect(db,context,item.prospect_id); return item

def update_activity(db,context,activity_id,payload:ActivityUpdate):
    item=get_activity(db,context,activity_id); prospect=get_prospect(db,context,item.prospect_id)
    if not can_update(context,prospect): raise HTTPException(403,"Modification interdite.")
    changes=payload.model_dump(exclude_unset=True)
    if changes.get("assigned_to") is not None: validate_owner(db,context,changes["assigned_to"])
    for k,v in changes.items(): setattr(item,k,v)
    if item.status=="completed" and item.completed_at is None: item.completed_at=datetime.now(timezone.utc)
    if item.status!="completed": item.completed_at=None
    db.flush();return item

def due_activities(db,context,overdue_only=False):
    stmt=select(ProspectActivity).join(Prospect,Prospect.id==ProspectActivity.prospect_id).where(ProspectActivity.organization_id==context.organization_id,ProspectActivity.status=="planned",ProspectActivity.scheduled_at.is_not(None),Prospect.status=="active")
    if overdue_only: stmt=stmt.where(ProspectActivity.scheduled_at<=datetime.now(timezone.utc))
    if not has_permission(context.role,Permission.PROSPECT_READ_ALL): stmt=stmt.where(Prospect.owner_user_id==context.user_id)
    return list(db.scalars(stmt.order_by(ProspectActivity.scheduled_at.asc())))
