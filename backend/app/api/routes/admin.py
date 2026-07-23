from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.roles import Permission, Role
from backend.app.core.security import AuthContext, require_permission
from backend.app.models.audit import AuditLog
from backend.app.models.identity import OrganizationMembership, UserProfile
from backend.app.schemas.admin import AuditResponse, UserAdminResponse, UserCreateRequest, UserUpdateRequest
from backend.app.services.audit_service import record_audit
from backend.app.services.supabase_admin_service import SupabaseAdminError, SupabaseAdminService, get_supabase_admin

router = APIRouter(prefix="/admin", tags=["administration"])


def _user_response(profile: UserProfile, membership: OrganizationMembership) -> UserAdminResponse:
    return UserAdminResponse(
        id=membership.id, user_id=profile.id, email=profile.email,
        first_name=profile.first_name, last_name=profile.last_name,
        role=Role(membership.role), active=membership.is_active,
        created_at=membership.created_at, last_login=profile.last_login_at,
    )


def _membership(db: Session, context: AuthContext, membership_id: uuid.UUID):
    row = db.execute(
        select(UserProfile, OrganizationMembership)
        .join(OrganizationMembership, OrganizationMembership.user_id == UserProfile.id)
        .where(OrganizationMembership.id == membership_id, OrganizationMembership.organization_id == context.organization_id)
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")
    return row


def _protect_last_admin(db: Session, context: AuthContext, target: OrganizationMembership, *, new_role=None, new_active=None):
    removes_admin = target.role == Role.ADMIN.value and target.is_active and (
        (new_role is not None and new_role != Role.ADMIN) or new_active is False
    )
    if not removes_admin:
        return
    count = db.scalar(
        select(func.count()).select_from(OrganizationMembership).where(
            OrganizationMembership.organization_id == context.organization_id,
            OrganizationMembership.role == Role.ADMIN.value,
            OrganizationMembership.is_active.is_(True),
        )
    )
    if int(count or 0) <= 1:
        raise HTTPException(status_code=409, detail="Le dernier administrateur actif ne peut pas être désactivé ou rétrogradé.")


@router.get("/users", response_model=list[UserAdminResponse])
def list_users(
    context: AuthContext = Depends(require_permission(Permission.USER_READ)),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        select(UserProfile, OrganizationMembership)
        .join(OrganizationMembership, OrganizationMembership.user_id == UserProfile.id)
        .where(OrganizationMembership.organization_id == context.organization_id)
        .order_by(UserProfile.last_name, UserProfile.first_name, UserProfile.email)
    )
    return [_user_response(profile, membership) for profile, membership in rows]


@router.post("/users", response_model=UserAdminResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreateRequest, request: Request,
    context: AuthContext = Depends(require_permission(Permission.USER_MANAGE)),
    db: Session = Depends(get_db),
    supabase: SupabaseAdminService = Depends(get_supabase_admin),
):
    email = str(payload.email).strip().lower()
    existing = db.execute(
        select(UserProfile, OrganizationMembership)
        .join(OrganizationMembership, OrganizationMembership.user_id == UserProfile.id)
        .where(UserProfile.email == email, OrganizationMembership.organization_id == context.organization_id)
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Cet utilisateur appartient déjà à l'organisation.")
    try:
        auth_user_id = supabase.invite_user(email, payload.first_name.strip(), payload.last_name.strip())
    except SupabaseAdminError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    provisioned = None
    try:
        if db.bind is not None and db.bind.dialect.name == "postgresql":
            provisioned = supabase.provision_member(
                auth_user_id, context.organization_id, email,
                payload.first_name.strip(), payload.last_name.strip(), payload.role.value,
            )
            profile, membership = _membership(db, context, provisioned[1])
        else:
            profile = db.scalar(select(UserProfile).where(UserProfile.auth_user_id == auth_user_id))
            if profile is None:
                profile = UserProfile(auth_user_id=auth_user_id, email=email, first_name=payload.first_name.strip(), last_name=payload.last_name.strip())
                db.add(profile)
                db.flush()
            membership = OrganizationMembership(organization_id=context.organization_id, user_id=profile.id, role=payload.role.value, is_active=True)
            db.add(membership)
            db.flush()
        record_audit(db, request, "user.invited", context=context, entity_type="membership", entity_id=str(membership.id), after_data={"email": email, "role": payload.role.value})
        response = _user_response(profile, membership)
        db.commit()
        return response
    except Exception:
        db.rollback()
        if provisioned is not None:
            supabase.cleanup_member(provisioned[0], provisioned[1])
        try:
            supabase.delete_user(auth_user_id)
        except SupabaseAdminError:
            pass
        raise


@router.patch("/users/{membership_id}", response_model=UserAdminResponse)
def update_user(
    membership_id: uuid.UUID, payload: UserUpdateRequest, request: Request,
    context: AuthContext = Depends(require_permission(Permission.USER_MANAGE)),
    db: Session = Depends(get_db),
):
    profile, membership = _membership(db, context, membership_id)
    if payload.role is None and payload.active is None:
        raise HTTPException(status_code=422, detail="Aucune modification demandée.")
    _protect_last_admin(db, context, membership, new_role=payload.role, new_active=payload.active)
    before = {"role": membership.role, "active": membership.is_active}
    if payload.role is not None:
        membership.role = payload.role.value
    if payload.active is not None:
        membership.is_active = payload.active
    after = {"role": membership.role, "active": membership.is_active}
    record_audit(db, request, "user.updated", context=context, entity_type="membership", entity_id=str(membership.id), before_data=before, after_data=after)
    response = _user_response(profile, membership)
    db.commit()
    return response


@router.post("/users/{membership_id}/password-reset", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(
    membership_id: uuid.UUID, request: Request,
    context: AuthContext = Depends(require_permission(Permission.USER_MANAGE)),
    db: Session = Depends(get_db),
    supabase: SupabaseAdminService = Depends(get_supabase_admin),
):
    profile, membership = _membership(db, context, membership_id)
    try:
        supabase.send_password_reset(profile.email)
    except SupabaseAdminError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    record_audit(db, request, "user.password_reset_requested", context=context, entity_type="membership", entity_id=str(membership.id))
    db.commit()


@router.get("/audit", response_model=list[AuditResponse])
def audit_log(
    limit: int = Query(default=100, ge=1, le=500),
    context: AuthContext = Depends(require_permission(Permission.AUDIT_READ)),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        select(AuditLog, UserProfile.email)
        .outerjoin(UserProfile, UserProfile.id == AuditLog.actor_user_id)
        .where(AuditLog.organization_id == context.organization_id)
        .order_by(AuditLog.occurred_at.desc()).limit(limit)
    )
    return [AuditResponse(
        id=entry.id, action=entry.action, actor_email=email or "",
        entity_type=entry.entity_type, entity_id=entry.entity_id,
        occurred_at=entry.occurred_at, ip_address=entry.ip_address, device_id=entry.device_id,
    ) for entry, email in rows]
