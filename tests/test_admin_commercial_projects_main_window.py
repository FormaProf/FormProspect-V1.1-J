from types import SimpleNamespace
from core.session import SessionState
from ui.windows.main_window import MainWindow


class FakePage:
    def __init__(self):
        self.refresh_count = 0

    def rafraichir(self):
        self.refresh_count += 1


class FakeStack:
    def __init__(self):
        self.current = None

    def setCurrentWidget(self, widget):
        self.current = widget


def test_admin_can_open_commercial_projects_page(monkeypatch):
    monkeypatch.setattr(
        SessionState, "has_role",
        classmethod(lambda cls, *roles: "Administrateur" in roles),
    )
    window = SimpleNamespace()
    window.admin_commercial_projects_page = FakePage()
    window.pages = FakeStack()

    MainWindow.ouvrir_admin_projets_commerciaux(window)

    assert window.admin_commercial_projects_page.refresh_count == 1
    assert window.pages.current is window.admin_commercial_projects_page
