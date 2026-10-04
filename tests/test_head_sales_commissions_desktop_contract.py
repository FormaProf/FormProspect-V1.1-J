from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_head_sales_desktop_contract():
    admin_page = (ROOT / "ui/pages/admin_account_page.py").read_text(encoding="utf-8")
    commissions_page = (ROOT / "ui/pages/commissions_page.py").read_text(encoding="utf-8")
    api_client = (ROOT / "services/cloud_api_client.py").read_text(encoding="utf-8")
    auth_service = (ROOT / "services/cloud_auth_service.py").read_text(encoding="utf-8")

    assert "head_sales_commission_rate" in auth_service
    assert "set_head_sales_commission_rate" in auth_service
    assert "déjà rattaché à un autre Head of Sales" in admin_page
    assert "Commission sur les commissions de l'équipe" in admin_page
    assert "mark_cloud_sale_head_sales_commission_paid" in api_client
    assert "Commission Head of Sales versée" in commissions_page
    assert "commercial_commission_cents" in commissions_page
