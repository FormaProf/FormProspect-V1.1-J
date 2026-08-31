from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from services.cloud_auth_service import (
    AccountDisabledError,
    CloudAuthService,
    CloudSession,
)


class FakeResponse:
    def __init__(self, status_code: int, payload):
        self.status_code = status_code
        self.payload = payload
        self.ok = 200 <= status_code < 300

    def json(self):
        return self.payload


def test_authentication_resolves_server_membership(monkeypatch, tmp_path):
    from services.auth_service import AuthService

    responses = iter([
        FakeResponse(200, {
            "access_token": "access",
            "refresh_token": "refresh",
            "expires_in": 3600,
        }),
        FakeResponse(200, [{
            "user_id": "11111111-1111-1111-1111-111111111111",
            "organization_id": "22222222-2222-2222-2222-222222222222",
            "organization_name": "NM Formation",
            "organization_slug": "nm-formation",
            "email": "admin@example.test",
            "first_name": "Admin",
            "last_name": "Cloud",
            "role": "admin",
        }]),
        FakeResponse(200, {
            "user_id": "11111111-1111-1111-1111-111111111111",
            "organization_id": "22222222-2222-2222-2222-222222222222",
            "email": "admin@example.test",
            "role": "admin",
            "permissions": ["user:manage"],
        }),
    ])

    monkeypatch.setattr("services.cloud_auth_service.requests.post", lambda *a, **k: next(responses))
    monkeypatch.setattr("services.cloud_auth_service.requests.get", lambda *a, **k: next(responses))
    monkeypatch.setattr(CloudAuthService, "_save_refresh_token", lambda self, token: None)
    monkeypatch.setattr(CloudAuthService, "register_login_event", lambda self: None)

    service = CloudAuthService(AuthService(tmp_path / "accounts.db"))
    user = service.authenticate("ADMIN@example.test", "correct-password")

    assert user is not None
    assert user.role == "Administrateur"
    assert user.organization_name == "NM Formation"
    assert user.permissions == ("user:manage",)
    assert service.local_profiles.authenticate(user.username, "correct-password") is None


def test_disabled_membership_terminates_session(monkeypatch, tmp_path):
    from services.auth_service import AuthService

    service = CloudAuthService(AuthService(tmp_path / "accounts.db"))
    service.session = CloudSession(
        access_token="access",
        refresh_token="refresh",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    monkeypatch.setattr(
        "services.cloud_auth_service.requests.get",
        lambda *a, **k: FakeResponse(403, {"detail": "disabled"}),
    )
    monkeypatch.setattr("services.cloud_auth_service.requests.post", lambda *a, **k: FakeResponse(200, {}))
    monkeypatch.setattr(CloudAuthService, "_clear_refresh_token", lambda self: None)

    with pytest.raises(AccountDisabledError):
        service.heartbeat()
    assert service.session is None
