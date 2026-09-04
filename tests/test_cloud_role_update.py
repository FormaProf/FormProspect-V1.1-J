from __future__ import annotations

from types import SimpleNamespace

from services.auth_service import AuthService
from services.cloud_auth_service import CloudAuthService


def test_cloud_set_role_uses_secure_admin_endpoint(tmp_path):
    service = CloudAuthService(AuthService(tmp_path / "accounts.db"))
    service.current_user = SimpleNamespace(id="cloud-admin")

    captured = {}

    def fake_patch(path, payload):
        captured["path"] = path
        captured["payload"] = payload
        return {"id": "membership-123", "role": "manager", "active": True}

    service.api.patch_json = fake_patch

    result = service.set_role("membership-123", "Manager")

    assert captured == {
        "path": "/admin/users/membership-123",
        "payload": {"role": "manager"},
    }
    assert result["role"] == "manager"


def test_cloud_list_users_exposes_manual_prospect_permission(tmp_path):
    service = CloudAuthService(AuthService(tmp_path / "accounts.db"))
    service.current_user = SimpleNamespace(id="cloud-admin")

    service.api.get_json = lambda path: [
        {
            "id": "membership-123",
            "user_id": "user-123",
            "email": "commercial@example.test",
            "first_name": "Florian",
            "last_name": "TEST",
            "role": "commercial",
            "active": True,
            "can_create_prospect_manually": True,
        }
    ]

    users = service.list_users()

    assert len(users) == 1
    assert users[0]["id"] == "membership-123"
    assert users[0]["role"] == "Commercial"
    assert users[0]["can_create_prospect_manually"] is True


def test_cloud_list_users_defaults_manual_prospect_permission_to_false(
    tmp_path,
):
    service = CloudAuthService(AuthService(tmp_path / "accounts.db"))
    service.current_user = SimpleNamespace(id="cloud-admin")

    service.api.get_json = lambda path: [
        {
            "id": "membership-123",
            "user_id": "user-123",
            "email": "commercial@example.test",
            "role": "commercial",
            "active": True,
        }
    ]

    users = service.list_users()

    assert users[0]["can_create_prospect_manually"] is False


def test_cloud_set_manual_prospect_permission_uses_secure_admin_endpoint(
    tmp_path,
):
    service = CloudAuthService(AuthService(tmp_path / "accounts.db"))
    service.current_user = SimpleNamespace(id="cloud-admin")

    captured = {}

    def fake_patch(path, payload):
        captured["path"] = path
        captured["payload"] = payload
        return {
            "id": "membership-123",
            "role": "commercial",
            "active": True,
            "can_create_prospect_manually": True,
        }

    service.api.patch_json = fake_patch

    result = service.set_manual_prospect_creation_permission(
        "membership-123",
        True,
    )

    assert captured == {
        "path": "/admin/users/membership-123",
        "payload": {
            "can_create_prospect_manually": True,
        },
    }
    assert result["can_create_prospect_manually"] is True
