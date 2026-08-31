from __future__ import annotations

from datetime import date, timedelta

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

TRAINER_TEST_START = (date.today() + timedelta(days=10)).isoformat()
TRAINER_TEST_END = (date.today() + timedelta(days=12)).isoformat()

import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from core.session import AuthenticatedUser, SessionState
from services.cloud_runtime import CloudRuntime
from ui.pages.trainer_dashboard_page import TrainerDashboardPage
from ui.pages.trainer_planning_page import TrainerPlanningPage
from ui.pages.trainer_session_detail_page import TrainerSessionDetailPage
from ui.pages.trainer_sessions_page import TrainerSessionsPage


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def trainer_user():
    user = AuthenticatedUser(
        id=88,
        username="jack",
        first_name="Jack",
        last_name="Carter",
        email="jack@example.test",
        role="Formateur",
        cloud_user_id="00000000-0000-0000-0000-000000000088",
        organization_id="00000000-0000-0000-0000-000000000001",
    )
    SessionState.login(user)
    yield user
    SessionState.logout()


class FakeTrainerApi:
    def get_my_cloud_trainer_profile(self):
        return {"first_name": "Jack", "full_name": "Jack Carter"}

    def list_my_cloud_trainer_sessions(self):
        return [{
            "id": "session-jack-1",
            "training_reference": "FP-BTP-01",
            "training_name": "Pilotage BTP",
            "client_name": "BEUVAIN MONTAGE",
            "status": "planned",
            "start_date": TRAINER_TEST_START,
            "end_date": TRAINER_TEST_END,
            "daily_schedule": "09:00-12:00 / 13:00-15:00",
            "modality": "distance",
            "participant_count": 1,
            "connection_link": "https://meet.google.com/test-test-test",
        }]

    def get_my_cloud_trainer_session(self, session_id):
        assert session_id == "session-jack-1"
        return {
            "id": session_id,
            "training_reference": "FP-BTP-01",
            "training_name": "Pilotage BTP",
            "training_category": "BTP",
            "training_description": "Description pédagogique",
            "training_objectives": "Piloter l'activité",
            "training_prerequisites": "Aucun prérequis",
            "training_certification": None,
            "duration_hours": 14,
            "trainer_name": "Jack Carter",
            "client_name": "BEUVAIN MONTAGE",
            "client_contact": "Contact client",
            "client_email": "contact@example.test",
            "client_phone": "03 20 00 00 00",
            "status": "planned",
            "start_date": TRAINER_TEST_START,
            "end_date": TRAINER_TEST_END,
            "daily_schedule": "09:00-12:00 / 13:00-15:00",
            "modality": "distance",
            "participant_count": 1,
            "connection_link": "https://meet.google.com/test-test-test",
        }


def test_sessions_page_emits_selected_session(qapp, trainer_user, monkeypatch):
    monkeypatch.setattr(CloudRuntime, "api", classmethod(lambda cls: FakeTrainerApi()))
    page = TrainerSessionsPage()
    page.rafraichir()
    page.table.selectRow(0)
    emitted = []
    page.session_open_requested.connect(emitted.append)
    page._open_selected_session()
    assert emitted == ["session-jack-1"]


def test_dashboard_double_click_emits_session(qapp, trainer_user, monkeypatch):
    monkeypatch.setattr(CloudRuntime, "api", classmethod(lambda cls: FakeTrainerApi()))
    page = TrainerDashboardPage()
    page.rafraichir()
    emitted = []
    page.session_open_requested.connect(emitted.append)
    page._open_selected_session(0, 0)
    assert emitted == ["session-jack-1"]


def test_planning_contains_open_button(qapp, trainer_user, monkeypatch):
    monkeypatch.setattr(CloudRuntime, "api", classmethod(lambda cls: FakeTrainerApi()))
    page = TrainerPlanningPage()
    page.rafraichir()
    buttons = page.findChildren(__import__('PySide6.QtWidgets', fromlist=['QPushButton']).QPushButton)
    assert any(button.text() == "Ouvrir" for button in buttons)


def test_detail_page_uses_secure_current_trainer_endpoint(qapp, trainer_user, monkeypatch):
    api = FakeTrainerApi()
    monkeypatch.setattr(CloudRuntime, "api", classmethod(lambda cls: api))
    page = TrainerSessionDetailPage()
    page.charger_session("session-jack-1")
    assert page.title_label.text() == "Pilotage BTP"
    assert page.client_label.text() == "BEUVAIN MONTAGE"
    assert page.trainer_value.text() == "Jack Carter"
    assert page.objectives_value.text() == "Piloter l'activité"
    assert "14" in page.duration_value.text()
