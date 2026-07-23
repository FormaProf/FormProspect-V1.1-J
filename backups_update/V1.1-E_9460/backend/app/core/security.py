from __future__ import annotations

import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from backend.app.core.config import Settings, get_settings
from backend.app.core.database import get_db
from backend.app.core.roles import Permission, Role, has_permission
from backend.app.models.identity import OrganizationMembership, UserProfile

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthContext:
    auth_user_id: uuid.UUID
    user_id: uuid.UUID
    organization_id: uuid.UUID
    role: Role
    email: str


@dataclass(frozen=True)
class VerifiedIdentity:
    auth_user_id: uuid.UUID
    email: str


class TokenVerifier:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._jwks_client = (
            jwt.PyJWKClient(settings.supabase_jwks_url) if settings.supabase_jwks_url else None
        )

    def decode(self, token: str) -> dict:
        options = {"require": ["sub", "exp", "iat"]}
        kwargs = {
            "audience": self.settings.supabase_jwt_audience,
            "issuer": self.settings.supabase_jwt_issuer or None,
            "leeway": self.settings.access_token_leeway_seconds,
            "options": options,
        }
        if self.settings.local_test_jwt_secret:
            return jwt.decode(token, self.settings.local_test_jwt_secret, algorithms=["HS256"], **kwargs)
        if not self._jwks_client:
            raise RuntimeError("SUPABASE_JWKS_URL n'est pas configuré.")
        signing_key = self._jwks_client.get_signing_key_from_jwt(token)
        return jwt.decode(token, signing_key.key, algorithms=["RS256", "ES256"], **kwargs)


def get_verified_identity(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> VerifiedIdentity:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentification requise.")
    try:
        claims = TokenVerifier(settings).decode(credentials.credentials)
        auth_user_id = uuid.UUID(str(claims["sub"]))
    except (jwt.PyJWTError, ValueError, KeyError, RuntimeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session invalide ou expirée.",
        ) from exc
    return VerifiedIdentity(auth_user_id=auth_user_id, email=str(claims.get("email", "")))


def get_auth_context(
    request: Request,
    identity: VerifiedIdentity = Depends(get_verified_identity),
    db: Session = Depends(get_db),
) -> AuthContext:
    auth_user_id = identity.auth_user_id

    requested_org = request.headers.get("X-Organization-ID", "")
    try:
        organization_id = uuid.UUID(requested_org)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="X-Organization-ID est requis et invalide.") from exc

    # Les politiques RLS PostgreSQL lisent cette valeur dans la transaction.
    # Le header reste non fiable : il ne donne accès qu'aux lignes de ce tenant,
    # puis l'adhésion active est obligatoirement validée ci-dessous.
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(
            text("SELECT set_config('app.organization_id', :organization_id, true)"),
            {"organization_id": str(organization_id)},
        )

    statement = (
        select(UserProfile, OrganizationMembership)
        .join(OrganizationMembership, OrganizationMembership.user_id == UserProfile.id)
        .where(
            UserProfile.auth_user_id == auth_user_id,
            UserProfile.status == "active",
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.is_active.is_(True),
        )
    )
    row = db.execute(statement).first()
    if row is None:
        raise HTTPException(status_code=403, detail="Compte désactivé ou organisation interdite.")
    profile, membership = row
    try:
        role = Role(membership.role)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="Rôle non reconnu.") from exc
    context = AuthContext(
        auth_user_id=auth_user_id,
        user_id=profile.id,
        organization_id=organization_id,
        role=role,
        email=profile.email,
    )
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(
            text("SELECT set_config('app.user_id', :user_id, true)"),
            {"user_id": str(profile.id)},
        )
    request.state.auth = context
    return context


def require_permission(permission: Permission):
    def dependency(context: AuthContext = Depends(get_auth_context)) -> AuthContext:
        if not has_permission(context.role, permission):
            raise HTTPException(status_code=403, detail="Permission insuffisante.")
        return context

    return dependency
