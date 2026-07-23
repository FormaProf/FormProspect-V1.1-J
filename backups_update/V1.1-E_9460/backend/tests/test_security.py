from backend.app.models import AuditLog, OrganizationMembership, UserProfile


def test_missing_token_is_rejected(test_context):
    response = test_context["client"].get(
        "/api/v1/identity/me",
        headers={"X-Organization-ID": str(test_context["org_id"])},
    )
    assert response.status_code == 401


def test_membership_discovery_requires_token(test_context):
    assert test_context["client"].get("/api/v1/identity/memberships").status_code == 401


def test_membership_discovery_returns_only_active_tenants(test_context):
    response = test_context["client"].get(
        "/api/v1/identity/memberships",
        headers={"Authorization": f"Bearer {test_context['token']()}"},
    )
    assert response.status_code == 200
    assert response.json() == [{
        "user_id": str(test_context["user_id"]),
        "organization_id": str(test_context["org_id"]),
        "organization_name": "NM FORMATION",
        "organization_slug": "nm-formation",
        "email": "admin@example.test",
        "first_name": "Nacim",
        "last_name": "MESSADI",
        "role": "admin",
    }]


def test_expired_token_is_rejected(test_context):
    response = test_context["client"].get(
        "/api/v1/identity/me",
        headers={
            "Authorization": f"Bearer {test_context['token'](expired=True)}",
            "X-Organization-ID": str(test_context["org_id"]),
        },
    )
    assert response.status_code == 401


def test_invalid_organization_header_is_rejected(test_context):
    response = test_context["client"].get(
        "/api/v1/identity/me",
        headers={"Authorization": f"Bearer {test_context['token']()}", "X-Organization-ID": "invalid"},
    )
    assert response.status_code == 400


def test_user_cannot_enter_another_organization(test_context):
    response = test_context["client"].get(
        "/api/v1/identity/me",
        headers={
            "Authorization": f"Bearer {test_context['token']()}",
            "X-Organization-ID": str(test_context["other_org_id"]),
        },
    )
    assert response.status_code == 403


def test_disabled_membership_is_rejected(test_context, auth_headers):
    with test_context["session_factory"]() as db:
        membership = db.query(OrganizationMembership).one()
        membership.is_active = False
        db.commit()
    response = test_context["client"].get("/api/v1/identity/me", headers=auth_headers)
    assert response.status_code == 403


def test_disabled_profile_is_rejected(test_context, auth_headers):
    with test_context["session_factory"]() as db:
        profile = db.query(UserProfile).one()
        profile.status = "disabled"
        db.commit()
    response = test_context["client"].get("/api/v1/identity/me", headers=auth_headers)
    assert response.status_code == 403


def test_current_identity_exposes_server_permissions(test_context, auth_headers):
    response = test_context["client"].get("/api/v1/identity/me", headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["role"] == "admin"
    assert "user:manage" in payload["permissions"]
    assert payload["organization_id"] == str(test_context["org_id"])


def test_organization_access_creates_audit_entry(test_context, auth_headers):
    response = test_context["client"].get("/api/v1/identity/organization", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["name"] == "NM FORMATION"
    with test_context["session_factory"]() as db:
        entry = db.query(AuditLog).one()
        assert entry.action == "organization.viewed"
        assert entry.actor_user_id == test_context["user_id"]
        assert entry.organization_id == test_context["org_id"]
        assert entry.device_id == "test-device"
