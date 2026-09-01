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


def _row(path, siret):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM prospects WHERE siret = ?", (siret,)).fetchone()
    conn.close()
    return dict(row) if row else None


def _count(path):
    conn = sqlite3.connect(path)
    count = conn.execute("SELECT COUNT(*) FROM prospects").fetchone()[0]
    conn.close()
    return count


def test_apply_is_additive_and_never_creates_or_deletes(tmp_path):
    db = tmp_path / "prospects.db"
    _make_db(db, [{
        "entreprise": "ENTREPRISE NADOT",
        "siret": "31035888200028",
        "siren": "310358882",
        "telephone": "01 34 51 26 77",
        "email": "ancien@nadot.fr",
        "site_web": "https://nadot.fr",
        "adresse": "1 rue Ancienne",
    }])
    xlsx = tmp_path / "enrichi.xlsx"
    pd.DataFrame([{
        "SIRET": "31035888200028",
        "Téléphone": "01 30 74 16 32",
        "Mobile": "06 11 22 33 44",
        "Email": "contact@nadot.fr",
        "Site web": "https://www.nadot.fr/contact",
        "Facebook": "https://facebook.com/nadot",
        "Adresse": "2 rue Nouvelle",
    }, {
        "SIRET": "99999999999999",
        "Téléphone": "09 99 99 99 99",
    }]).to_excel(xlsx, index=False)

    stats = ProspectExcelUpdateService().appliquer_mise_a_jour_sqlite(xlsx, db)

    prospect = _row(db, "31035888200028")
    assert "01 34 51 26 77" in prospect["telephone"]
    assert "01 30 74 16 32" in prospect["telephone"]
    assert "06 11 22 33 44" in prospect["telephone"]
    assert "ancien@nadot.fr" in prospect["email"]
    assert "contact@nadot.fr" in prospect["email"]
    assert "https://nadot.fr" in prospect["site_web"]
    assert "https://www.nadot.fr/contact" in prospect["site_web"]
    assert prospect["facebook"] == "https://facebook.com/nadot"
    # Un champ scalaire contradictoire n'est jamais écrasé automatiquement.
    assert prospect["adresse"] == "1 rue Ancienne"
    assert _count(db) == 1
    assert stats["prospects_mis_a_jour"] == 1
    assert stats["introuvables"] == 1
    assert stats["creation_prospects"] is False
    assert stats["suppression_donnees"] is False
    assert stats["conflits_ignores"] >= 1


def test_apply_uses_exact_siret_only_never_siren_fallback(tmp_path):
    db = tmp_path / "prospects.db"
    _make_db(db, [{
        "entreprise": "CIBLE",
        "siret": "31035888200028",
        "siren": "310358882",
        "telephone": "",
    }])
    xlsx = tmp_path / "enrichi.xlsx"
    pd.DataFrame([{
        "SIRET": "31035888299999",
        "SIREN": "310358882",
        "Téléphone": "01 23 45 67 89",
    }]).to_excel(xlsx, index=False)

    stats = ProspectExcelUpdateService().appliquer_mise_a_jour_sqlite(xlsx, db)

    assert _row(db, "31035888200028")["telephone"] == ""
    assert stats["prospects_mis_a_jour"] == 0
    assert stats["introuvables"] == 1


def test_apply_empty_cells_never_clear_existing_data_and_deduplicates(tmp_path):
    db = tmp_path / "prospects.db"
    _make_db(db, [{
        "entreprise": "TEST",
        "siret": "30109677200027",
        "siren": "301096772",
        "telephone": "01 47 37 56 00",
        "email": "contact@test.fr",
        "site_web": "https://test.fr",
    }])
    xlsx = tmp_path / "enrichi.xlsx"
    pd.DataFrame([{
        "SIRET": "30109677200027",
        "Téléphone": "+33 1 47 37 56 00",
        "Email": "CONTACT@TEST.FR",
        "Site web": "https://test.fr/",
        "Facebook": "",
    }]).to_excel(xlsx, index=False)

    stats = ProspectExcelUpdateService().appliquer_mise_a_jour_sqlite(xlsx, db)
    prospect = _row(db, "30109677200027")

    assert prospect["telephone"] == "01 47 37 56 00"
    assert prospect["email"] == "contact@test.fr"
    assert prospect["site_web"] == "https://test.fr"
    assert stats["prospects_mis_a_jour"] == 0
    assert stats["informations_ajoutees"] == 0


def test_apply_completes_empty_scalar_fields_but_preserves_conflicts(tmp_path):
    db = tmp_path / "prospects.db"
    _make_db(db, [{
        "entreprise": "TEST",
        "siret": "30109677200027",
        "siren": "301096772",
        "adresse": "",
        "ville": "PARIS",
    }])
    xlsx = tmp_path / "enrichi.xlsx"
    pd.DataFrame([{
        "SIRET": "30109677200027",
        "Adresse": "56 RUE DU FAUBOURG SAINT-ANTOINE",
        "Ville": "LYON",
    }]).to_excel(xlsx, index=False)

    stats = ProspectExcelUpdateService().appliquer_mise_a_jour_sqlite(xlsx, db)
    prospect = _row(db, "30109677200027")

    assert prospect["adresse"] == "56 RUE DU FAUBOURG SAINT-ANTOINE"
    assert prospect["ville"] == "PARIS"
    assert stats["champs_completes"] == 1
    assert stats["conflits_ignores"] == 1


def test_apply_rolls_back_entire_transaction_on_sql_error(tmp_path):
    db = tmp_path / "prospects.db"
    conn = sqlite3.connect(db)
    conn.execute("""
        CREATE TABLE prospects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entreprise TEXT, siret TEXT, siren TEXT, adresse TEXT,
            code_postal TEXT, ville TEXT, code_naf TEXT,
            telephone TEXT,
            site_web TEXT,
            email TEXT CHECK(email <> 'boom@example.fr'),
            facebook TEXT, linkedin TEXT, instagram TEXT, youtube TEXT
        )
    """)
    conn.execute("INSERT INTO prospects (entreprise, siret, telephone, email) VALUES ('A', '11111111111111', '', '')")
    conn.execute("INSERT INTO prospects (entreprise, siret, telephone, email) VALUES ('B', '22222222222222', '', '')")
    conn.commit()
    conn.close()

    xlsx = tmp_path / "enrichi.xlsx"
    pd.DataFrame([
        {"SIRET": "11111111111111", "Téléphone": "01 11 11 11 11"},
        {"SIRET": "22222222222222", "Email": "boom@example.fr"},
    ]).to_excel(xlsx, index=False)

    with pytest.raises(sqlite3.IntegrityError):
        ProspectExcelUpdateService().appliquer_mise_a_jour_sqlite(xlsx, db)

    assert _row(db, "11111111111111")["telephone"] == ""
    assert _row(db, "22222222222222")["email"] == ""
