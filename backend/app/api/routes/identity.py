from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.roles import Permission
from backend.app.core.security import (
    AuthContext,
    VerifiedIdentity,
    get_auth_context,
    get_verified_identity,
    require_permission,
)
from backend.app.models.identity import Organization, OrganizationMembership, UserProfile
from backend.app.schemas.identity import CurrentUserResponse, MembershipResponse, OrganizationResponse
from backend.app.services.audit_service import record_audit

router = APIRouter(prefix="/identity", tags=["identity"])


@router.get("/memberships", response_model=list[MembershipResponse])
def memberships(
    identity: VerifiedIdentity = Depends(get_verified_identity),
    db: Session = Depends(get_db),
) -> list[MembershipResponse]:
    """Discover active tenants without trusting a tenant supplied by the client."""
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        rows = db.execute(
            text("SELECT * FROM app_discover_memberships(:auth_user_id)"),
            {"auth_user_id": str(identity.auth_user_id)},
        ).mappings()
        return [MembershipResponse(**row) for row in rows]

    statement = (
        select(UserProfile, OrganizationMembership, Organization)
        .join(OrganizationMembership, OrganizationMembership.user_id == UserProfile.id)
        .join(Organization, Organization.id == OrganizationMembership.organization_id)
        .where(
            UserProfile.auth_user_id == identity.auth_user_id,
            UserProfile.status == "active",
            OrganizationMembership.is_active.is_(True),
            Organization.status == "active",
        )
    )
    return [
        MembershipResponse(
            user_id=profile.id,
            organization_id=organization.id,
            organization_name=organization.name,
            organization_slug=organization.slug,
            email=profile.email,
            first_name=profile.first_name,
            last_name=profile.last_name,
            role=membership.role,
        )
        for profile, membership, organization in db.execute(statement)
    ]


@router.get("/me", response_model=CurrentUserResponse)
def current_user(context: AuthContext = Depends(get_auth_context)) -> CurrentUserResponse:
    return CurrentUserResponse.from_context(context)


@router.get("/organization", response_model=OrganizationResponse)
def current_organization(
    request: Request,
    context: AuthContext = Depends(require_permission(Permission.ORGANIZATION_READ)),
    db: Session = Depends(get_db),
) -> Organization:
    organization = db.get(Organization, context.organization_id)
    if organization is None:
        # Une adhésion valide sans organisation serait une incohérence de données.
        raise RuntimeError("Organisation introuvable.")
    record_audit(db, request, "organization.viewed", context=context, entity_type="organization", entity_id=str(organization.id))
    db.commit()
    return organization
