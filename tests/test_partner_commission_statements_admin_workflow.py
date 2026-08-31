from __future__ import annotations

from PySide6.QtWidgets import QApplication, QMessageBox

from core.session import AuthenticatedUser, SessionState
from ui.dialogs.partner_commission_statements_dialog import PartnerCommissionStatementsDialog


class FakePartnerStatementsAPI:
    def __init__(self):
        self.created = []
        self.partner_list_calls = 0

    def list_admin_commercial_partners(self):
        self.partner_list_calls += 1
        return [
            {"id": "partner-active", "legal_name": "J2D PRESTIGE CALL Sarl", "active": True},
            {"id": "partner-inactive", "legal_name": "Ancien partenaire", "active": False},
        ]

    def list_partner_commission_invoices(self, *, year=None, commercial_partner_id=None):
        return []

    def create_partner_commission_statement(
        self, *, commercial_partner_id: str, year: int, month: int
    ):
        self.created.append(
            {
                "commercial_partner_id": commercial_partner_id,
                "year": year,
                "month": month,
            }
        )
        return {
            "id": "statement-1",
            "statement_number": "RCP-2026-0001",
            "commercial_partner_id": commercial_partner_id,
            "total_cents": 17000,
            "lines": [],
        }


def _qapp():
    return QApplication.instance() or QApplication([])


def _login(role: str):
    SessionState.login(
        AuthenticatedUser(
            id=1,
            username="test",
            first_name="Test",
            last_name="User",
            email="test@example.test",
            role=role,
        )
    )


def test_admin_selects_partner_and_creates_statement(monkeypatch):
    _qapp()
    api = FakePartnerStatementsAPI()
    _login("Administrateur")
    try:
        monkeypatch.setattr(
            QMessageBox, "question", staticmethod(lambda *args, **kwargs: QMessageBox.Yes)
        )
        monkeypatch.setattr(
            QMessageBox, "information", staticmethod(lambda *args, **kwargs: QMessageBox.Ok)
        )

        dialog = PartnerCommissionStatementsDialog(
            api, selected_year=2026, selected_month=8
        )

        assert api.partner_list_calls == 1
        assert dialog.create_button.isHidden() is False
        assert dialog.partner_label.isHidden() is False
        assert dialog.partner_combo.isHidden() is False
        assert dialog.partner_combo.count() == 1
        assert dialog.partner_combo.currentData() == "partner-active"
        assert dialog.partner_combo.currentText() == "J2D PRESTIGE CALL Sarl"

        dialog._create_statement()

        assert api.created == [
            {
                "commercial_partner_id": "partner-active",
                "year": 2026,
                "month": 8,
            }
        ]
    finally:
        SessionState.logout()


def test_foreign_director_cannot_create_statement_from_desktop():
    _qapp()
    api = FakePartnerStatementsAPI()
    _login("Dirigeant hors France")
    try:
        dialog = PartnerCommissionStatementsDialog(
            api, selected_year=2026, selected_month=8
        )

        assert api.partner_list_calls == 0
        assert dialog.create_button.isHidden() is True
        assert dialog.partner_label.isHidden() is True
        assert dialog.partner_combo.isHidden() is True
        assert dialog.upload_invoice.isHidden() is False

        dialog._create_statement()
        assert api.created == []
    finally:
        SessionState.logout()
