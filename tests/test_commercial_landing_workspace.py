from services.cloud_api_client import CloudAPIClient, CloudAPIError
from services.commercial_project_workspace_service import CommercialProjectWorkspaceService


def test_api_get_my_commercial_landing_uses_me_endpoint(monkeypatch):
    client = CloudAPIClient(
        auth_service=object(),
        base_url="https://example.test",
    )
    calls = []
    expected = {
        "id": "landing-1",
        "project_id": "project-1",
        "organization_id": "org-1",
        "token": "token-1",
        "is_active": True,
    }

    def fake_get_json(path, *, params=None):
        calls.append((path, params))
        return expected

    monkeypatch.setattr(client, "get_json", fake_get_json)

    result = client.get_my_commercial_landing_link("project-1")

    assert result == expected
    assert calls == [
        ("/commercial-landing-links/me", {"project_id": "project-1"})
    ]


def test_api_ensure_my_commercial_landing_uses_put_me_endpoint(monkeypatch):
    client = CloudAPIClient(
        auth_service=object(),
        base_url="https://example.test",
    )
    calls = []
    expected = {
        "id": "landing-1",
        "project_id": "project-1",
        "organization_id": "org-1",
        "token": "token-1",
        "is_active": True,
    }

    class FakeResponse:
        def json(self):
            return expected

    def fake_request(method, path, *, params=None, json=None, expected=(200,)):
        calls.append((method, path, params, json))
        return FakeResponse()

    monkeypatch.setattr(client, "request", fake_request)

    result = client.ensure_my_commercial_landing_link("project-1")

    assert result == expected
    assert calls == [
        ("PUT", "/commercial-landing-links/me", {"project_id": "project-1"}, None)
    ]


def test_api_set_my_commercial_landing_active_uses_patch_me_endpoint(monkeypatch):
    client = CloudAPIClient(
        auth_service=object(),
        base_url="https://example.test",
    )
    calls = []
    expected = {
        "id": "landing-1",
        "project_id": "project-1",
        "organization_id": "org-1",
        "token": "token-1",
        "is_active": False,
    }

    class FakeResponse:
        def json(self):
            return expected

    def fake_request(method, path, *, params=None, json=None, expected=(200,)):
        calls.append((method, path, params, json))
        return FakeResponse()

    monkeypatch.setattr(client, "request", fake_request)

    result = client.set_my_commercial_landing_link_active(
        "project-1",
        False,
    )

    assert result == expected
    assert calls == [
        (
            "PATCH",
            "/commercial-landing-links/me/active",
            {"project_id": "project-1"},
            {"is_active": False},
        )
    ]


def test_api_lists_my_landing_projects_from_me_endpoint(monkeypatch):
    client = CloudAPIClient(
        auth_service=object(),
        base_url="https://example.test",
    )
    calls = []
    expected = [
        {"id": "project-1", "name": "BTP HDF"},
        {"id": "project-2", "name": "BTP IDF"},
    ]

    def fake_get_json(path, *, params=None):
        calls.append((path, params))
        return expected

    monkeypatch.setattr(client, "get_json", fake_get_json)

    result = client.list_my_commercial_landing_projects()

    assert result == expected
    assert calls == [
        ("/commercial-landing-links/me/projects", None)
    ]


class FakeLandingAPI:
    def __init__(self):
        self.calls = []

    @staticmethod
    def _payload(active=True):
        return {
            "id": "landing-1",
            "project_id": "project-1",
            "organization_id": "org-1",
            "token": "token-1",
            "is_active": active,
        }

    def get_my_commercial_landing_link(self, project_id):
        self.calls.append(("get", project_id))
        return self._payload()

    def ensure_my_commercial_landing_link(self, project_id):
        self.calls.append(("ensure", project_id))
        return self._payload()

    def set_my_commercial_landing_link_active(self, project_id, active):
        self.calls.append(("active", project_id, active))
        return self._payload(active=active)


def test_workspace_get_landing_maps_current_commercial_payload():
    api = FakeLandingAPI()
    service = CommercialProjectWorkspaceService(api)

    landing = service.get_landing(" project-1 ")

    assert landing.id == "landing-1"
    assert landing.project_id == "project-1"
    assert landing.organization_id == "org-1"
    assert landing.token == "token-1"
    assert landing.is_active is True
    assert api.calls == [("get", "project-1")]


def test_workspace_ensure_landing_uses_current_commercial_only():
    api = FakeLandingAPI()
    service = CommercialProjectWorkspaceService(api)

    landing = service.ensure_landing(" project-1 ")

    assert landing.project_id == "project-1"
    assert landing.is_active is True
    assert api.calls == [("ensure", "project-1")]


def test_workspace_set_landing_active_uses_current_commercial_only():
    api = FakeLandingAPI()
    service = CommercialProjectWorkspaceService(api)

    landing = service.set_landing_active(" project-1 ", False)

    assert landing.project_id == "project-1"
    assert landing.is_active is False
    assert api.calls == [("active", "project-1", False)]


def test_workspace_get_landing_returns_none_when_link_does_not_exist():
    class MissingLandingAPI:
        def get_my_commercial_landing_link(self, project_id):
            raise CloudAPIError("Landing introuvable.", status_code=404)

    service = CommercialProjectWorkspaceService(MissingLandingAPI())

    assert service.get_landing("project-1") is None
