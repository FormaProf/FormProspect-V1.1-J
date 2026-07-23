from __future__ import annotations

import uuid

from backend.app.models import AuditLog
from backend.app.services.supabase_admin_service import get_supabase_admin


class FakeSupabaseAdmin:
    def __init__(self):
        self.invited_id = uuid.uuid4()
        self.reset_emails = []
        self.deleted = []

    def invite_user(self, email, first_name, last_name):
        return self.invited_id

    def delete_user(self, auth_user_id):
        self.deleted.append(auth_user_id)

    def send_password_reset(self, email):
        self.reset_emails.append(email)


def test_admin_user_lifecycle_and_audit(test_context, auth_headers):
    fake = FakeSupabaseAdmin()
    test_context["client"].app.dependency_overrides[get_supabase_admin] = lambda: fake

    listed = test_context["client"].get("/api/v1/admin/users", headers=auth_headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    admin_membership_id = listed.json()[0]["id"]

    protected = test_context["client"].patch(
        f"/api/v1/admin/users/{admin_membership_id}", headers=auth_headers, json={"active": False}
    )
    assert protected.status_code == 409

    created = test_context["client"].post(
        "/api/v1/admin/users", headers=auth_headers,
        json={"email": "commercial@example.com", "first_name": "Camille", "last_name": "Test", "role": "commercial"},
    )
    assert created.status_code == 201, created.text
    user = created.json()
    assert user["active"] is True
    assert user["role"] == "commercial"

    updated = test_context["client"].patch(
        f"/api/v1/admin/users/{user['id']}", headers=auth_headers, json={"role": "manager", "active": False}
    )
    assert updated.status_code == 200
    assert updated.json()["role"] == "manager"
    assert updated.json()["active"] is False

    reset = test_context["client"].post(
        f"/api/v1/admin/users/{user['id']}/password-reset", headers=auth_headers
    )
    assert reset.status_code == 204
    assert fake.reset_emails == ["commercial@example.com"]

    audit = test_context["client"].get("/api/v1/admin/audit", headers=auth_headers)
    assert audit.status_code == 200
    actions = {entry["action"] for entry in audit.json()}
    assert {"user.invited", "user.updated", "user.password_reset_requested"} <= actions
    with test_context["session_factory"]() as db:
        assert db.query(AuditLog).count() == 3
