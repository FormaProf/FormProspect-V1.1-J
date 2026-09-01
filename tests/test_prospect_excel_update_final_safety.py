import sqlite3

import pandas as pd
import pytest

from services.prospect_excel_update_service import ProspectExcelUpdateService


COLUMNS_SQL = """
CREATE TABLE prospects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entreprise TEXT,
    siret TEXT,
    siren TEXT,
    adresse TEXT,
    code_postal TEXT,
    ville TEXT,
    code_naf TEXT,
    telephone TEXT,
    site_web TEXT,
    email TEXT,
    facebook TEXT,
    linkedin TEXT,
    instagram TEXT,
    youtube TEXT
)
"""


def _make_db(path, rows):
    conn = sqlite3.connect(path)
    conn.execute(COLUMNS_SQL)
    for row in rows:
        conn.execute(
            """
            INSERT INTO prospects (
                entreprise, siret, siren, adresse, code_postal, ville, code_naf,
                telephone, site_web, email, facebook, linkedin, instagram, youtube
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.get("entreprise", ""), row.get("siret", ""), row.get("siren", ""),
                row.get("adresse", ""), row.get("code_postal", ""), row.get("ville", ""),
                row.get("code_naf", ""), row.get("telephone", ""), row.get("site_web", ""),
                row.get("email", ""), row.get("facebook", ""), row.get("linkedin", ""),
                row.get("instagram", ""), row.get("youtube", ""),
            ),
        )
    conn.commit()
    conn.close()


def _prospect(path, prospect_id=1):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM prospects WHERE id = ?", (prospect_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def test_sqlite_comparison_requires_a_real_siret_column(tmp_path):
    db = tmp_path / "prospects.db"
    _make_db(db, [{"entreprise": "NADOT", "siret": "31035888200028"}])
    xlsx = tmp_path / "sans_siret.xlsx"
    pd.DataFrame([{"SIREN": "310358882", "Email": "contact@nadot.fr"}]).to_excel(
        xlsx, index=False
    )

    with pytest.raises(ValueError, match="colonne SIRET"):
        ProspectExcelUpdateService().comparer_avec_sqlite(xlsx, db)


class _MutatingPreviewService(ProspectExcelUpdateService):
    def comparer_avec_sqlite(self, fichier_excel, database_path, *, apercu_limite=100):
        preview = super().comparer_avec_sqlite(
            fichier_excel,
            database_path,
            apercu_limite=apercu_limite,
        )
        conn = sqlite3.connect(database_path)
        conn.execute(
            "UPDATE prospects SET siret = ? WHERE siret = ?",
            ("31035888200010", "31035888200028"),
        )
        conn.commit()
        conn.close()
        return preview


def test_local_apply_rechecks_siret_and_rolls_back_if_preview_became_stale(tmp_path):
    db = tmp_path / "prospects.db"
    _make_db(db, [{
        "entreprise": "NADOT",
        "siret": "31035888200028",
        "siren": "310358882",
        "email": "",
    }])
    xlsx = tmp_path / "enrichi.xlsx"
    pd.DataFrame([{
        "SIRET": "31035888200028",
        "Email": "contact@nadot.fr",
    }]).to_excel(xlsx, index=False)

    with pytest.raises(ValueError, match="SIRET.*changé"):
        _MutatingPreviewService().appliquer_mise_a_jour_sqlite(xlsx, db)

    prospect = _prospect(db)
    assert prospect["siret"] == "31035888200010"
    assert prospect["email"] == ""


def test_local_duplicate_rows_never_choose_between_conflicting_scalar_values(tmp_path):
    db = tmp_path / "prospects.db"
    _make_db(db, [{
        "entreprise": "NADOT",
        "siret": "31035888200028",
        "siren": "310358882",
        "adresse": "",
    }])
    xlsx = tmp_path / "enrichi.xlsx"
    pd.DataFrame([
        {"SIRET": "31035888200028", "Adresse": "10 rue Alpha"},
        {"SIRET": "31035888200028", "Adresse": "20 rue Beta"},
    ]).to_excel(xlsx, index=False)

    result = ProspectExcelUpdateService().appliquer_mise_a_jour_sqlite(xlsx, db)

    assert _prospect(db)["adresse"] == ""
    assert result["prospects_mis_a_jour"] == 0
    assert result["prospects_sans_action_runtime"] == 1
    assert result["conflits_runtime_ignores"] == 1


def test_local_duplicate_rows_merge_multivalue_contacts_in_one_final_value(tmp_path):
    db = tmp_path / "prospects.db"
    _make_db(db, [{
        "entreprise": "NADOT",
        "siret": "31035888200028",
        "siren": "310358882",
        "telephone": "01 34 51 26 77",
    }])
    xlsx = tmp_path / "enrichi.xlsx"
    pd.DataFrame([
        {"SIRET": "31035888200028", "Téléphone": "01 30 74 16 32"},
        {"SIRET": "31035888200028", "Téléphone": "09 62 12 27 94"},
    ]).to_excel(xlsx, index=False)

    result = ProspectExcelUpdateService().appliquer_mise_a_jour_sqlite(xlsx, db)
    telephone = _prospect(db)["telephone"]

    assert telephone == "01 34 51 26 77 ; 01 30 74 16 32 ; 09 62 12 27 94"
    assert result["prospects_mis_a_jour"] == 1
    assert result["valeurs_fusionnees"] == 2
