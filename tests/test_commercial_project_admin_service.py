from types import SimpleNamespace

from services.commercial_project_admin_service import CommercialProjectAdminService


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
                {"id": "child-1", "name": "BTP Nord", "status": "ready", "commercial_project_id": "parent-btp"},
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
