import pytest
from PySide6.QtWidgets import QApplication

@pytest.fixture
def qapp():
    return QApplication.instance() or QApplication([])

from types import SimpleNamespace

from core.session import SessionState
import ui.pages.admin_commercial_projects_page as admin_page_module
from ui.pages.admin_commercial_projects_page import AdminCommercialProjectsPage


class FakeAdminService:
    def __init__(self, snapshot):
        self.snapshot = snapshot
        self.calls = 0

    def load(self):
        self.calls += 1
        return self.snapshot


def build_snapshot():
    commercial = SimpleNamespace(
        id="user-florian", name="Florian",
        email="florian@test.fr", is_active=True,
    )
    child = SimpleNamespace(
        id="child-1", name="BTP Nord",
        status="ready", commercial_project_id="parent-btp",
    )
    parent = SimpleNamespace(
        id="parent-btp", name="BTP",
        description="Offre BTP", is_active=True,
        assigned_commercials=(commercial,), projects=(child,),
    )
    free_project = SimpleNamespace(
        id="child-free", name="Projet libre",
        status="preparation", commercial_project_id=None,
    )
    return SimpleNamespace(
        parents=(parent,),
        commercials=(commercial,),
        ungrouped_projects=(free_project,),
    )


def test_admin_page_displays_commercial_project_hierarchy(qapp, monkeypatch):
    monkeypatch.setattr(
        SessionState, "has_role",
        classmethod(lambda cls, *roles: "Administrateur" in roles),
    )
    service = FakeAdminService(build_snapshot())
    page = AdminCommercialProjectsPage(service=service, auto_refresh=False)
    page.rafraichir()

    assert service.calls == 1
    assert page.parent_table.rowCount() == 1
    assert page.parent_table.item(0, 0).text() == "BTP"
    assert page.parent_table.item(0, 2).text() == "Actif"
    assert page.commercial_table.rowCount() == 1
    assert page.commercial_table.item(0, 0).text() == "Florian"
    assert page.project_table.rowCount() == 1
    assert page.project_table.item(0, 0).text() == "BTP Nord"
    assert page.available_project_count.text() == "1 projet disponible"



class RecordingAdminService(FakeAdminService):
    def __init__(self, snapshot):
        super().__init__(snapshot)
        self.mutations = []

    def create_parent(self, name, description):
        self.mutations.append(("create", name, description))

    def update_parent(self, parent_id, name, description):
        self.mutations.append(("update", parent_id, name, description))

    def set_parent_active(self, parent_id, is_active):
        self.mutations.append(("status", parent_id, is_active))

    def assign_commercial(self, parent_id, user_id):
        self.mutations.append(("assign", parent_id, user_id))

    def remove_commercial(self, parent_id, user_id):
        self.mutations.append(("remove", parent_id, user_id))

    def attach_project(self, parent_id, project_id):
        self.mutations.append(("attach", parent_id, project_id))

    def detach_project(self, project_id):
        self.mutations.append(("detach", project_id))


def test_admin_page_mutation_actions_delegate_and_refresh(qapp, monkeypatch):
    monkeypatch.setattr(
        SessionState, "has_role",
        classmethod(lambda cls, *roles: "Administrateur" in roles),
    )
    service = RecordingAdminService(build_snapshot())
    page = AdminCommercialProjectsPage(service=service, auto_refresh=False)
    page.rafraichir()

    page._create_parent("IA", "Offre IA")
    page._update_parent("parent-btp", "BTP Premium", "Pilotage")
    page._set_parent_active("parent-btp", False)
    page._assign_commercial("parent-btp", "user-florian")
    page._remove_commercial("parent-btp", "user-florian")
    page._attach_project("parent-btp", "child-free")
    page._detach_project("child-1")

    assert service.mutations == [
        ("create", "IA", "Offre IA"),
        ("update", "parent-btp", "BTP Premium", "Pilotage"),
        ("status", "parent-btp", False),
        ("assign", "parent-btp", "user-florian"),
        ("remove", "parent-btp", "user-florian"),
        ("attach", "parent-btp", "child-free"),
        ("detach", "child-1"),
    ]
    assert service.calls > 1


def test_admin_page_exposes_parent_management_controls(qapp):
    page = AdminCommercialProjectsPage(
        service=FakeAdminService(build_snapshot()),
        auto_refresh=False,
    )

    assert page.create_parent_button.text() == "Nouveau projet"
    assert page.edit_parent_button.text() == "Modifier"
    assert page.toggle_parent_button.text() == "Désactiver"


def test_admin_page_toggle_selected_parent(qapp, monkeypatch):
    monkeypatch.setattr(
        SessionState, "has_role",
        classmethod(lambda cls, *roles: "Administrateur" in roles),
    )
    service = RecordingAdminService(build_snapshot())
    page = AdminCommercialProjectsPage(service=service, auto_refresh=False)
    page.rafraichir()

    page._on_toggle_parent_clicked()

    assert ("status", "parent-btp", False) in service.mutations



class FakeParentProjectDialog:
    def __init__(self, parent=None, *, name="", description=""):
        self.name = name

    def exec(self):
        return True

    def values(self):
        if self.name:
            return "BTP Premium", "Pilotage"
        return "IA", "Offre IA"


def test_admin_page_create_and_edit_parent_from_dialog(qapp, monkeypatch):
    monkeypatch.setattr(
        SessionState, "has_role",
        classmethod(lambda cls, *roles: "Administrateur" in roles),
    )
    monkeypatch.setattr(
        admin_page_module, "ParentProjectDialog",
        FakeParentProjectDialog, raising=False,
    )
    service = RecordingAdminService(build_snapshot())
    page = AdminCommercialProjectsPage(service=service, auto_refresh=False)
    page.rafraichir()

    page._on_create_parent_clicked()
    page._on_edit_parent_clicked()

    assert ("create", "IA", "Offre IA") in service.mutations
    assert (
        "update", "parent-btp", "BTP Premium", "Pilotage"
    ) in service.mutations


def test_admin_page_exposes_commercial_assignment_controls(qapp):
    page = AdminCommercialProjectsPage(
        service=FakeAdminService(build_snapshot()),
        auto_refresh=False,
    )

    assert page.add_commercial_button.text() == "Affecter un commercial"
    assert page.remove_commercial_button.text() == "Retirer"


class FakeCommercialAssignmentDialog:
    def __init__(self, parent=None, *, commercials=()):
        self.commercials = commercials

    def exec(self):
        return True

    def selected_user_id(self):
        return "user-elise"


def test_admin_page_assigns_and_removes_commercial(qapp, monkeypatch):
    monkeypatch.setattr(
        SessionState, "has_role",
        classmethod(lambda cls, *roles: "Administrateur" in roles),
    )
    monkeypatch.setattr(
        admin_page_module, "CommercialAssignmentDialog",
        FakeCommercialAssignmentDialog, raising=False,
    )

    snapshot = build_snapshot()
    elise = SimpleNamespace(
        id="user-elise", name="Elise",
        email="elise@test.fr", is_active=True,
    )
    snapshot.commercials = snapshot.commercials + (elise,)
    service = RecordingAdminService(snapshot)
    page = AdminCommercialProjectsPage(service=service, auto_refresh=False)
    page.rafraichir()

    page._on_add_commercial_clicked()
    page.commercial_table.selectRow(0)
    page._on_remove_commercial_clicked()

    assert ("assign", "parent-btp", "user-elise") in service.mutations
    assert ("remove", "parent-btp", "user-florian") in service.mutations


def test_admin_page_exposes_child_project_controls(qapp):
    page = AdminCommercialProjectsPage(
        service=FakeAdminService(build_snapshot()),
        auto_refresh=False,
    )

    assert page.attach_project_button.text() == "Rattacher un projet"
    assert page.detach_project_button.text() == "Détacher"


class FakeChildProjectDialog:
    def __init__(self, parent=None, *, projects=()):
        self.projects = projects

    def exec(self):
        return True

    def selected_project_id(self):
        return "child-free"


def test_admin_page_attaches_and_detaches_child_project(qapp, monkeypatch):
    monkeypatch.setattr(
        SessionState, "has_role",
        classmethod(lambda cls, *roles: "Administrateur" in roles),
    )
    monkeypatch.setattr(
        admin_page_module, "ChildProjectDialog",
        FakeChildProjectDialog, raising=False,
    )
    service = RecordingAdminService(build_snapshot())
    page = AdminCommercialProjectsPage(service=service, auto_refresh=False)
    page.rafraichir()

    page._on_attach_project_clicked()
    page.project_table.selectRow(0)
    page._on_detach_project_clicked()

    assert ("attach", "parent-btp", "child-free") in service.mutations
    assert ("detach", "child-1") in service.mutations
