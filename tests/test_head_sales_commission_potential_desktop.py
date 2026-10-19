from __future__ import annotations

from pathlib import Path

from ui.pages.commissions_page import CommissionsPage


ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "ui/pages/commissions_page.py").read_text(encoding="utf-8")


def test_manager_team_commission_total_excludes_cancelled_sales():
    rows = [
        {
            "status": "signed",
            "commission_beneficiary_type": "head_sales",
            "commercial_commission_cents": 25_500,
        },
        {
            "status": "signed",
            "commission_beneficiary_type": "head_sales",
            "commercial_commission_cents": 50_000,
        },
        {
            "status": "cancelled",
            "commission_beneficiary_type": "head_sales",
            "commercial_commission_cents": 99_999,
        },
    ]

    assert CommissionsPage._manager_team_commission_total(rows) == 75_500


def test_manager_team_commission_total_excludes_manager_own_sale():
    rows = [
        {
            "status": "signed",
            "commission_beneficiary_type": "head_sales",
            "commercial_commission_cents": 50_000,
        },
        {
            "status": "signed",
            "commission_beneficiary_type": "commercial",
            "commercial_commission_cents": 87_500,
        },
    ]

    assert CommissionsPage._manager_team_commission_total(rows) == 50_000


def test_manager_gain_totals_include_personal_and_head_sales_commissions():
    rows = [
        {
            "status": "signed",
            "commission_beneficiary_type": "head_sales",
            "commission_status": "pending",
            "commission_cents": 2_730,
        },
        {
            "status": "signed",
            "commission_beneficiary_type": "head_sales",
            "commission_status": "pending",
            "commission_cents": 8_750,
        },
        {
            "status": "signed",
            "commission_beneficiary_type": "head_sales",
            "commission_status": "pending",
            "commission_cents": 5_000,
        },
        {
            "status": "signed",
            "commission_beneficiary_type": "commercial",
            "commission_status": "pending",
            "commission_cents": 93_750,
        },
        {
            "status": "signed",
            "commission_beneficiary_type": "commercial",
            "commission_status": "due",
            "commission_cents": 12_500,
        },
        {
            "status": "signed",
            "commission_beneficiary_type": "commercial",
            "commission_status": "paid",
            "commission_cents": 7_500,
        },
        {
            "status": "cancelled",
            "commission_beneficiary_type": "commercial",
            "commission_status": "pending",
            "commission_cents": 999_999,
        },
    ]

    totals = CommissionsPage._manager_gain_totals(rows)

    assert totals == {
        "pending": 110_230,
        "due": 12_500,
        "paid": 7_500,
    }


def test_manager_pending_helper_displays_single_snapshot_rate():
    rows = [
        {
            "status": "signed",
            "commission_status": "pending",
            "commission_rate": 10,
            "commission_cents": 2_550,
        },
        {
            "status": "signed",
            "commission_status": "due",
            "commission_rate": 10,
            "commission_cents": 5_000,
        },
    ]

    assert (
        CommissionsPage._manager_rate_helper(rows, pending_only=True)
        == "10 % des commissions équipe concernées"
    )


def test_manager_rate_helper_handles_historical_rate_changes():
    rows = [
        {
            "status": "signed",
            "commission_status": "pending",
            "commission_rate": 10,
            "commission_cents": 2_550,
        },
        {
            "status": "signed",
            "commission_status": "pending",
            "commission_rate": 12.5,
            "commission_cents": 3_125,
        },
    ]

    assert (
        CommissionsPage._manager_rate_helper(rows, pending_only=True)
        == "Taux historiques appliqués vente par vente"
    )


def test_head_sales_ui_uses_server_pending_total_and_no_extra_cloud_call():
    assert '"Gain potentiel en attente"' in PAGE
    assert '"Commissions de l\'équipe"' in PAGE
    assert 'summary["commission_pending_cents"]' in PAGE
    assert 'self._manager_team_commission_total(' in PAGE

    refresh = PAGE.split("def rafraichir(self, *_args) -> None:", 1)[1].split(
        "\n    def ",
        1,
    )[0]
    assert refresh.count("api.get_cloud_sales_summary(") == 1
    assert refresh.count("api.list_cloud_sales(") == 1
