from core.application_state import ApplicationState
from services.cloud_runtime import CloudRuntime
from ui.windows.main_window import MainWindow

class FakeAPI:
    def get_project(self, project_id):
        assert project_id == "btp-1"
        return {
            "id": "btp-1",
            "name": "BTP HDF - Florian",
            "assigned_to": "user-florian",
            "commercial_project_id": "parent-btp",
        }


class FakeWindow:
    def __init__(self):
        self.dashboard_opened = 0

    def ouvrir_dashboard(self):
        self.dashboard_opened += 1


def test_commercial_child_activation_sets_cloud_workspace_and_opens_dashboard(monkeypatch):
    api = FakeAPI()
    monkeypatch.setattr(CloudRuntime, "api", lambda: api)
    ApplicationState.clear_project()
    window = FakeWindow()

    MainWindow._ouvrir_projet_commercial_enfant(window, "btp-1")

    project = ApplicationState.get_cloud_project()
    assert project is not None
    assert project.id == "btp-1"
    assert project.name == "BTP HDF - Florian"
    assert window.dashboard_opened == 1
    ApplicationState.clear_project()


class FakeCommercialProjectsPage:
    def __init__(self):
        self.refresh_count = 0

    def rafraichir(self):
        self.refresh_count += 1

class FakePages:
    def __init__(self):
        self.current = None

    def setCurrentWidget(self, widget):
        self.current = widget


def test_open_commercial_projects_refreshes_and_displays_page():
    window = FakeWindow()
    window.commercial_projects_page = FakeCommercialProjectsPage()
    window.pages = FakePages()

    MainWindow.ouvrir_projets_commerciaux(window)

    assert window.commercial_projects_page.refresh_count == 1
    assert window.pages.current is window.commercial_projects_page


class FakeCommercialWorkspaceService:
    def __init__(self, decision):
        self.decision = decision
        self.received_user_id = None

    def list_for_commercial(self, user_id):
        self.received_user_id = user_id
        return ["parent"]

    def resolve_initial_navigation(self, parents):
        assert parents == ["parent"]
        return self.decision


def test_commercial_startup_opens_single_child_directly():
    from types import SimpleNamespace
    window = FakeWindow()
    window.commercial_user_id = "user-florian"
    service = FakeCommercialWorkspaceService(
        SimpleNamespace(mode="open_project", project_id="btp-1")
    )
    window.commercial_project_workspace_service = service
    opened = []
    window._ouvrir_projet_commercial_enfant = opened.append
    window.ouvrir_projets_commerciaux = lambda: opened.append("selector")

    MainWindow._initialiser_navigation_commerciale(window)

    assert service.received_user_id == "user-florian"
    assert opened == ["btp-1"]


def test_commercial_startup_shows_selector_when_choice_is_required():
    from types import SimpleNamespace
    window = FakeWindow()
    window.commercial_user_id = "user-florian"
    service = FakeCommercialWorkspaceService(
        SimpleNamespace(mode="show_parents", project_id=None)
    )
    window.commercial_project_workspace_service = service
    opened = []
    window._ouvrir_projet_commercial_enfant = opened.append
    window.ouvrir_projets_commerciaux = lambda: opened.append("selector")

    MainWindow._initialiser_navigation_commerciale(window)

    assert opened == ["selector"]


class FakeStatusBar:
    def __init__(self):
        self.message = ""

    def showMessage(self, message):
        self.message = message


def test_status_bar_displays_active_cloud_project(monkeypatch):
    from types import SimpleNamespace
    from core.session import SessionState

    ApplicationState.clear_project()
    ApplicationState.set_cloud_project({"id": "btp-1", "name": "BTP HDF - Florian"})

    monkeypatch.setattr(SessionState, "user", lambda: SimpleNamespace(display_name="Florian", role="Commercial"))
    monkeypatch.setattr(SessionState, "has_role", lambda *roles: False)

    window = FakeWindow()
    status = FakeStatusBar()
    window.statusBar = lambda: status

    MainWindow.mettre_a_jour_barre_statut(window)

    assert "BTP HDF - Florian" in status.message
    ApplicationState.clear_project()
