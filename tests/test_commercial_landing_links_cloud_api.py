from types import SimpleNamespace

from services.cloud_api_client import CloudAPIClient


def test_get_admin_commercial_landing_link_uses_admin_endpoint(monkeypatch):
    client = CloudAPIClient(auth_service=object(), base_url="https://example.test")
    calls = []
    payload = {
        "id": "link-1",
        "project_id": "project-1",
        "token": "token-1",
        "is_active": True,
    }

    def fake_get_json(path, *, params=None):
        calls.append((path, params))
        return payload

    monkeypatch.setattr(client, "get_json", fake_get_json)

    result = client.get_admin_commercial_landing_link(
        "user-florian",
        "project-1",
    )

    assert result == payload
    assert calls == [
        (
            "/commercial-landing-links/admin/user-florian",
            {"project_id": "project-1"},
        )
    ]


def test_ensure_admin_commercial_landing_link_uses_put_endpoint(monkeypatch):
    client = CloudAPIClient(auth_service=object(), base_url="https://example.test")
    calls = []
    payload = {
        "id": "link-1",
        "project_id": "project-1",
        "token": "token-1",
        "is_active": True,
    }

    def fake_request(method, path, *, params=None, json=None, expected=(200,)):
        calls.append((method, path, params, json, expected))
        return SimpleNamespace(json=lambda: payload)

    monkeypatch.setattr(client, "request", fake_request)

    result = client.ensure_admin_commercial_landing_link(
        "user-florian",
        "project-1",
    )

    assert result == payload
    assert calls == [
        (
            "PUT",
            "/commercial-landing-links/admin/user-florian",
            {"project_id": "project-1"},
            None,
            (200,),
        )
    ]


def test_set_admin_commercial_landing_link_active_uses_patch_endpoint(monkeypatch):
    client = CloudAPIClient(auth_service=object(), base_url="https://example.test")
    calls = []
    payload = {
        "id": "link-1",
        "project_id": "project-1",
        "token": "token-1",
        "is_active": False,
    }

    def fake_request(method, path, *, params=None, json=None, expected=(200,)):
        calls.append((method, path, params, json, expected))
        return SimpleNamespace(json=lambda: payload)

    monkeypatch.setattr(client, "request", fake_request)

    result = client.set_admin_commercial_landing_link_active(
        "user-florian",
        "project-1",
        False,
    )

    assert result == payload
    assert calls == [
        (
            "PATCH",
            "/commercial-landing-links/admin/user-florian/active",
            {"project_id": "project-1"},
            {"is_active": False},
            (200,),
         )
    ]
