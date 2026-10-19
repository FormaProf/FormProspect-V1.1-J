from __future__ import annotations

from types import SimpleNamespace

import pandas as pd

from core.session import SessionState
from services.export_service import ExportService
from ui.pages.prospects_page import ProspectsPage


def test_excel_export_is_admin_only(monkeypatch):
    monkeypatch.setattr(
        SessionState,
        "user",
        lambda: SimpleNamespace(role="Administrateur"),
    )
    assert ProspectsPage._peut_exporter_excel() is True

    monkeypatch.setattr(
        SessionState,
        "user",
        lambda: SimpleNamespace(role="Manager"),
    )
    assert ProspectsPage._peut_exporter_excel() is False

    monkeypatch.setattr(
        SessionState,
        "user",
        lambda: SimpleNamespace(role="Commercial"),
    )
    assert ProspectsPage._peut_exporter_excel() is False


def test_cloud_rows_export_all_expected_columns(tmp_path):
    rows = [
        (
            "prospect-1",
            "Entreprise A",
            "Lens",
            "62300",
            "0321000000",
            "https://a.example",
            "a@example.test",
            "A contacter",
            "Haute",
            "Relance",
            "2026-10-20T10:00:00",
            "Nacim",
            0,
            "★★★★★",
            "Score Cloud à venir",
            "0611111111",
            "Import BTP",
        ),
        (
            "prospect-2",
            "Entreprise B",
            "Lille",
            "59000",
            "0322000000",
            "",
            "b@example.test",
            "Contacté",
            "Normale",
            "",
            "",
            "Mélanie",
            0,
            "★★★★★",
            "Score Cloud à venir",
            "",
            "Prospection",
        ),
    ]

    output = tmp_path / "crm.xlsx"
    total = ExportService().exporter_lignes_prospects_excel(
        rows,
        output,
    )

    assert total == 2

    exported = pd.read_excel(output)
    assert list(exported.columns) == [
        "Entreprise",
        "Ville",
        "Code postal",
        "Téléphone",
        "Mobile",
        "Site web",
        "Email",
        "Pipeline",
        "Priorité",
        "Prochaine action",
        "Date prochaine action",
        "Commercial assigné",
        "Source",
    ]
    assert exported.loc[0, "Entreprise"] == "Entreprise A"
    assert exported.loc[1, "Commercial assigné"] == "Mélanie"


def test_cloud_export_fetches_all_filtered_pages():
    source = (
        __import__("pathlib").Path(__file__).resolve().parents[1]
        / "ui"
        / "pages"
        / "prospects_page.py"
    ).read_text(encoding="utf-8")

    assert "batch_size = 500" in source
    assert "while True:" in source
    assert "rechercher_prospects_filtres(" in source
    assert "**criteres" in source
    assert "project_id=project_id" in source
    assert "offset += len(batch)" in source
    assert "L'export Cloud sera activ" not in source
