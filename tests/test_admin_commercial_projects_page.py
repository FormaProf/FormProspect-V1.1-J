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

    def assign_project_to_commercial(self, project_id, commercial_user_id):
        self.mutations.append(("assign_project_commercial", project_id, commercial_user_id))


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

class LandingAwareAdminService(FakeAdminService):
    def __init__(self, snapshot):
        super().__init__(snapshot)
        self.landing_calls = []

    def get_landing(self, project_id, commercial_user_id):
        self.landing_calls.append((project_id, commercial_user_id))
        return SimpleNamespace(
            id="link-1",
            commercial_user_id=commercial_user_id,
            project_id=project_id,
            organization_id="org-1",
            token="token-abc",
            is_active=True,
        )


def test_admin_page_displays_landing_for_selected_child_project(qapp, monkeypatch):
    monkeypatch.setattr(
        SessionState, "has_role",
        classmethod(lambda cls, *roles: "Administrateur" in roles),
    )

    snapshot = build_snapshot()
    snapshot.parents[0].projects[0].assigned_to = "user-florian"

    service = LandingAwareAdminService(snapshot)
    page = AdminCommercialProjectsPage(service=service, auto_refresh=False)
    page.rafraichir()

    page.project_table.selectRow(0)
    qapp.processEvents()

    assert service.landing_calls[-1] == ("child-1", "user-florian")
    assert page.landing_commercial_label.text() == "Florian"
    assert page.landing_status_label.text() == "Actif"
    assert page.landing_url_edit.text() == (
        "https://pilotage.forma-prof.fr/"
        "?organization_id=org-1&token=token-abc"
    )

def test_admin_page_exposes_landing_controls(qapp):
    page = AdminCommercialProjectsPage(
        service=FakeAdminService(build_snapshot()),
        auto_refresh=False,
    )

    assert page.create_landing_button.text() == "Créer le lien"
    assert page.copy_landing_button.text() == "Copier"
    assert page.open_landing_button.text() == "Ouvrir"
    assert page.toggle_landing_button.text() == "Désactiver"

def test_admin_page_displays_missing_landing_without_crashing(qapp, monkeypatch):
    monkeypatch.setattr(
        SessionState, "has_role",
        classmethod(lambda cls, *roles: "Administrateur" in roles),
    )
    snapshot = build_snapshot()
    snapshot.parents[0].projects[0].assigned_to = "user-florian"
    service = FakeAdminService(snapshot)
    service.get_landing = lambda project_id, commercial_user_id: None
    page = AdminCommercialProjectsPage(service=service, auto_refresh=False)
    page.rafraichir()
    page._project_selection_changed(0, 0, -1, -1)
    assert page.landing_commercial_label.text() == "Florian"
    assert page.landing_status_label.text() == "Aucun lien"
    assert page.landing_url_edit.text() == ""

def test_admin_page_creates_landing_for_selected_child_project(qapp, monkeypatch):
    monkeypatch.setattr(
        SessionState, "has_role",
        classmethod(lambda cls, *roles: "Administrateur" in roles),
    )
    snapshot = build_snapshot()
    snapshot.parents[0].projects[0].assigned_to = "user-florian"
    service = FakeAdminService(snapshot)
    calls = []
    service.get_landing = lambda project_id, commercial_user_id: None
    service.ensure_landing = lambda project_id, commercial_user_id: calls.append((project_id, commercial_user_id)) or SimpleNamespace(id="link-1", commercial_user_id=commercial_user_id, project_id=project_id, organization_id="org-1", token="token-new", is_active=True)
    page = AdminCommercialProjectsPage(service=service, auto_refresh=False)
    page.rafraichir()
    page.project_table.selectRow(0)
    page._on_create_landing_clicked()
    assert calls == [("child-1", "user-florian")]
    assert page.landing_status_label.text() == "Actif"
    assert page.landing_url_edit.text() == "https://pilotage.forma-prof.fr/?organization_id=org-1&token=token-new"

def test_admin_page_disables_active_landing(qapp, monkeypatch):
    monkeypatch.setattr(
        SessionState, "has_role",
        classmethod(lambda cls, *roles: "Administrateur" in roles),
    )
    snapshot = build_snapshot()
    snapshot.parents[0].projects[0].assigned_to = "user-florian"
    service = FakeAdminService(snapshot)
    calls = []
    service.get_landing = lambda project_id, commercial_user_id: SimpleNamespace(id="link-1", commercial_user_id=commercial_user_id, project_id=project_id, organization_id="org-1", token="token-abc", is_active=True)
    service.set_landing_active = lambda project_id, commercial_user_id, active: calls.append((project_id, commercial_user_id, active)) or SimpleNamespace(id="link-1", commercial_user_id=commercial_user_id, project_id=project_id, organization_id="org-1", token="token-abc", is_active=active)
    page = AdminCommercialProjectsPage(service=service, auto_refresh=False)
    page.rafraichir()
    page.project_table.selectRow(0)
    page._project_selection_changed(0, 0, -1, -1)
    page._on_toggle_landing_clicked()
    assert calls == [("child-1", "user-florian", False)]
    assert page.landing_status_label.text() == "Inactif"
    assert page.toggle_landing_button.text() == "Activer"

def test_admin_page_copies_landing_url(qapp):
    page = AdminCommercialProjectsPage(
        service=FakeAdminService(build_snapshot()),
        auto_refresh=False,
    )
    url = "https://pilotage.forma-prof.fr/?organization_id=org-1&token=token-abc"
    page.landing_url_edit.setText(url)
    page._on_copy_landing_clicked()
    assert qapp.clipboard().text() == url

def test_admin_page_opens_landing_url(qapp, monkeypatch):
    page = AdminCommercialProjectsPage(
        service=FakeAdminService(build_snapshot()),
        auto_refresh=False,
    )
    url = "https://pilotage.forma-prof.fr/?organization_id=org-1&token=token-abc"
    page.landing_url_edit.setText(url)
    calls = []
    monkeypatch.setattr(admin_page_module.QDesktopServices, "openUrl", lambda value: calls.append(value.toString()) or True)
    page._on_open_landing_clicked()
    assert calls == [url]

def test_admin_page_does_not_query_landing_until_child_is_assigned(
    qapp,
    monkeypatch,
):
    monkeypatch.setattr(
        SessionState,
        "has_role",
        classmethod(lambda cls, *roles: "Administrateur" in roles),
    )

    snapshot = build_snapshot()
    snapshot.parents[0].projects[0].assigned_to = ""

    service = LandingAwareAdminService(snapshot)
    page = AdminCommercialProjectsPage(service=service, auto_refresh=False)
    page.rafraichir()

    page.commercial_table.selectRow(0)
    page.project_table.selectRow(0)
    qapp.processEvents()

    assert service.landing_calls == []
    assert page.landing_commercial_label.text() == "Florian"
    assert page.landing_status_label.text() == "Projet à affecter au commercial"


def test_admin_page_exposes_assign_project_to_commercial_control(qapp):
    page = AdminCommercialProjectsPage(
        service=FakeAdminService(build_snapshot()),
        auto_refresh=False,
    )

    assert page.assign_project_commercial_button.text() == 'Affecter au commercial'


def test_admin_page_assigns_selected_child_project_to_selected_commercial(qapp, monkeypatch):
    monkeypatch.setattr(
        SessionState,
        "has_role",
        classmethod(lambda cls, *roles: "Administrateur" in roles),
    )

    snapshot = build_snapshot()
    snapshot.parents[0].projects[0].assigned_to = ""
    service = RecordingAdminService(snapshot)
    page = AdminCommercialProjectsPage(service=service, auto_refresh=False)
    page.rafraichir()

    page.commercial_table.selectRow(0)
    page.project_table.selectRow(0)
    qapp.processEvents()

    page.assign_project_commercial_button.click()
    qapp.processEvents()

    assert (
        "assign_project_commercial",
        "child-1",
        "user-florian",
    ) in service.mutations
