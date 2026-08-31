from __future__ import annotations

from datetime import date, timedelta

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

TRAINER_TEST_START = (date.today() + timedelta(days=10)).isoformat()
TRAINER_TEST_END = (date.today() + timedelta(days=12)).isoformat()

import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication, QMessageBox

from core.session import AuthenticatedUser, SessionState
from services.cloud_runtime import CloudRuntime
from ui.pages.trainer_dashboard_page import TrainerDashboardPage
from ui.pages.trainer_sessions_page import TrainerSessionsPage
from ui.widgets.sidebar import Sidebar
from ui.windows.main_window import MainWindow


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    return app


@pytest.fixture
def trainer_user():
    user = AuthenticatedUser(
        id=77,
        username="melanie",
        first_name="Mélanie",
        last_name="CROCFER",
        email="melanie@example.test",
        role="Formateur",
        cloud_user_id="00000000-0000-0000-0000-000000000077",
        organization_id="00000000-0000-0000-0000-000000000001",
    )
    SessionState.login(user)
    yield user
    SessionState.logout()


class FakeAuthService:
    is_cloud = False

    def __init__(self, user):
        self.user = user

    def get_user(self, user_id):
        return self.user if user_id == self.user.id else None

    def get_user_record(self, user_id):
        return {"last_login": "2026-08-17T20:00:00"}

    def license_info(self):
        return {"plan": "Pro", "status": "Active"}


class FakeTrainerApi:
    def __init__(self):
        self.profile_calls = 0
        self.session_calls = 0

    def get_my_cloud_trainer_profile(self):
        self.profile_calls += 1
        return {
            "id": "trainer-1",
            "first_name": "Mélanie",
            "last_name": "CROCFER",
            "full_name": "Mélanie CROCFER",
        }

    def list_my_cloud_trainer_sessions(self):
        self.session_calls += 1
        return [
            {
                "id": "session-1",
                "training_reference": "FP-BTP-01",
                "training_name": "Pilotage BTP",
                "client_name": "BAZA ETANCHEITE",
                "client_contact": "Ahmed",
                "client_email": "client@example.test",
                "client_phone": "0600000000",
                "status": "planned",
                "start_date": TRAINER_TEST_START,
                "end_date": TRAINER_TEST_END,
                "daily_schedule": "09:00-12:00 / 13:00-17:00",
                "modality": "distanciel",
                "participant_count": 2,
                "connection_link": "https://meet.google.com/test-test-test",
            }
        ]


def visible_sidebar_keys(sidebar: Sidebar) -> set[str]:
    return {
        key for key, button in sidebar.buttons_by_key.items()
        if not button.isHidden()
    }


def test_trainer_sidebar_is_strictly_dedicated(qapp, trainer_user):
    sidebar = Sidebar()
    assert visible_sidebar_keys(sidebar) == {
        "trainer_dashboard",
        "trainer_sessions",
        "trainer_planning",
        "account",
    }


def test_trainer_main_window_does_not_instantiate_commercial_pages(qapp, trainer_user, monkeypatch):
    # Évite un dialogue modal si l'on teste volontairement une ouverture interdite.
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: warnings.append(args) or QMessageBox.Ok)

    window = MainWindow(FakeAuthService(trainer_user))
    assert window.is_trainer_space is True
    assert hasattr(window, "trainer_dashboard_page")
    assert hasattr(window, "trainer_sessions_page")
    assert hasattr(window, "trainer_planning_page")
    assert not hasattr(window, "prospects_page")
    assert not hasattr(window, "commissions_page")
    assert not hasattr(window, "admin_account_page")

    menu_titles = {action.text() for action in window.menuBar().actions()}
    assert "Compte" in menu_titles
    assert "Aide" in menu_titles
    assert "Outils" not in menu_titles

    window.ouvrir_commissions()
    assert warnings, "Une ouverture directe d'une fonction commerciale doit être refusée."
    window.close()


def test_trainer_pages_only_use_current_user_endpoints(qapp, trainer_user, monkeypatch):
    api = FakeTrainerApi()
    monkeypatch.setattr(CloudRuntime, "api", classmethod(lambda cls: api))

    dashboard = TrainerDashboardPage()
    dashboard.rafraichir()
    assert api.profile_calls == 1
    assert api.session_calls == 1
    assert dashboard.metric_upcoming.text() == "1"

    sessions = TrainerSessionsPage()
    sessions.rafraichir()
    assert api.session_calls == 2
    assert sessions.table.rowCount() == 1
    assert sessions.table.item(0, 0).text() == "Pilotage BTP"
    assert sessions.table.item(0, 1).text() == "BAZA ETANCHEITE"
