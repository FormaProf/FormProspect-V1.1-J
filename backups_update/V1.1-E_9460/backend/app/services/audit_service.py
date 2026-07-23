from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from backend.app.core.middleware import client_ip
from backend.app.core.security import AuthContext
from backend.app.models.audit import AuditLog


def record_audit(
    db: Session,
    request: Request,
    action: str,
    *,
    context: AuthContext | None = None,
    entity_type: str = "",
    entity_id: str = "",
    before_data: dict | None = None,
    after_data: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        organization_id=context.organization_id if context else None,
        actor_user_id=context.user_id if context else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_data=before_data,
        after_data=after_data,
        ip_address=client_ip(request),
        device_id=request.headers.get("X-Device-ID", "")[:128],
        user_agent=request.headers.get("User-Agent", "")[:512],
        request_id=getattr(request.state, "request_id", ""),
    )
    db.add(entry)
    return entry

