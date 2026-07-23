from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.config import Settings, get_settings
from backend.app.core.database import Base, get_db
from backend.app.main import create_app
from backend.app.models import Organization, OrganizationMembership, UserProfile

TEST_SECRET = "test-only-secret-with-at-least-32-characters"


@pytest.fixture()
def test_context():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    org_id = uuid.uuid4()
    other_org_id = uuid.uuid4()
    auth_user_id = uuid.uuid4()
    user_id = uuid.uuid4()
    with session_factory() as db:
        db.add_all(
            [
                Organization(id=org_id, name="NM FORMATION", slug="nm-formation"),
                Organization(id=other_org_id, name="Autre société", slug="autre-societe"),
                UserProfile(
                    id=user_id,
                    auth_user_id=auth_user_id,
                    first_name="Nacim",
                    last_name="MESSADI",
                    email="admin@example.test",
                ),
                OrganizationMembership(
                    organization_id=org_id,
                    user_id=user_id,
                    role="admin",
                    is_active=True,
                ),
            ]
        )
        db.commit()

    settings = Settings(
        environment="local_test",
        database_url="sqlite+pysqlite:///:memory:",
        local_test_jwt_secret=TEST_SECRET,
        supabase_jwt_audience="authenticated",
        allowed_hosts=["testserver"],
    )
    app = create_app(settings)

    def override_db():
        db: Session = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: settings

    def token(subject: uuid.UUID = auth_user_id, *, expired: bool = False) -> str:
        now = datetime.now(timezone.utc)
        expires = now - timedelta(minutes=1) if expired else now + timedelta(minutes=15)
        return jwt.encode(
            {
                "sub": str(subject),
                "aud": "authenticated",
                "iat": now,
                "exp": expires,
                "email": "admin@example.test",
            },
            TEST_SECRET,
            algorithm="HS256",
        )

    with TestClient(app) as client:
        yield {
            "client": client,
            "session_factory": session_factory,
            "org_id": org_id,
            "other_org_id": other_org_id,
            "auth_user_id": auth_user_id,
            "user_id": user_id,
            "token": token,
        }


@pytest.fixture()
def auth_headers(test_context):
    return {
        "Authorization": f"Bearer {test_context['token']()}",
        "X-Organization-ID": str(test_context["org_id"]),
        "X-Device-ID": "test-device",
    }
