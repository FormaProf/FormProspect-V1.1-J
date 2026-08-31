from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from services.partner_commission_statement_pdf import (
    build_partner_statement_html,
    save_partner_statement_pdf,
)


def _sample_statement():
    return {
        "statement_number": "RCP-2026-0001",
        "period_year": 2026,
        "period_month": 8,
        "issued_at": "2026-08-31",
        "seller_name": "J2D PRESTIGE CALL Sarl",
        "seller_country": "Cameroun",
        "seller_address": "Yaoundé",
        "seller_city": "Yaoundé",
        "seller_registration_number": "RC/YAE/2021/B/2822",
        "seller_tax_id": "M102116605187K",
        "buyer_name": "NM FORMATION",
        "buyer_address": "347 rue Alexandra David-Néel",
        "buyer_postal_code": "59120",
        "buyer_city": "Loos",
        "buyer_country": "France",
        "buyer_siret": "94034583800012",
        "total_cents": 17000,
        "lines": [{
            "setter_name": "Commercial test",
            "prospect_name": "Entreprise test",
            "offer_name": "Form@Prof BTP",
            "signed_at": "2026-08-10",
            "commission_rate": "10.00",
            "commission_cents": 17000,
        }],
    }


def test_partner_statement_html_is_explicitly_not_an_invoice():
    html = build_partner_statement_html(_sample_statement())
    assert "Relevé de commissions partenaire" in html
    assert "ne constitue pas une facture" in html
    assert "J2D PRESTIGE CALL Sarl" in html
    assert "170,00 €" in html


def test_partner_statement_pdf_is_generated(tmp_path):
    app = QApplication.instance() or QApplication([])
    destination = tmp_path / "releve.pdf"
    saved = save_partner_statement_pdf(_sample_statement(), destination)
    assert saved == destination
    assert destination.is_file()
    assert destination.read_bytes().startswith(b"%PDF")
    assert destination.stat().st_size > 500
