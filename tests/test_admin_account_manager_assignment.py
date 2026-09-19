from __future__ import annotations

from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication, QInputDialog

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
