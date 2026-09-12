from types import SimpleNamespace

import app as app_module


def test_commercial_startup_does_not_auto_select_child_project(monkeypatch):
    user = SimpleNamespace(role="Commercial", cloud_user_id="user-florian")
    calls = []

    def fake_clear_project():
        calls.append("clear")

    class ForbiddenAPI:
        def list_projects(self, **params):
            raise AssertionError("Le demarrage ne doit plus choisir un projet enfant.")

    monkeypatch.setattr(app_module.ApplicationState, "clear_project", fake_clear_project)
    monkeypatch.setattr(app_module.CloudRuntime, "api", lambda: ForbiddenAPI())

    app_module.activate_commercial_cloud_project(user)

    assert calls == ["clear"]


def test_admin_and_manager_startup_keep_existing_workspace(monkeypatch):
    calls = []

    def fake_clear_project():
        calls.append("clear")

    monkeypatch.setattr(app_module.ApplicationState, "clear_project", fake_clear_project)

    for role in ("Administrateur", "Manager"):
        user = SimpleNamespace(role=role, cloud_user_id="user-1")
        app_module.activate_commercial_cloud_project(user)

    assert calls == []


def test_admin_and_manager_startup_keep_existing_workspace(monkeypatch):
    calls = []

    def fake_clear_project():
        calls.append("clear")

    monkeypatch.setattr(app_module.ApplicationState, "clear_project", fake_clear_project)

    for role in ("Administrateur", "Manager"):
        user = SimpleNamespace(role=role, cloud_user_id="user-1")
        app_module.activate_commercial_cloud_project(user)

    assert calls == []
