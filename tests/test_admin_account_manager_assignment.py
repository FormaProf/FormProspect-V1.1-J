from __future__ import annotations

from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication, QInputDialog, QMessageBox

from core.session import SessionState
from ui.pages.admin_account_page import AdminAccountPage


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


class FakeAuthService:
    is_cloud = True

    def list_users(self):
        return [
            {
                "id": "membership-manager",
                "user_id": "user-manager",
                "first_name": "Marie",
                "last_name": "Manager",
                "email": "manager@example.test",
                "role": "Manager",
                "active": True,
                "presence_status": "offline",
                "last_login": None,
                "manager_user_id": None,
                "head_sales_commission_rate": 10.0,
                "can_create_prospect_manually": False,
            },
            {
                "id": "membership-commercial",
                "user_id": "user-commercial",
                "first_name": "Florian",
                "last_name": "Commercial",
                "email": "commercial@example.test",
                "role": "Commercial",
                "active": True,
                "presence_status": "offline",
                "last_login": None,
                "manager_user_id": "user-manager",
                "head_sales_commission_rate": 0.0,
                "can_create_prospect_manually": False,
            },
            {
                "id": "membership-trainer",
                "user_id": "user-trainer",
                "first_name": "Mélanie",
                "last_name": "Formatrice",
                "email": "trainer@example.test",
                "role": "Formateur",
                "active": True,
                "presence_status": "offline",
                "last_login": None,
                "manager_user_id": None,
                "head_sales_commission_rate": 0.0,
                "can_create_prospect_manually": False,
            },
            {
                "id": "membership-commercial-2",
                "user_id": "user-commercial-2",
                "first_name": "Sami",
                "last_name": "Commercial",
                "email": "commercial2@example.test",
                "role": "Commercial",
                "active": True,
                "presence_status": "offline",
                "last_login": None,
                "manager_user_id": None,
                "head_sales_commission_rate": 0.0,
                "can_create_prospect_manually": False,
            },
            {
                "id": "membership-manager-2",
                "user_id": "user-manager-2",
                "first_name": "Second",
                "last_name": "Manager",
                "email": "manager2@example.test",
                "role": "Manager",
                "active": True,
                "presence_status": "offline",
                "last_login": None,
                "manager_user_id": None,
                "head_sales_commission_rate": 8.0,
                "can_create_prospect_manually": False,
            },
            {
                "id": "membership-commercial-3",
                "user_id": "user-commercial-3",
                "first_name": "Elise",
                "last_name": "Commercial",
                "email": "commercial3@example.test",
                "role": "Commercial",
                "active": True,
                "presence_status": "offline",
                "last_login": None,
                "manager_user_id": "user-manager-2",
                "head_sales_commission_rate": 0.0,
                "can_create_prospect_manually": False,
            },
        ]

    def license_info(self):
        return {
            "plan": "test",
            "status": "active",
            "unlimited": True,
        }


def test_admin_can_prepare_head_of_sales_assignment_for_active_commercial(
    qapp,
    monkeypatch,
):
    monkeypatch.setattr(
        SessionState,
        "has_role",
        lambda *roles: "Administrateur" in roles,
    )
    monkeypatch.setattr(
        SessionState,
        "user",
        lambda: SimpleNamespace(
            display_name="Admin Test",
            role="Administrateur",
            email="admin@example.test",
        ),
    )

    page = AdminAccountPage(FakeAuthService())
    page.table.selectRow(1)

    assert page.manager_assignment_button.isHidden() is False
    assert page.manager_assignment_button.isEnabled()
    assert page.manager_assignment_button.text() == "Affecter un Head of Sales"


def test_admin_assigns_selected_commercial_to_head_of_sales(qapp, monkeypatch):
    monkeypatch.setattr(
        SessionState,
        'has_role',
        lambda *roles: 'Administrateur' in roles,
    )
    monkeypatch.setattr(
        SessionState,
        'user',
        lambda: SimpleNamespace(
            display_name='Admin Test',
            role='Administrateur',
            email='admin@example.test',
        ),
    )

    service = FakeAuthService()
    calls = []
    service.set_manager = lambda membership_id, manager_user_id: calls.append(
        (membership_id, manager_user_id)
    ) or {'manager_user_id': manager_user_id}

    captured = {}

    def fake_get_item(parent, title, label, items, current=0, editable=False):
        captured['title'] = title
        captured['items'] = list(items)
        captured['current'] = current
        return items[current], True

    monkeypatch.setattr(QInputDialog, 'getItem', fake_get_item)

    page = AdminAccountPage(service)
    page.table.selectRow(1)
    page.manager_assignment_button.click()

    assert captured['items'][0] == 'Aucun'
    assert any('Marie Manager' in item for item in captured['items'][1:])
    assert captured['current'] == 1
    assert calls == [('membership-commercial', 'user-manager')]


def test_admin_can_remove_head_of_sales_assignment(qapp, monkeypatch):
    monkeypatch.setattr(
        SessionState,
        'has_role',
        lambda *roles: 'Administrateur' in roles,
    )
    monkeypatch.setattr(
        SessionState,
        'user',
        lambda: SimpleNamespace(
            display_name='Admin Test',
            role='Administrateur',
            email='admin@example.test',
        ),
    )

    service = FakeAuthService()
    calls = []
    service.set_manager = lambda membership_id, manager_user_id: calls.append(
        (membership_id, manager_user_id)
    ) or {'manager_user_id': manager_user_id}

    def fake_get_item(parent, title, label, items, current=0, editable=False):
        assert items[0] == 'Aucun'
        assert current == 1
        return 'Aucun', True

    monkeypatch.setattr(QInputDialog, 'getItem', fake_get_item)

    page = AdminAccountPage(service)
    page.table.selectRow(1)
    page.manager_assignment_button.click()

    assert calls == [('membership-commercial', None)]


def _patch_admin_session(monkeypatch):
    monkeypatch.setattr(
        SessionState,
        "has_role",
        lambda *roles: "Administrateur" in roles,
    )
    monkeypatch.setattr(
        SessionState,
        "user",
        lambda: SimpleNamespace(
            display_name="Admin Test",
            role="Administrateur",
            email="admin@example.test",
        ),
    )


def test_admin_can_promote_active_trainer_to_head_of_sales(qapp, monkeypatch):
    _patch_admin_session(monkeypatch)
    service = FakeAuthService()
    role_calls = []
    service.set_role = lambda membership_id, role: role_calls.append(
        (membership_id, role)
    ) or {"role": role}

    monkeypatch.setattr(
        "ui.pages.admin_account_page.QMessageBox.question",
        lambda *args, **kwargs: QMessageBox.Yes,
    )

    page = AdminAccountPage(service)
    page.table.selectRow(2)

    assert page.promote_button.isEnabled()
    page.promote_button.click()
    assert role_calls == [("membership-trainer", "Manager")]


def test_head_of_sales_can_manage_team_from_selected_manager(qapp, monkeypatch):
    _patch_admin_session(monkeypatch)
    service = FakeAuthService()
    manager_calls = []
    service.set_manager = lambda membership_id, manager_user_id: manager_calls.append(
        (membership_id, manager_user_id)
    ) or {"manager_user_id": manager_user_id}

    page = AdminAccountPage(service)
    page.table.selectRow(0)

    assert page.manager_assignment_button.isEnabled()
    assert page.manager_assignment_button.text() == "Gérer l'équipe"

    monkeypatch.setattr(
        page,
        "_select_manager_team",
        lambda manager_name, manager_user_id, commercials, current_rate: (
            {"membership-commercial-2"},
            10.0,
        ),
    )

    page.manager_assignment_button.click()

    assert manager_calls == [
        ("membership-commercial", None),
        ("membership-commercial-2", "user-manager"),
    ]


def test_team_management_never_reassigns_commercial_from_another_manager(
    qapp,
    monkeypatch,
):
    _patch_admin_session(monkeypatch)
    service = FakeAuthService()
    manager_calls = []
    rate_calls = []
    service.set_manager = lambda membership_id, manager_user_id: manager_calls.append(
        (membership_id, manager_user_id)
    ) or {"manager_user_id": manager_user_id}
    service.set_head_sales_commission_rate = (
        lambda membership_id, rate: rate_calls.append((membership_id, rate))
        or {"head_sales_commission_rate": rate}
    )

    page = AdminAccountPage(service)
    page.table.selectRow(0)

    monkeypatch.setattr(
        page,
        "_select_manager_team",
        lambda manager_name, manager_user_id, commercials, current_rate: (
            {
                "membership-commercial",
                "membership-commercial-2",
                "membership-commercial-3",
            },
            12.0,
        ),
    )

    page.manager_assignment_button.click()

    assert rate_calls == [("membership-manager", 12.0)]
    assert ("membership-commercial-3", "user-manager") not in manager_calls
    assert ("membership-commercial-2", "user-manager") in manager_calls


def test_individual_assignment_does_not_offer_another_manager_before_removal(
    qapp,
    monkeypatch,
):
    _patch_admin_session(monkeypatch)
    service = FakeAuthService()
    calls = []
    service.set_manager = lambda membership_id, manager_user_id: calls.append(
        (membership_id, manager_user_id)
    ) or {"manager_user_id": manager_user_id}

    captured = {}

    def fake_get_item(parent, title, label, items, current=0, editable=False):
        captured["items"] = list(items)
        captured["current"] = current
        return "Aucun", True

    monkeypatch.setattr(QInputDialog, "getItem", fake_get_item)

    page = AdminAccountPage(service)
    page.table.selectRow(1)
    page.manager_assignment_button.click()

    assert captured["items"] == ["Aucun", "Marie Manager"]
    assert captured["current"] == 1
    assert calls == [("membership-commercial", None)]
