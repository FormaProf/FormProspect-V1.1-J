from types import SimpleNamespace

from services.commercial_project_workspace_service import CommercialProjectWorkspaceService


class FakeAPI:
    def __init__(self):
        self.project_calls = []

    def list_commercial_projects(self):
        return [
            {"id": "parent-btp", "name": "BTP"},
            {"id": "parent-ia", "name": "IA"},
        ]

    def list_projects(self, **params):
        self.project_calls.append(params)
        items = [
            {"id": "btp-1", "name": "BTP HDF - Florian", "assigned_to": "user-florian", "commercial_project_id": "parent-btp", "prospect_count": 100},
            {"id": "btp-landing", "name": "Landing Page BTP - Florian", "assigned_to": "user-florian", "commercial_project_id": "parent-btp", "prospect_count": 20},
            {"id": "ia-1", "name": "IA HDF - Florian", "assigned_to": "user-florian", "commercial_project_id": "parent-ia", "prospect_count": 50},
            {"id": "btp-marc", "name": "BTP IDF - Marc", "assigned_to": "user-marc", "commercial_project_id": "parent-btp", "prospect_count": 999},
            {"id": "other-1", "name": "Autre projet", "assigned_to": "user-florian", "commercial_project_id": "parent-other", "prospect_count": 999},
        ]
        return SimpleNamespace(items=items, total=len(items), limit=100, offset=0)


def test_commercial_overviews_keep_btp_and_ia_separate():
    api = FakeAPI()
    service = CommercialProjectWorkspaceService(api)

    overviews = service.list_for_commercial("user-florian")

    assert [item.name for item in overviews] == ["BTP", "IA"]
    by_name = {item.name: item for item in overviews}
    assert by_name["BTP"].prospect_count == 120
    assert [project.name for project in by_name["BTP"].projects] == ["BTP HDF - Florian", "Landing Page BTP - Florian"]
    assert by_name["IA"].prospect_count == 50
    assert [project.name for project in by_name["IA"].projects] == ["IA HDF - Florian"]
    assert api.project_calls[0]["assigned_to"] == "user-florian"


def test_assigned_parent_with_no_own_children_stays_empty():
    api = FakeAPI()
    calls = []

    api.list_commercial_projects = lambda: [{"id": "parent-btp", "name": "BTP"}]

    def fake_list_projects(**params):
        calls.append(params)
        items = [
            {"id": "btp-marc", "name": "BTP IDF - Marc", "assigned_to": "user-marc", "commercial_project_id": "parent-btp", "prospect_count": 999},
        ]
        return SimpleNamespace(items=items, total=1, limit=100, offset=0)

    api.list_projects = fake_list_projects
    service = CommercialProjectWorkspaceService(api)

    overviews = service.list_for_commercial("user-florian")

    assert len(overviews) == 1
    assert overviews[0].name == "BTP"
    assert overviews[0].projects == ()
    assert overviews[0].prospect_count == 0
    assert calls[0]["assigned_to"] == "user-florian"
