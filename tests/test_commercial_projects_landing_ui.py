from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication

from ui.pages.commercial_projects_page import CommercialProjectsPage


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


class FakeLandingService:
    def __init__(self, landing=None):
        self.landing = landing
        self.calls = []

    def list_for_commercial(self, user_id):
        child_1 = SimpleNamespace(
            id="btp-1",
            name="BTP HDF - Florian",
            prospect_count=100,
        )
        child_2 = SimpleNamespace(
            id="btp-2",
            name="Landing Page BTP - Florian",
            prospect_count=20,
        )
        return [
            SimpleNamespace(
                id="parent-btp",
                name="BTP",
                projects=(child_1, child_2),
                prospect_count=120,
                lead_chaud_count=10,
                lead_chaud_by_project={"btp-1": 7, "btp-2": 3},
            )
        ]

    def get_landing(self, project_id):
        self.calls.append(("get", project_id))
        return self.landing

    def ensure_landing(self, project_id):
        self.calls.append(("ensure", project_id))
        self.landing = SimpleNamespace(
            id="landing-1",
            project_id=project_id,
            organization_id="org-1",
            token="token-1",
            is_active=True,
        )
        return self.landing

    def set_landing_active(self, project_id, active):
        self.calls.append(("active", project_id, active))
        self.landing = SimpleNamespace(
            id="landing-1",
            project_id=project_id,
            organization_id="org-1",
            token="token-1",
            is_active=active,
        )
        return self.landing


def active_landing():
    return SimpleNamespace(
        id="landing-1",
        project_id="btp-1",
        organization_id="org-1",
        token="token-1",
        is_active=True,
    )


def test_landing_action_does_not_open_project(qapp):
    service = FakeLandingService(active_landing())
    page = CommercialProjectsPage(
        service=service,
        user_id="user-florian",
    )
    opened = []
    page.project_open_requested.connect(opened.append)

    assert "btp-1" in page.landing_buttons

    page.landing_buttons["btp-1"].click()

    assert opened == []
    assert service.calls == [("get", "btp-1")]


def test_active_landing_panel_shows_status_and_public_url(qapp):
    service = FakeLandingService(active_landing())
    page = CommercialProjectsPage(
        service=service,
        user_id="user-florian",
    )

    page.landing_buttons["btp-1"].click()

    assert page.landing_status_label.text() == "Actif"
    assert page.landing_url_edit.text() == (
        "https://pilotage.forma-prof.fr/"
        "?organization_id=org-1&token=token-1"
    )
    assert page.toggle_landing_button.text() == "Désactiver"


def test_missing_landing_can_be_created(qapp):
    service = FakeLandingService(None)
    page = CommercialProjectsPage(
        service=service,
        user_id="user-florian",
    )

    page.landing_buttons["btp-1"].click()

    assert page.landing_status_label.text() == "Aucun lien"
    assert page.landing_url_edit.text() == ""

    page.create_landing_button.click()

    assert ("ensure", "btp-1") in service.calls
    assert page.landing_status_label.text() == "Actif"
    assert "organization_id=org-1" in page.landing_url_edit.text()


def test_landing_can_be_deactivated_and_reactivated(qapp):
    service = FakeLandingService(active_landing())
    page = CommercialProjectsPage(
        service=service,
        user_id="user-florian",
    )

    page.landing_buttons["btp-1"].click()
    page.toggle_landing_button.click()

    assert ("active", "btp-1", False) in service.calls
    assert page.landing_status_label.text() == "Inactif"
    assert page.toggle_landing_button.text() == "Activer"

    page.toggle_landing_button.click()

    assert ("active", "btp-1", True) in service.calls
    assert page.landing_status_label.text() == "Actif"
    assert page.toggle_landing_button.text() == "Désactiver"


def test_manager_workspace_does_not_expose_personal_landing_actions(qapp):
    class ManagerService:
        def list_for_manager(self):
            child = SimpleNamespace(
                id="btp-1",
                name="BTP HDF",
                prospect_count=10,
            )
            return [
                SimpleNamespace(
                    id="parent-btp",
                    name="BTP",
                    projects=(child,),
                    prospect_count=10,
                    lead_chaud_count=0,
                    lead_chaud_by_project={"btp-1": 0},
                )
            ]

    page = CommercialProjectsPage(
        service=ManagerService(),
        user_id="manager-1",
        workspace_mode="manager",
    )

    assert page.landing_buttons == {}


def test_single_project_parent_keeps_direct_open_and_exposes_landing(qapp):
    class SingleProjectService:
        def __init__(self):
            self.calls = []

        def list_for_commercial(self, user_id):
            child = SimpleNamespace(
                id="btp-1",
                name="BTP HDF - Florian",
                prospect_count=10,
            )
            return [
                SimpleNamespace(
                    id="parent-btp",
                    name="BTP",
                    projects=(child,),
                    prospect_count=10,
                    lead_chaud_count=1,
                    lead_chaud_by_project={"btp-1": 1},
                )
            ]

        def get_landing(self, project_id):
            self.calls.append(("get", project_id))
            return active_landing()

    service = SingleProjectService()
    page = CommercialProjectsPage(
        service=service,
        user_id="user-florian",
    )
    opened = []
    page.project_open_requested.connect(opened.append)

    assert "parent-btp" in page.parent_buttons
    assert "btp-1" in page.landing_buttons

    page.landing_buttons["btp-1"].click()

    assert opened == []
    assert service.calls == [("get", "btp-1")]

    page.parent_buttons["parent-btp"].click()

    assert opened == ["btp-1"]
