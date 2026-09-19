from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication

from ui.pages.commercial_projects_page import CommercialProjectsPage


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


class FakeService:
    def list_for_commercial(self, user_id):
        return [
            SimpleNamespace(id="parent-btp", name="BTP", projects=(), prospect_count=120, lead_chaud_count=10),
            SimpleNamespace(id="parent-ia", name="IA", projects=(), prospect_count=50, lead_chaud_count=2),
        ]


def test_page_shows_separate_commercial_parent_cards(qapp):
    page = CommercialProjectsPage(service=FakeService(), user_id="user-florian")

    assert set(page.parent_buttons) == {"parent-btp", "parent-ia"}
    assert page.parent_buttons["parent-btp"].text().find("BTP") >= 0
    assert "120 prospect(s)" in page.parent_buttons["parent-btp"].text()
    assert "10 lead(s) chaud(s)" in page.parent_buttons["parent-btp"].text()
    assert page.parent_buttons["parent-ia"].text().find("IA") >= 0


def test_clicking_parent_with_one_child_requests_direct_project_open(qapp):
    child = SimpleNamespace(id="btp-1", name="BTP HDF - Florian")
    parent = SimpleNamespace(id="parent-btp", name="BTP", projects=(child,), prospect_count=120)
    service = SimpleNamespace(list_for_commercial=lambda user_id: [parent])
    page = CommercialProjectsPage(service=service, user_id="user-florian")
    opened = []
    page.project_open_requested.connect(opened.append)

    page.parent_buttons["parent-btp"].click()

    assert opened == ["btp-1"]


def test_clicking_parent_with_multiple_children_shows_child_choices(qapp):
    child_1 = SimpleNamespace(id="btp-1", name="BTP HDF - Florian")
    child_2 = SimpleNamespace(id="btp-2", name="Landing Page BTP - Florian")
    parent = SimpleNamespace(id="parent-btp", name="BTP", projects=(child_1, child_2), prospect_count=120)
    ia_child = SimpleNamespace(id="ia-1", name="IA HDF - Florian")
    ia_parent = SimpleNamespace(id="parent-ia", name="IA", projects=(ia_child,), prospect_count=50)
    service = SimpleNamespace(list_for_commercial=lambda user_id: [parent, ia_parent])
    page = CommercialProjectsPage(service=service, user_id="user-florian")
    opened = []
    page.project_open_requested.connect(opened.append)

    assert set(page.parent_buttons) == {"parent-btp", "parent-ia"}
    page.parent_buttons["parent-btp"].click()

    assert opened == []
    assert set(page.child_buttons) == {"btp-1", "btp-2"}


def test_child_buttons_request_their_own_project_only(qapp):
    child_1 = SimpleNamespace(id="btp-1", name="BTP HDF - Florian")
    child_2 = SimpleNamespace(id="btp-2", name="Landing Page BTP - Florian")
    parent = SimpleNamespace(id="parent-btp", name="BTP", projects=(child_1, child_2), prospect_count=120)
    service = SimpleNamespace(list_for_commercial=lambda user_id: [parent])
    page = CommercialProjectsPage(service=service, user_id="user-florian")
    opened = []
    page.project_open_requested.connect(opened.append)

    assert page.parent_buttons == {}
    assert set(page.child_buttons) == {"btp-1", "btp-2"}
    page.child_buttons["btp-2"].click()

    assert opened == ["btp-2"]


def test_single_parent_with_multiple_children_is_shown_directly(qapp):
    child_1 = SimpleNamespace(id="btp-1", name="BTP HDF - Florian")
    child_2 = SimpleNamespace(id="btp-2", name="Landing Page BTP - Florian")
    parent = SimpleNamespace(id="parent-btp", name="BTP", projects=(child_1, child_2), prospect_count=120)
    service = SimpleNamespace(list_for_commercial=lambda user_id: [parent])
    page = CommercialProjectsPage(service=service, user_id="user-florian")

    assert page.parent_buttons == {}
    assert set(page.child_buttons) == {"btp-1", "btp-2"}


def test_single_parent_without_visible_children_shows_empty_state(qapp):
    parent = SimpleNamespace(
        id="parent-btp",
        name="BTP",
        projects=(),
        prospect_count=0,
    )
    service = SimpleNamespace(list_for_commercial=lambda user_id: [parent])
    page = CommercialProjectsPage(service=service, user_id="user-florian")

    assert page.parent_buttons == {}
    assert page.child_buttons == {}
    assert page.empty_label.text() == "Aucun projet disponible pour le moment."
    assert page.empty_label.isHidden() is False


def test_child_view_hides_parents_and_back_restores_them(qapp):
    btp_1 = SimpleNamespace(id="btp-1", name="BTP HDF - Florian")
    btp_2 = SimpleNamespace(id="btp-2", name="Landing Page BTP - Florian")
    btp = SimpleNamespace(id="parent-btp", name="BTP", projects=(btp_1, btp_2), prospect_count=120)
    ia_1 = SimpleNamespace(id="ia-1", name="IA HDF - Florian")
    ia = SimpleNamespace(id="parent-ia", name="IA", projects=(ia_1,), prospect_count=50)
    service = SimpleNamespace(list_for_commercial=lambda user_id: [btp, ia])
    page = CommercialProjectsPage(service=service, user_id="user-florian")

    page.parent_buttons["parent-btp"].click()

    assert page.parent_buttons == {}
    assert set(page.child_buttons) == {"btp-1", "btp-2"}
    assert page.back_button.isHidden() is False

    page.back_button.click()

    assert set(page.parent_buttons) == {"parent-btp", "parent-ia"}
    assert page.child_buttons == {}
    assert page.back_button.isHidden() is True


def test_empty_parent_among_multiple_parents_shows_empty_state_and_back(qapp):
    btp = SimpleNamespace(id="parent-btp", name="BTP", projects=(), prospect_count=0)
    ia_child = SimpleNamespace(id="ia-1", name="IA HDF - Florian")
    ia = SimpleNamespace(id="parent-ia", name="IA", projects=(ia_child,), prospect_count=50)
    service = SimpleNamespace(list_for_commercial=lambda user_id: [btp, ia])
    page = CommercialProjectsPage(service=service, user_id="user-florian")

    page.parent_buttons["parent-btp"].click()

    assert page.parent_buttons == {}
    assert page.child_buttons == {}
    assert page.empty_label.isHidden() is False
    assert page.back_button.isHidden() is False

    page.back_button.click()
    assert set(page.parent_buttons) == {"parent-btp", "parent-ia"}


def test_child_cards_show_prospect_and_hot_lead_counts(qapp):
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
    parent = SimpleNamespace(
        id="parent-btp",
        name="BTP",
        projects=(child_1, child_2),
        prospect_count=120,
        lead_chaud_count=10,
        lead_chaud_by_project={"btp-1": 7, "btp-2": 3},
    )
    service = SimpleNamespace(list_for_commercial=lambda user_id: [parent])
    page = CommercialProjectsPage(service=service, user_id="user-florian")

    assert "100 prospect(s)" in page.child_buttons["btp-1"].text()
    assert "7 lead(s) chaud(s)" in page.child_buttons["btp-1"].text()
    assert "20 prospect(s)" in page.child_buttons["btp-2"].text()
    assert "3 lead(s) chaud(s)" in page.child_buttons["btp-2"].text()

def test_manager_page_uses_team_scope_and_manager_title(qapp):
    calls = []

    class FakeManagerService:
        def list_for_manager(self):
            calls.append("manager")
            return []

        def list_for_commercial(self, user_id):
            raise AssertionError(
                "La vue Manager ne doit pas appeler list_for_commercial()."
            )

    page = CommercialProjectsPage(
        service=FakeManagerService(),
        user_id="user-manager",
        workspace_mode="manager",
    )

    assert calls == ["manager"]
    assert page.title_label.text() == "Projets de mon équipe"
