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
