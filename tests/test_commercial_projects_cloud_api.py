from services.cloud_api_client import CloudAPIClient


def test_list_commercial_projects_forwards_include_inactive(monkeypatch):
    client = CloudAPIClient(
        auth_service=object(),
        base_url="https://example.test",
    )

    calls = []
    expected = [{"id": "parent-1", "name": "BTP"}]

    def fake_get_json(path, *, params=None):
        calls.append((path, params))
        return expected

    monkeypatch.setattr(client, "get_json", fake_get_json)

    result = client.list_commercial_projects(include_inactive=True)

    assert result == expected
    assert calls == [
        ("/commercial-projects", {"include_inactive": "true"})
    ]


def test_list_commercial_projects_defaults_to_active_only(monkeypatch):
    client = CloudAPIClient(
        auth_service=object(),
        base_url="https://example.test",
    )

    calls = []

    def fake_get_json(path, *, params=None):
        calls.append((path, params))
        return []

    monkeypatch.setattr(client, "get_json", fake_get_json)

    result = client.list_commercial_projects()

    assert result == []
    assert calls == [
        ("/commercial-projects", {"include_inactive": "false"})
    ]


def test_get_commercial_project_uses_detail_endpoint(monkeypatch):
    client = CloudAPIClient(
        auth_service=object(),
        base_url="https://example.test",
    )

    calls = []
    expected = {
        "id": "parent-1",
        "name": "BTP",
        "is_active": True,
    }

    def fake_get_json(path, *, params=None):
        calls.append((path, params))
        return expected

    monkeypatch.setattr(client, "get_json", fake_get_json)

    result = client.get_commercial_project("parent-1")

    assert result == expected
    assert calls == [
        ("/commercial-projects/parent-1", None)
    ]


def test_create_commercial_project_posts_payload(monkeypatch):
    client = CloudAPIClient(auth_service=object(), base_url="https://example.test")
    calls = []
    payload = {"name": "BTP", "description": "Offre BTP"}
    expected = {"id": "parent-1", **payload, "is_active": True}
    def fake_post_json(path, body, *, expected=(200, 201)):
        calls.append((path, body, expected))
        return expected_result
    expected_result = expected
    monkeypatch.setattr(client, "post_json", fake_post_json)
    result = client.create_commercial_project(payload)
    assert result == expected
    assert calls == [("/commercial-projects", payload, (200, 201))]


def test_update_commercial_project_patches_payload(monkeypatch):
    client = CloudAPIClient(auth_service=object(), base_url="https://example.test")
    calls = []
    payload = {"name": "BTP Premium", "description": "Nouvelle description"}
    expected = {"id": "parent-1", **payload, "is_active": True}
    def fake_patch_json(path, body):
        calls.append((path, body))
        return expected
    monkeypatch.setattr(client, "patch_json", fake_patch_json)
    result = client.update_commercial_project("parent-1", payload)
    assert result == expected
    assert calls == [("/commercial-projects/parent-1", payload)]


def test_set_commercial_project_status_patches_status_endpoint(monkeypatch):
    client = CloudAPIClient(auth_service=object(), base_url="https://example.test")
    calls = []
    expected = {"id": "parent-1", "name": "BTP", "is_active": False}
    def fake_patch_json(path, body):
        calls.append((path, body))
        return expected
    monkeypatch.setattr(client, "patch_json", fake_patch_json)
    result = client.set_commercial_project_status("parent-1", False)
    assert result == expected
    assert calls == [("/commercial-projects/parent-1/status", {"is_active": False})]


def test_list_commercial_project_assignments_uses_parent_endpoint(monkeypatch):
    client = CloudAPIClient(auth_service=object(), base_url="https://example.test")
    calls = []
    expected = [{"user_id": "user-florian", "commercial_project_id": "parent-1"}]
    def fake_get_json(path, *, params=None):
        calls.append((path, params))
        return expected
    monkeypatch.setattr(client, "get_json", fake_get_json)
    result = client.list_commercial_project_assignments("parent-1")
    assert result == expected
    assert calls == [("/commercial-projects/parent-1/commercial-assignments", None)]


def test_add_commercial_project_assignment_posts_user(monkeypatch):
    client = CloudAPIClient(auth_service=object(), base_url="https://example.test")
    calls = []
    expected = {"commercial_project_id": "parent-1", "user_id": "user-florian"}
    def fake_post_json(path, payload, *, expected=(200, 201)):
        calls.append((path, payload))
        return expected_result
    expected_result = expected
    monkeypatch.setattr(client, "post_json", fake_post_json)
    result = client.add_commercial_project_assignment("parent-1", "user-florian")
    assert result == expected
    assert calls == [("/commercial-projects/parent-1/commercial-assignments", {"user_id": "user-florian"})]


def test_remove_commercial_project_assignment_uses_delete_204(monkeypatch):
    client = CloudAPIClient(auth_service=object(), base_url="https://example.test")
    calls = []
    def fake_request(method, path, *, params=None, json=None, expected=(200,)):
        calls.append((method, path, expected))
        return object()
    monkeypatch.setattr(client, "request", fake_request)
    result = client.remove_commercial_project_assignment("parent-1", "user-florian")
    assert result is None
    assert calls == [("DELETE", "/commercial-projects/parent-1/commercial-assignments/user-florian", (204,))]


def test_set_project_commercial_parent_patches_dedicated_endpoint(monkeypatch):
    client = CloudAPIClient(auth_service=object(), base_url="https://example.test")
    calls = []
    expected = {"id": "project-1", "commercial_project_id": "parent-1"}
    def fake_patch_json(path, payload):
        calls.append((path, payload))
        return expected
    monkeypatch.setattr(client, "patch_json", fake_patch_json)
    result = client.set_project_commercial_parent("project-1", "parent-1")
    assert result == expected
    assert calls == [("/projects/project-1/commercial-project", {"commercial_project_id": "parent-1"})]


def test_set_project_commercial_parent_can_detach_parent(monkeypatch):
    client = CloudAPIClient(auth_service=object(), base_url="https://example.test")
    calls = []
    expected = {"id": "project-1", "commercial_project_id": None}
    def fake_patch_json(path, payload):
        calls.append((path, payload))
        return expected
    monkeypatch.setattr(client, "patch_json", fake_patch_json)
    result = client.set_project_commercial_parent("project-1", None)
    assert result == expected
    assert calls == [("/projects/project-1/commercial-project", {"commercial_project_id": None})]
