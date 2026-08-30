from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import sys
import types

import pytest


ROOT = Path(__file__).resolve().parents[1]
SERVICES = ROOT / "services"


@dataclass
class FakeSession:
    access_token: str = "old-access"
    refresh_token: str = "refresh-token"
    expires_at: datetime = datetime.now(timezone.utc) + timedelta(hours=1)
    organization_id: str = "org-123"


class FakeResponse:
    def __init__(self, status_code: int, payload=None, text: str = ""):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text
        self.ok = 200 <= status_code < 300

    def json(self):
        return self._payload


class FakeAuth:
    def __init__(self):
        self.session = FakeSession()
        self.ensure_calls = 0
        self.refresh_calls = 0

    def ensure_session_fresh(self, *, margin_seconds=120):
        self.ensure_calls += 1

    def refresh_session(self):
        self.refresh_calls += 1
        self.session.access_token = "new-access"


def _load_api_module():
    models_pkg = sys.modules.setdefault("models", types.ModuleType("models"))
    cloud_user = types.ModuleType("models.cloud_user")
    cloud_user.CloudUser = type("CloudUser", (), {})
    cloud_user.CloudUserDataError = type("CloudUserDataError", (ValueError,), {})
    sys.modules["models.cloud_user"] = cloud_user
    setattr(models_pkg, "cloud_user", cloud_user)

    spec = importlib.util.spec_from_file_location(
        "session_refresh_cloud_api_client", SERVICES / "cloud_api_client.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_valid_request_does_not_force_refresh():
    module = _load_api_module()
    auth = FakeAuth()
    client = module.CloudAPIClient(auth, "https://example.test/api/v1")
    calls = []

    def fake_request(method, url, **kwargs):
        calls.append(kwargs["headers"]["Authorization"])
        return FakeResponse(200, {"ok": True})

    client.http.request = fake_request
    response = client.request("GET", "/x")

    assert response.status_code == 200
    assert auth.ensure_calls == 1
    assert auth.refresh_calls == 0
    assert calls == ["Bearer old-access"]


def test_401_refreshes_once_and_retries_with_new_token():
    module = _load_api_module()
    auth = FakeAuth()
    client = module.CloudAPIClient(auth, "https://example.test/api/v1")
    calls = []

    def fake_request(method, url, **kwargs):
        calls.append(kwargs["headers"]["Authorization"])
        if len(calls) == 1:
            return FakeResponse(401, {"detail": "expired"})
        return FakeResponse(200, {"ok": True})

    client.http.request = fake_request
    response = client.request("GET", "/x")

    assert response.status_code == 200
    assert auth.refresh_calls == 1
    assert calls == ["Bearer old-access", "Bearer new-access"]


def test_second_401_is_not_retried_forever():
    module = _load_api_module()
    auth = FakeAuth()
    client = module.CloudAPIClient(auth, "https://example.test/api/v1")
    calls = []

    def fake_request(method, url, **kwargs):
        calls.append(kwargs["headers"]["Authorization"])
        return FakeResponse(401, {"detail": "still unauthorized"})

    client.http.request = fake_request

    with pytest.raises(module.CloudAPIError) as exc:
        client.request("GET", "/x")

    assert exc.value.status_code == 401
    assert auth.refresh_calls == 1
    assert len(calls) == 2


def test_refresh_failure_returns_session_error_without_retrying_request():
    module = _load_api_module()

    class BrokenAuth(FakeAuth):
        def refresh_session(self):
            self.refresh_calls += 1
            raise RuntimeError("refresh rejected")

    auth = BrokenAuth()
    client = module.CloudAPIClient(auth, "https://example.test/api/v1")
    calls = []

    def fake_request(method, url, **kwargs):
        calls.append(1)
        return FakeResponse(401, {"detail": "expired"})

    client.http.request = fake_request

    with pytest.raises(module.CloudAPIError) as exc:
        client.request("GET", "/x")

    assert exc.value.status_code == 401
    assert auth.refresh_calls == 1
    assert len(calls) == 1


def test_multipart_reopens_file_and_retries_once(tmp_path):
    module = _load_api_module()
    auth = FakeAuth()
    client = module.CloudAPIClient(auth, "https://example.test/api/v1")
    source = tmp_path / "doc.txt"
    source.write_text("hello", encoding="utf-8")
    bodies = []

    def fake_request(method, url, **kwargs):
        handle = kwargs["files"]["file"][1]
        bodies.append(handle.read())
        if len(bodies) == 1:
            return FakeResponse(401, {"detail": "expired"})
        return FakeResponse(201, {"id": "doc-1"})

    client.http.request = fake_request
    result = client._multipart_json(
        "POST", "/documents", data={"x": "1"}, file_path=source, expected=(201,)
    )

    assert result == {"id": "doc-1"}
    assert auth.refresh_calls == 1
    assert bodies == [b"hello", b"hello"]

def _load_auth_module():
    # Minimal stubs for imports not present in the focused audit bundle.
    core_pkg = sys.modules.setdefault("core", types.ModuleType("core"))
    core_session = types.ModuleType("core.session")
    core_session.AuthenticatedUser = type("AuthenticatedUser", (), {})
    sys.modules["core.session"] = core_session
    setattr(core_pkg, "session", core_session)

    services_pkg = sys.modules.setdefault("services", types.ModuleType("services"))
    auth_mod = types.ModuleType("services.auth_service")
    auth_mod.AuthService = type("AuthService", (), {})
    sys.modules["services.auth_service"] = auth_mod
    setattr(services_pkg, "auth_service", auth_mod)

    api_module = _load_api_module()
    sys.modules["services.cloud_api_client"] = api_module
    setattr(services_pkg, "cloud_api_client", api_module)

    spec = importlib.util.spec_from_file_location(
        "session_refresh_cloud_auth_service", SERVICES / "cloud_auth_service.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_accepting_refreshed_token_preserves_organization(monkeypatch):
    module = _load_auth_module()
    service = object.__new__(module.CloudAuthService)
    service.session = module.CloudSession(
        access_token="old",
        refresh_token="refresh-old",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        organization_id="org-keep",
    )
    service.current_user = None
    service._clear_refresh_token = lambda: None
    service._save_refresh_token = lambda token: None

    service._accept_token_payload(
        {
            "access_token": "new",
            "refresh_token": "refresh-new",
            "expires_in": 3600,
        },
        remember_session=False,
    )

    assert service.session.access_token == "new"
    assert service.session.refresh_token == "refresh-new"
    assert service.session.organization_id == "org-keep"


def test_ensure_session_fresh_refreshes_only_near_expiry():
    module = _load_auth_module()
    service = object.__new__(module.CloudAuthService)
    service.current_user = None
    calls = []
    service.refresh_session = lambda: calls.append("refresh")

    service.session = module.CloudSession(
        access_token="a",
        refresh_token="r",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        organization_id="org",
    )
    service.ensure_session_fresh(margin_seconds=120)
    assert calls == []

    service.session.expires_at = datetime.now(timezone.utc) + timedelta(seconds=30)
    service.ensure_session_fresh(margin_seconds=120)
    assert calls == ["refresh"]
