from __future__ import annotations

from types import SimpleNamespace

from services.auth_service import AuthService
from services.cloud_auth_service import CloudAuthService


def test_cloud_license_info_never_uses_local_max_users(tmp_path):
    local = AuthService(tmp_path / "accounts.db")
    assert local.license_info()["max_users"] == 10

    service = CloudAuthService(local)
    service.current_user = SimpleNamespace(id="cloud-admin")

    expected = {
        "plan": "internal",
        "plan_label": "Interne",
        "status": "active",
        "max_users": None,
        "active_users": 6,
        "remaining_users": None,
        "unlimited": True,
        "can_add_user": True,
    }
    service.api.get_json = lambda path: expected if path == "/admin/license" else None

    assert service.license_info() == expected
    assert service.license_info()["max_users"] is None
