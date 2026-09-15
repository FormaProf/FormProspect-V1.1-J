from types import SimpleNamespace

from services.commercial_project_admin_service import CommercialProjectAdminService
from services.cloud_api_client import CloudAPIError


class FakeAPI:
    def __init__(self):
        self.calls = []
        self.parents = [
            {"id": "parent-btp", "name": "BTP", "description": "Offre BTP", "is_active": True},
            {"id": "parent-ia", "name": "IA", "description": "", "is_active": False},
        ]
        self.users = [
            SimpleNamespace(id="user-florian", role="commercial", full_name="Florian", email="florian@test.fr", is_active=True),
            SimpleNamespace(id="user-aziz", role="commercial", full_name="Aziz", email="aziz@test.fr", is_active=False),
            SimpleNamespace(id="user-manager", role="manager", full_name="Manager", email="manager@test.fr", is_active=True),
        ]
        self.projects = SimpleNamespace(
            items=[
                {"id": "child-1", "name": "BTP Nord", "status": "ready", "commercial_project_id": "parent-btp", "assigned_to": "user-florian"},
                {"id": "child-free", "name": "Projet libre", "status": "preparation", "commercial_project_id": None},
            ],
            total=2,
        )

    def list_commercial_projects(self, *, include_inactive=False):
        self.calls.append(("parents", include_inactive))
        return self.parents

    def list_users(self, *, active_only=True):
        self.calls.append(("users", active_only))
        return self.users

    def list_projects(self, **params):
        self.calls.append(("projects", params))
        return self.projects

    def list_commercial_project_assignments(self, parent_id):
        if parent_id == "parent-btp":
            return [{"user_id": "user-florian"}]
        if parent_id == "parent-ia":
            return [{"user_id": "user-aziz"}]
        return []

    def create_commercial_project(self, payload):
        self.calls.append(("create", payload))
        return payload

    def update_commercial_project(self, parent_id, payload):
        self.calls.append(("update", parent_id, payload))
        return payload

    def set_commercial_project_status(self, parent_id, active):
        self.calls.append(("status", parent_id, active))
        return {"id": parent_id, "is_active": active}

    def add_commercial_project_assignment(self, parent_id, user_id):
        self.calls.append(("assign", parent_id, user_id))

    def remove_commercial_project_assignment(self, parent_id, user_id):
        self.calls.append(("unassign", parent_id, user_id))

    def set_project_commercial_parent(self, project_id, parent_id):
        self.calls.append(("attach", project_id, parent_id))


def test_admin_snapshot_groups_parents_commercials_and_child_projects():
    api = FakeAPI()
    snapshot = CommercialProjectAdminService(api).load()

    assert [item.name for item in snapshot.parents] == ["BTP", "IA"]
    assert snapshot.parents[0].assigned_commercials[0].name == "Florian"
    assert snapshot.parents[0].projects[0].name == "BTP Nord"
    assert [item.name for item in snapshot.commercials] == ["Florian", "Aziz"]
    assert [item.name for item in snapshot.ungrouped_projects] == ["Projet libre"]
    assert ("parents", True) in api.calls
    assert ("users", False) in api.calls


def test_admin_mutations_delegate_to_existing_cloud_api():
    api = FakeAPI()
    service = CommercialProjectAdminService(api)

    service.create_parent(" BTP ", " Offre BTP ")
    service.update_parent("parent-btp", " BTP Premium ", " Nouvelle offre ")
    service.set_parent_active("parent-btp", False)
    service.assign_commercial("parent-btp", "user-florian")
    service.remove_commercial("parent-btp", "user-florian")
    service.attach_project("parent-btp", "child-1")
    service.detach_project("child-1")

    assert ("create", {"name": "BTP", "description": "Offre BTP"}) in api.calls
    assert ("update", "parent-btp", {"name": "BTP Premium", "description": "Nouvelle offre"}) in api.calls
    assert ("status", "parent-btp", False) in api.calls
    assert ("assign", "parent-btp", "user-florian") in api.calls
    assert ("unassign", "parent-btp", "user-florian") in api.calls
    assert ("attach", "child-1", "parent-btp") in api.calls
    assert ("attach", "child-1", None) in api.calls


def test_admin_child_project_keeps_primary_commercial_assignment():
    snapshot = CommercialProjectAdminService(FakeAPI()).load()

    child = snapshot.parents[0].projects[0]
    assert child.assigned_to == "user-florian"


def test_admin_service_gets_landing_for_child_project():
    api = FakeAPI()
    api.get_admin_commercial_landing_link = lambda user_id, project_id: {
        "id": "link-1",
        "organization_id": "org-1",
        "project_id": project_id,
        "token": "token-abc",
        "is_active": True,
    }
    result = CommercialProjectAdminService(api).get_landing("child-1", "user-florian")
    assert result.id == "link-1"
    assert result.project_id == "child-1"
    assert result.commercial_user_id == "user-florian"
    assert result.is_active is True

def test_admin_service_ensures_landing_for_child_project():
    api = FakeAPI()
    calls = []
    api.ensure_admin_commercial_landing_link = lambda user_id, project_id: calls.append((user_id, project_id)) or {"id": "link-1", "organization_id": "org-1", "project_id": project_id, "token": "token-abc", "is_active": True}
    result = CommercialProjectAdminService(api).ensure_landing("child-1", "user-florian")
    assert calls == [("user-florian", "child-1")]
    assert result.token == "token-abc"

def test_admin_service_sets_landing_active_for_child_project():
    api = FakeAPI()
    calls = []
    api.set_admin_commercial_landing_link_active = lambda user_id, project_id, active: calls.append((user_id, project_id, active)) or {"id": "link-1", "organization_id": "org-1", "project_id": project_id, "token": "token-abc", "is_active": active}
    result = CommercialProjectAdminService(api).set_landing_active("child-1", "user-florian", False)
    assert calls == [("user-florian", "child-1", False)]
    assert result.is_active is False

def test_admin_service_returns_none_when_landing_is_missing():
    api = FakeAPI()
    def missing_landing(user_id, project_id):
        raise CloudAPIError("Aucun lien", status_code=404)
    api.get_admin_commercial_landing_link = missing_landing
    result = CommercialProjectAdminService(api).get_landing("child-1", "user-florian")
    assert result is None
